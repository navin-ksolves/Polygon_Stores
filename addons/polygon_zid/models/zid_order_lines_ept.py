# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class ZidOrderLinesEpt(models.Model):
    _name = 'zid.order.lines.ept'
    _description = 'Zid Order Lines Ept'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Order Line Name", required=True, tracking=True)
    order_id = fields.Many2one('zid.order.ept', string="Order", tracking=True, required=True, index=True)
    so_line_id = fields.Many2one('sale.order.line', string="Sale Order Line", tracking=True, required=False, index=True)
    product_id = fields.Many2one('product.product', string="Product", tracking=True, required=True, index=True)
    item_id = fields.Many2one('zid.product.template', string="Item", tracking=True, required=False, index=True)
    sku = fields.Char(string="SKU", tracking=True, required=False)
    quantity = fields.Float(string="Quantity", tracking=True)
    price = fields.Float(string="Price", tracking=True)
    zid_instance_id = fields.Many2one('zid.instance.ept', string="Instance", tracking=True, required=True, index=True)

    @api.model
    def create(self, vals):
        # find tax
        tax_percentage = 0
        if vals.get('tax_percentage'):
            tax_percentage = vals['tax_percentage']
            del vals['tax_percentage']
        tax_id = self.env["account.tax"].search([("type_tax_use", "=", "sale"), ("amount", "=", int(tax_percentage))], limit=1)

        # check if order line already exists
        existing_zid_order_line= self.search([('order_id','=', vals['order_id']),
                                              ('product_id','=',vals['product_id']),
                                              ('zid_instance_id','=',vals['zid_instance_id'])], limit=1)
        # if found only update the values
        if existing_zid_order_line:
            if vals.get('price_string'):
                del vals['price_string']
            existing_zid_order_line.write(vals)
            # if existing order line has odoo so line attached then update it's values
            if existing_zid_order_line.so_line_id:
                so_line_vals = {
                    'product_id': vals['product_id'],
                    'product_uom_qty': vals['quantity'],
                    'price_unit': vals['price'],
                }
                if tax_id:
                    so_line_vals['tax_id'] = tax_id.id
                else:
                    _logger.info(f"Tax with tax percentage = {tax_percentage} not found in Odoo!!")
                self.env['sale.order.line'].create(so_line_vals)
            return existing_zid_order_line
        # finding matching currency in odoo to use in sale order line
        if vals.get('price_string'):
            currency_name = vals.get('price_string').split(' ')[1]
            odoo_currency = self.env['res.currency'].search([('name','=', currency_name)])
            del vals['price_string']
        zid_order_line = super(ZidOrderLinesEpt, self).create(vals)
        zid_order = self.env['zid.order.ept'].browse(vals['order_id'])
        if zid_order:
            odoo_order_id = zid_order.so_id.id
            if not odoo_order_id:
                raise ValidationError("SO dosen't exist in Odoo")
        # create order line in odoo sale order
        so_line_vals = {
            'order_id': odoo_order_id,
            'product_id': vals['product_id'],
            'product_uom_qty': vals['quantity'],
            'price_unit': vals['price'],
        }
        if odoo_currency:
            so_line_vals['currency_id'] = odoo_currency.id
        if tax_id:
            so_line_vals['tax_id'] = tax_id.id
        else:
            _logger.info(f"Tax with tax percentage = {tax_percentage} not found in Odoo!!")

        odoo_sale_order_line = self.env['sale.order.line'].create(so_line_vals)
        # linking zid sale order line with odoo sale order line
        if odoo_sale_order_line:
            zid_order_line.so_line_id = odoo_sale_order_line.id
        return zid_order_line


