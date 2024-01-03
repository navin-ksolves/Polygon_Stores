# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class ZidOrderEpt(models.Model):
    _name = 'zid.order.ept'
    _description = 'Zid Order Ept'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Order Name", required=True, tracking=True)
    online_order_id = fields.Integer(string="Online Order ID", tracking=True, required=True, index=True)
    order_partner_id = fields.Many2one('zid.customer.ept', string="Order Partner", tracking=True)
    partner_location_id = fields.Many2one('res.partner', string="Partner Location", tracking=True)
    so_id = fields.Many2one('sale.order', string="Sale Order", tracking=True, required=False, index=True)
    instance_id = fields.Many2one('zid.instance.ept', string="Instance", tracking=True, required=True, index=True)
    order_datetime = fields.Datetime(string="Order Date", tracking=True)
    fulfillment_status = fields.Selection([('fulfilled', 'Fulfilled'), ('pending', 'Unfulfilled')],
                                          string="Fulfillment Status", tracking=True, default='unfulfilled')
    financial_status = fields.Boolean(string="Financial Status", tracking=True)
    currency = fields.Many2one('res.currency', string="Currency", tracking=True,
                               default=lambda self: self.env.company.currency_id.id)
    payment_method = fields.Char(string="Payment Method", tracking=True)
    subtotal_price = fields.Float(string="Subtotal Price", tracking=True)
    discount_code = fields.Char(string="Discount Code", tracking=True)
    discount_type = fields.Char(string="Discount Type", tracking=True)
    total_discount = fields.Float(string="Total Discount", tracking=True)
    shipping_method = fields.Char(string="Shipping Method", tracking=True)
    shipping_price = fields.Float(string="Shipping Price", tracking=True)
    taxes = fields.Char(string="Taxes", tracking=True)
    total_tax = fields.Float(string="Total Tax", tracking=True)
    total_price = fields.Float(string="Total Price", tracking=True)
    delivery_address_id = fields.Many2one('zid.customer.locations','Delivery Address')
    order_status = fields.Char('Zid Order Status')
    zid_order_line_ids = fields.One2many('zid.order.lines.ept','order_id', string='Zid Order Lines')

    def create(self, vals):
        # Check if order already exists
        order = self.search(
            [('online_order_id', '=', vals['online_order_id']), ('instance_id', '=', vals['instance_id'])], limit=1)
        if order:
            # Update the order if present
            order.write(vals)
            _logger.info("Order already exists! Hence updated")
            return order
        else:
            instance = self.env['zid.instance.ept'].sudo().search([('id', '=', vals['instance_id'])])
            so_obj = self.env['sale.order']
            so_id = so_obj.search([('name', '=', vals['name']), ('zid_instance_id', '=', vals['instance_id'])])
            if so_id:
                vals['so_id'] = so_id.id
            else:
                so_vals = {
                    'name': 'Zid - ' + vals['name'],
                    'partner_id': vals['partner_location_id'],
                    'state': 'draft',
                    'online_order_id':vals['online_order_id'],
                    'owner_id': instance.polygon_client_id.partner_id.id,
                    'product_owner_id': instance.polygon_client_id.partner_id.id,
                    'instance_id': instance.polygon_instance_id.id,
                    'company_id': instance.company_id.id,
                    'warehouse_id': instance.warehouse_id.id,
                    'team_id': instance.sales_team_id.id,
                    'date_order': vals['order_datetime'],
                    'zid_instance_id': instance.id
                }
                so = so_obj.create(so_vals)
                if so:
                    vals['so_id'] = so.id
                    # _logger.error(f"Sale Order Creation Failed for zid order {vals['name']}")
            zid_order = super(ZidOrderEpt, self).create(vals)
            payment_status_vals = {
                'name' : vals['payment_method'],
                'zid_instance_id': instance.id
            }
            payment_gateway = self.env['zid.payment.gateway.ept'].create(payment_status_vals)

            financial_status_vals = {
                'financial_status': vals['fulfillment_status'],
                'payment_gateway_id': payment_gateway.id,
                'zid_instance_id': instance.id
            }
            self.env['zid.sale.auto.workflow.configuration.ept'].create(financial_status_vals)

            return zid_order


class InheritSaleOrder(models.Model):
    _inherit = "sale.order"

    zid_instance_id = fields.Many2one('zid.instance.ept', 'Zid Instance')