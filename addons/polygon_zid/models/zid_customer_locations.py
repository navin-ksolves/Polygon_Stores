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
    phone = fields.Char('Phone')
    email = fields.Char('Email')

    def create(self, vals):
        address = super(ZidCustomerLocations, self).create(vals)
        city = self.env['zid.state.master'].browse(vals.get('state'))
        country = self.env['zid.country.master'].search([('zid_country_id','=',vals.get('county'))])
        partner_record = self.env['res.partner'].search([('id','=', address.customer_id.customer_partner_id.id)])
        if partner_record:
            partner_address_vals = {
                'parent_id':partner_record.id,
                'street': vals.get('street'),
                'city': city.display_name,
                'country_id': country.odoo_country.id if country else False,
                'type' : 'delivery' if vals['is_shipping'] else 'invoice',
                'email': vals.get('email'),
                'phone': vals.get('phone'),
                'name': vals.get('name')
            }
            odoo_address = partner_record.create(partner_address_vals)
            if odoo_address:
              address['address_id']  = odoo_address.id
        # Create address in res_partner record
        return address