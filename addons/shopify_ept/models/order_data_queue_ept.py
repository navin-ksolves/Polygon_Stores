# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import time
import re
import logging
from datetime import datetime, timedelta
import pytz
from odoo import models, fields, api, _

from odoo.exceptions import UserError
from ..shopify.pyactiveresource.connection import ClientError
from .. import shopify

utc = pytz.utc

_logger = logging.getLogger("Shopify Order Queue")


class ShopifyOrderDataQueueEpt(models.Model):
    _name = "shopify.order.data.queue.ept"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Shopify Order Data Queue"

    name = fields.Char(help="Sequential name of imported order.", copy=False)
    shopify_instance_id = fields.Many2one('shopify.instance.ept', string='Instance',
                                          help="Order imported from this Shopify Instance.")
    state = fields.Selection([('draft', 'Draft'), ('partially_completed', 'Partially Completed'),
                              ('completed', 'Completed'), ('failed', 'Failed')], tracking=True,
                             default='draft', copy=False, compute="_compute_queue_state",
                             store=True)
    shopify_order_common_log_lines_ids = fields.One2many("common.log.lines.ept", compute="_compute_log_lines")

    order_data_queue_line_ids = fields.One2many("shopify.order.data.queue.line.ept",
                                                "shopify_order_data_queue_id")
    order_queue_line_total_record = fields.Integer(string='Total Records',
                                                   compute='_compute_order_queue_line_record')
    order_queue_line_draft_record = fields.Integer(string='Draft Records',
                                                   compute='_compute_order_queue_line_record')
    order_queue_line_fail_record = fields.Integer(string='Fail Records',
                                                  compute='_compute_order_queue_line_record')
    order_queue_line_done_record = fields.Integer(string='Done Records',
                                                  compute='_compute_order_queue_line_record')

    order_queue_line_cancel_record = fields.Integer(string='Cancel Records',
                                                    compute='_compute_order_queue_line_record')
    created_by = fields.Selection([("import", "By Manually Import Process"), ("webhook", "By Webhook"),
                                   ("scheduled_action", "By Scheduled Action")],
                                  help="Identify the process that generated a queue.", default="import")
    is_process_queue = fields.Boolean('Is Processing Queue', default=False)
    running_status = fields.Char(default="Running...")
    queue_process_count = fields.Integer(string="Queue Process Times",
                                         help="it is used know queue how many time processed")
    is_action_require = fields.Boolean(default=False, help="it is used  to find the action require queue")
    queue_type = fields.Selection([("shipped", "Shipped Order Queue"), ("unshipped", "Unshipped Order Queue")],
                                  help="Identify to queue for which type of order import.")

    @api.depends('order_data_queue_line_ids.shopify_order_common_log_lines_ids')
    def _compute_log_lines(self):
        for line in self:
            line.shopify_order_common_log_lines_ids = line.order_data_queue_line_ids.shopify_order_common_log_lines_ids

    @api.depends('order_data_queue_line_ids.state')
    def _compute_queue_state(self):
        
        for record in self:
            if record.order_queue_line_total_record == record.order_queue_line_done_record + \
                    record.order_queue_line_cancel_record:
                record.state = "completed"
            elif record.order_queue_line_draft_record == record.order_queue_line_total_record:
                record.state = "draft"
            elif record.order_queue_line_total_record == record.order_queue_line_fail_record:
                record.state = "failed"
            else:
                record.state = "partially_completed"

    @api.depends('order_data_queue_line_ids.state')
    def _compute_order_queue_line_record(self):
        
        for order_queue in self:
            queue_lines = order_queue.order_data_queue_line_ids
            order_queue.order_queue_line_total_record = len(queue_lines)
            order_queue.order_queue_line_draft_record = len(queue_lines.filtered(lambda x: x.state == "draft"))
            order_queue.order_queue_line_done_record = len(queue_lines.filtered(lambda x: x.state == "done"))
            order_queue.order_queue_line_fail_record = len(queue_lines.filtered(lambda x: x.state == "failed"))
            order_queue.order_queue_line_cancel_record = len(queue_lines.filtered(lambda x: x.state == "cancel"))

    @api.model_create_multi
    def create(self, vals):
      
        for val in vals:
            sequence_id = self.env.ref('shopify_ept.seq_order_queue_data').ids
            if sequence_id:
                record_name = self.env['ir.sequence'].browse(sequence_id).next_by_id()
            else:
                record_name = '/'
            val.update({'name': record_name or ''})
        return super(ShopifyOrderDataQueueEpt, self).create(vals)

    def import_order_cron_action(self, ctx=False):
        
        if isinstance(ctx, dict):
            instance_id = ctx.get('shopify_instance_id')
            instance = self.env['shopify.instance.ept'].browse(instance_id)
            from_date = instance.last_date_order_import
            to_date = datetime.now()
            if not from_date:
                from_date = to_date - timedelta(3)

            self.shopify_create_order_data_queues(instance, from_date, to_date, created_by="scheduled_action")
        return True

    def import_shipped_order_cron_action(self, ctx=False):
        
        if not isinstance(ctx, dict):
            return True
        instance_id = ctx.get('shopify_instance_id')
        instance = self.env['shopify.instance.ept'].browse(instance_id)
        from_date = instance.last_shipped_order_import_date
        to_date = datetime.now()
        if not from_date:
            from_date = to_date - timedelta(3)

        self.shopify_create_order_data_queues(instance, from_date, to_date, created_by="scheduled_action",
                                              order_type="shipped")
        return True

    def convert_dates_by_timezone(self, instance, from_date, to_date):
        
        if not instance.shopify_store_time_zone:
            shop_id = shopify.Shop.current()
            shop_detail = shop_id.to_dict()
            instance.write({'shopify_store_time_zone': shop_detail.get('iana_timezone')})
            self._cr.commit()

        from_date = pytz.utc.localize(from_date).astimezone(pytz.timezone(instance.shopify_store_time_zone or
                                                                          'UTC')).strftime('%Y-%m-%dT%H:%M:%S%z')
        to_date = pytz.utc.localize(to_date).astimezone(pytz.timezone(instance.shopify_store_time_zone or
                                                                      'UTC')).strftime('%Y-%m-%dT%H:%M:%S%z')
        return from_date, to_date

    def shopify_create_order_data_queues(self, instance, from_date, to_date, created_by="import",
                                         order_type="unshipped"):
        
        order_data_queue_line_obj = self.env["shopify.order.data.queue.line.ept"]
        start = time.time()
        order_queues = []
        instance.connect_in_shopify()
        if order_type != "shipped":
            queue_type = 'unshipped'
            for order_status_id in instance.shopify_order_status_ids:
                order_status = order_status_id.status
                order_ids = self.shopify_order_request(instance, from_date, to_date, order_status)

                if order_ids:
                    order_queues = order_data_queue_line_obj.create_order_data_queue_line(order_ids,
                                                                                          instance,
                                                                                          queue_type,
                                                                                          created_by)
                    if len(order_ids) >= 250:
                        order_queue_list = self.list_all_orders(order_ids, instance, created_by, queue_type)
                        order_queues += order_queue_list
                instance.last_date_order_import = to_date - timedelta(days=2)
        else:
            order_queues = self.shopify_shipped_order_request(instance, from_date, to_date, created_by="import",
                                                              order_type="shipped")
            instance.last_shipped_order_import_date = to_date - timedelta(days=2)
        end = time.time()
        _logger.info("Imported Orders in %s seconds.", str(end - start))
        return order_queues

    def shopify_order_request(self, instance, from_date, to_date, order_type):
        
        from_date, to_date = self.convert_dates_by_timezone(instance, from_date, to_date)
        try:
            order_ids = shopify.Order().find(status="any",
                                             fulfillment_status=order_type,
                                             updated_at_min=from_date,
                                             updated_at_max=to_date, limit=250)
        except Exception as error:
            raise UserError(error)

        return order_ids

    def shopify_shipped_order_request(self, instance, from_date, to_date, order_type, created_by):
        
        order_data_queue_line_obj = self.env["shopify.order.data.queue.line.ept"]
        order_queues = []
        queue_type = 'shipped'
        order_ids = self.shopify_order_request(instance, from_date, to_date, order_type)
        if order_ids:
            order_queues = order_data_queue_line_obj.create_order_data_queue_line(order_ids,
                                                                                  instance,
                                                                                  queue_type,
                                                                                  created_by)
            if len(order_ids) >= 250:
                order_queue_list = self.list_all_orders(order_ids, instance, created_by, queue_type)
                order_queues += order_queue_list

        return order_queues

    def list_all_orders(self, result, instance, created_by, queue_type):
        
        order_data_queue_line_obj = self.env["shopify.order.data.queue.line.ept"]
        order_queue_list = []
        catch = ""

        while result:
            page_info = ""
            # link: link of next page.
            link = shopify.ShopifyResource.connection.response.headers.get('Link')
            if not link or not isinstance(link, str):
                return order_queue_list

            for page_link in link.split(','):
                if page_link.find('next') > 0:
                    page_info = page_link.split(';')[0].strip('<>').split('page_info=')[1]
                    try:
                        result = shopify.Order().find(limit=250, page_info=page_info)
                    except ClientError as error:
                        if hasattr(error,
                                   "response") and error.response.code == 429 and error.response.msg == "Too Many Requests":
                            time.sleep(int(float(error.response.headers.get('Retry-After', 5))))
                            result = shopify.Order().find(limit=250, page_info=page_info)
                    except Exception as error:
                        raise UserError(error)
                    if result:
                        order_queues = order_data_queue_line_obj.create_order_data_queue_line(result, instance,
                                                                                              queue_type,
                                                                                              created_by)
                        order_queue_list += order_queues
            if catch == page_info:
                break
        return order_queue_list

    def import_order_process_by_remote_ids(self, instance, order_ids):
        
        order_data_queue_line_obj = self.env["shopify.order.data.queue.line.ept"]
        order_queue_obj = self.env["shopify.order.data.queue.ept"]
        queue_type = 'unshipped'
        if order_ids:
            instance.connect_in_shopify()
            # Below one line is used to find only character values from order ids.
            re.findall("[a-zA-Z]+", order_ids)
            if len(order_ids.split(',')) <= 50:
                # order_ids_list is a list of all order ids which response did not given by shopify.
                order_ids_list = list(set(re.findall(re.compile(r"(\d+)"), order_ids)))
                results = shopify.Order().find(ids=','.join(order_ids_list), status='any')
                if results:
                    _logger.info('%s Shopify order(s) imported from instance : %s', len(results), instance.name)
                    order_ids_list = [order_id.strip() for order_id in order_ids_list]
                    # Below process to identify which id response did not give by Shopify.
                    [order_ids_list.remove(str(result.id)) for result in results if str(result.id) in order_ids_list]
            else:
                raise UserError(_('Please enter the Order ids 50 or less'))
            if results:
                if order_ids_list:
                    #print("REsultttttttttttttttttttttttttt",results)
                    _logger.warning("Orders are not found for ids :%s", str(order_ids_list))
                order_queues = order_data_queue_line_obj.create_order_data_queue_line(results,
                                                                                      instance,
                                                                                      queue_type,
                                                                                      created_by="import")
                #order_queue_obj.browse(order_queues).order_data_queue_line_ids.process_import_order_queue_data()
        return True

    def create_schedule_activity(self, queue_id):
        
        mail_activity_obj = self.env['mail.activity']
        ir_model_obj = self.env['ir.model']
        model_id = ir_model_obj.search([('model', '=', 'shopify.order.data.queue.ept')])
        activity_type_id = queue_id and queue_id.shopify_instance_id.shopify_activity_type_id.id
        date_deadline = datetime.strftime(
            datetime.now() + timedelta(days=int(queue_id.shopify_instance_id.shopify_date_deadline)), "%Y-%m-%d")
        if queue_id:
            shopify_order_id_list = queue_id.order_data_queue_line_ids.filtered(
                lambda line: line.state == 'failed').mapped('shopify_order_id')
            if len(shopify_order_id_list) > 0:
                note = 'Your order has not been imported for Shopify Order Reference : %s' % str(
                    shopify_order_id_list)[1:-1]
                for user_id in queue_id.shopify_instance_id.shopify_user_ids:
                    mail_activity = mail_activity_obj.search([('res_model_id', '=', model_id.id),
                                                              ('user_id', '=', user_id.id),
                                                              ('res_name', '=', queue_id.name),
                                                              ('activity_type_id', '=', activity_type_id)])
                    note_2 = "<p>" + note + '</p>'
                    duplicate_activity = mail_activity.filtered(lambda x: x.note == note_2)
                    if not mail_activity or not duplicate_activity:
                        vals = {'activity_type_id': activity_type_id, 'note': note,
                                'res_id': queue_id.id, 'user_id': user_id.id or self._uid,
                                'res_model_id': model_id.id, 'date_deadline': date_deadline}
                        try:
                            mail_activity_obj.create(vals)
                        except Exception as error:
                            _logger.info("Unable to create schedule activity, Please give proper "
                                         "access right of this user :%s  ", user_id.name)
                            _logger.info(error)
        return True

    @api.model
    def retrieve_dashboard(self, *args, **kwargs):
       
        dashboard = self.env['queue.line.dashboard']
        return dashboard.get_data(table='shopify.order.data.queue.line.ept')
