# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.exceptions import ValidationError
from . import common_functions
import logging, ast

_logger = logging.getLogger(__name__)

class ZidSchedulerOrderLine(models.Model):
    _name = 'zid.scheduler.order.line'
    _description = 'Zid Order Line Scheduler '
    _inherit = ['mail.thread', 'mail.activity.mixin']

    status = fields.Selection([('draft', 'Draft'), ('progress', 'In Progess'), ('done', 'Done'), ('failed', 'Failed')],
                              string="Status", tracking=True, default='draft', readonly=True)
    data = fields.Text(string="Json Data", readonly=True)
    scheduler_order_id = fields.Many2one('zid.scheduler.order', 'Order', readonly=True)
    locations = fields.Char('Location', readonly=True) # TODO: verify fields
    header = fields.Char('Header', readonly=True)
    lines = fields.Integer('Lines', readonly=True)
    order_id = fields.Many2one('zid.order.ept','Zid Order')
    attempts = fields.Integer("Scheduler Attempts")

    def process_order_line(self, args={}):
        """
        Cron function to process order line scheduler records that are in draft state
        :return:
        """
        record_limit = args.get('limit')
        orders_lines = self.search(['|', '&', ('status','=','failed'),('attempts','<', 3),('status', '=', 'draft')], limit = record_limit)
        _logger.info("Syncing Zid Orders!!")
        order_line_objs = self.env['zid.order.lines.ept']
        for orders_line in orders_lines:
            try:
                _logger.info("Syncing order line!!")
                orders_line.status = 'progress'
                orders_line.attempts += 1
                input_string = orders_line['data']
                order_line_data = ast.literal_eval(input_string)['data'][0]
                zid_instance_id = orders_line.scheduler_order_id.scheduler_log_id.instance_id.id
                product_variant = self.env['zid.product.variants'].search([('zid_id','=',order_line_data['id']),
                                                                           ('zid_instance_id','=',zid_instance_id)])
                if not product_variant:
                    raise ValidationError(f"Variant with Zid Id {order_line_data['id']} does not exists!!")
                zid_order_line_vals = {
                    'name': f"Zid Order id {orders_line.order_id.name} Order Line",
                    'order_id': orders_line.order_id.id,
                    'product_id': product_variant.product_variant_id.id,
                    # 'item_id' : product_variant.product_template_id.id,
                    'sku' : order_line_data['sku'],
                    'quantity' : order_line_data['quantity'],
                    'price' : order_line_data['price'],
                    'zid_instance_id' : zid_instance_id,
                    'tax_percentage' : order_line_data['tax_percentage']
                }
                zid_order_line_id = order_line_objs.create(zid_order_line_vals)
                if zid_order_line_id:
                    orders_line.order_id = zid_order_line_id.order_id.id
                    orders_line.status = 'done'
                    # Updating attempt of order scheduler record
                    common_functions.update_log_line_attempts(self, 'zid.scheduler.order.line',
                                                              orders_line.scheduler_order_id,
                                                              'scheduler_order_id')
                    # Update scheduler log line attempts
                    common_functions.update_log_line_attempts(self, 'zid.scheduler.order',
                                                              orders_line.scheduler_order_id.scheduler_log_id,
                                                              'scheduler_log_id')
                    # Incrementing completed line of order
                    orders_line.scheduler_order_id.line_done += 1
                    # Checking if order completed & total line equal, if equal then status = 'done'
                    if orders_line.scheduler_order_id.line_count == orders_line.scheduler_order_id.line_done:
                        orders_line.scheduler_order_id.status = 'done'
                        # Incrementing scheduler log line completed log lines
                        orders_line.scheduler_order_id.scheduler_log_id.completed_lines += 1
                        # Updating status of scheduler log line
                        common_functions.update_scheduler_log_state(orders_line.scheduler_order_id.scheduler_log_id)

            except Exception as e:
                orders_line.status = 'failed'
                # Updating attempt of order scheduler record
                common_functions.update_log_line_attempts(self, 'zid.scheduler.order.line',
                                                          orders_line.scheduler_order_id,
                                                          'scheduler_order_id')
                # Update scheduler log line attempts
                common_functions.update_log_line_attempts(self, 'zid.scheduler.order',
                                                          orders_line.scheduler_order_id.scheduler_log_id,
                                                          'scheduler_log_id')
                _logger.error(str(e))
                _logger.error("Order Line Creation Failed!!")



