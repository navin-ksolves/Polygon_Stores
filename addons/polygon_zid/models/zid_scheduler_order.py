# -*- coding: utf-8 -*-
from odoo import models, fields, api
from . import common_functions
from odoo.exceptions import ValidationError
from datetime import datetime
import requests
import logging, ast

_logger = logging.getLogger(__name__)


class ZidSchedulerOrder(models.Model):
    _name = 'zid.scheduler.order'
    _description = 'Zid Order Scheduler'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    status = fields.Selection([('draft', 'Draft'), ('progress', 'In Progess'), ('done', 'Done'), ('failed', 'Failed')],
                              string="Status", tracking=True, default='draft', readonly=True)
    data = fields.Text(string="Json Data", readonly=True)
    contact = fields.Char('Contact', readonly=True)
    header = fields.Char('Header', readonly=True)  # TODO: verify fields
    line_count = fields.Integer('Line Count', readonly=True)
    line_done = fields.Integer('Line Done', readonly=True)
    scheduler_log_id = fields.Many2one('zid.scheduler.log.line', string="Scheduler Log", readonly=True)
    customer = fields.Boolean('Customer', readonly=True)
    attempts = fields.Integer("Scheduler Attempts")

    def process_zid_order_queue(self, args={}):
        """
        Cron function to process order queue
        :return:
        """
        record_limit = args.get('limit')
        orders = self.search(['|', '&', ('status','=','failed'),('attempts','<', 3),('status', '=', 'draft')], limit = record_limit)
        _logger.info("Syncing Zid Orders!!")
        order_objs = self.env['zid.order.ept']
        for order in orders:
            try:
                order.status = 'progress'
                input_string = order['data']
                order_data = ast.literal_eval(input_string)
                full_order_data = self.get_full_order_detail(order_data['id'], order.scheduler_log_id)
                # Checking customer present or not, if not then create customer
                zid_customer = self.env['zid.customer.ept'].search([('email', '=', order_data['customer']['email'])])
                customer_details = order_data['customer']
                if not zid_customer:
                    customer_vals = {
                        'name': customer_details['name'],
                        'email': customer_details['email'],
                        'phone': customer_details['mobile'],
                        'instance_id': order.scheduler_log_id.instance_id.id
                    }
                    zid_customer = self.env['zid.customer.ept'].create(customer_vals)

                # Creating customer location
                if full_order_data.get('shipping').get('address'):
                    address = full_order_data.get('shipping').get('address')
                    state = self.env['zid.state.master'].search([('zid_state_id','=',address.get('city').get('id'))])
                    country = self.env['zid.country.master'].search([('zid_country_id','=',address.get('country').get('id'))])
                    address_vals = {
                        'name': f"Shipping Address - {customer_details['name']}",
                        'customer_id' : zid_customer.id if zid_customer['id'] else False,
                        'street' : address['street'],
                        'street2' : address['district'],
                        'is_billing': False,
                        'is_shipping': True,
                        'state' : state.id if state else False,
                        'country' : country.id if country else False
                    }
                    customer_location = self.env['zid.customer.locations'].create(address_vals)

                if zid_customer:
                    order.customer = True
                # Creating zid order
                zid_order_vals = {
                    'name': order_data['code'],
                    'online_order_id': order_data['id'],
                    'order_status': order_data['order_status']['code'],
                    'order_partner_id': zid_customer.id,
                    'partner_location_id': zid_customer.customer_partner_id.id,
                    'delivery_address_id': customer_location.id,
                    # 'invoice_address_id': billing_address.id,
                    # 'owner_id':order.scheduler_log_id.instance_id.owner_id.id,
                    'instance_id': order.scheduler_log_id.instance_id.id,
                    # 'invoice_no': invoice_number,
                    # 'paid': item['paid'],
                    # 'total_tax': taxes_total if taxes_total > 0 else 0,
                    'order_datetime': datetime.strptime(order_data['created_at'].split(' ')[0], '%Y-%m-%d').date(),
                    'fulfillment_status': order_data['payment_status'],
                    'payment_method': order_data['payment']['method']['type'],
                    'subtotal_price': order_data['order_total'],
                    # 'discount_code': item['discountCode'],
                    # 'discount_type': item['discountType'],
                    # 'total_discount': item['discountAmount'],
                    # 'shipping_price': item['shippingAmount'],
                    # 'taxes': taxes['name'] if taxes else '',
                    'total_price': order_data['order_total'],
                    # 'schedule_id': schedule.id,
                    # 'item_id': item['id'],
                    # 'fiscal_position_id': account_fiscal_position_id,
                }
                _logger.info('Creating order with vals: %s' % zid_order_vals)
                order_record = order_objs.create(zid_order_vals)

                if order_record:
                    _logger.info('Order created! Order ID: %s, processing other items' % order[0])
                    # order.store_location_id = store_location_id.id
                    # order.status = 'done'
                    # order.scheduler_log_id.completed_lines += 1
                    # Calculating number of order lines linked to the order
                    order.line_count = full_order_data['products_count']
                    common_functions.update_scheduler_log_state(order.scheduler_log_id)
                    # Creating Order Line Logs
                    self.create_order_line_scheduler_data(order_record.id, full_order_data['products'], order.id)
            except Exception as e:
                _logger.error(str(e))
                _logger.error("Order Creation Failed!!")
    def create_order_line_scheduler_data(self,order_record_id, order_lines, order_scheduler_id):
        """
        Helper function to create order lines in scheduler
        :param order_record_id: id if zid.order record
        :param order_lines: order lines dictionary
        """
        for order_line in order_lines:
            order_line_scheduler_vals = {
                'status' : 'draft',
                'data' : {'data' : [order_line]},
                'scheduler_order_id' : order_scheduler_id,
                'order_id' : order_record_id
            }
            self.env['zid.scheduler.order.line'].create(order_line_scheduler_vals)


    def get_full_order_detail(self,order_id, scheduler_log_id):
        """
        Helper function to get all the detail of the order
        :param order_id: zid id of the order
        :param scheduler_log_id: scheduler log object
        :return: dictionary containing complete data of order
        """
        instance = scheduler_log_id.instance_id.id
        url = f"https://api.zid.sa/v1/managers/store/orders/{order_id}/view"
        headers = common_functions.fetch_authentication_details(self, instance)
        response = requests.get(url, headers=headers)
        return response.json()['order']