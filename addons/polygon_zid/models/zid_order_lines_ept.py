# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ZidOrderLinesEpt(models.Model):
    _name = 'zid.order.lines.ept'
    _description = 'Zid Order Lines Ept'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Order Line Name", required=True, tracking=True)
    order_id = fields.Many2one('zid.order.ept', string="Order", tracking=True, required=True, index=True)
    so_line_id = fields.Many2one('sale.order.line', string="Sale Order Line", tracking=True, required=False, index=True)
    product_id = fields.Many2one('product.product', string="Product", tracking=True, required=True, index=True)
    item_id = fields.Many2one('zid.product.template', string="Item", tracking=True, required=True, index=True)
    sku = fields.Char(string="SKU", tracking=True, required=False)
    quantity = fields.Float(string="Quantity", tracking=True)
    price = fields.Float(string="Price", tracking=True)
