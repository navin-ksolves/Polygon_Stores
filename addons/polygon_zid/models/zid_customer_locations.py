# -*- coding: utf-8 -*-
from odoo import models, fields


class ZidCustomerLocations(models.Model):
    _name = 'zid.customer.locations'
    _description = 'Zid Customer Locations'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", required=True, tracking=True)
    customer_id = fields.Many2one('zid.customer.ept', string="Customer", required=True, tracking=True)
    address_id = fields.Many2one('res.partner', string="Address", tracking=True)
    street = fields.Char(string="Street", tracking=True)
    street2 = fields.Char(string="Street 2", tracking=True)
    # city = fields.Char(string="City", tracking=True)
    # state = fields.Char(string="State", tracking=True)
    # country = fields.Char(string="Country", tracking=True)
    is_billing = fields.Boolean(string="Is Billing", default=False, tracking=True)
    is_shipping = fields.Boolean(string="Is Shipping", default=False, tracking=True)
    active = fields.Boolean(string="Active", default=True, tracking=True)
    state = fields.Many2one('zid.state.master', 'City', tracking=True)
    country = fields.Many2one('zid.country.master', 'Country', tracking=True)
