# -*- coding: utf-8 -*-
from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)


class ZidCustomer(models.Model):
    _name = 'zid.customer.ept'
    _description = 'Zid Customer EPT'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Customer Name", required=True, tracking=True)
    email = fields.Char(string="Email", required=True, tracking=True)
    phone = fields.Char(string="Phone", tracking=True)
    customer_partner_id = fields.Many2one('res.partner', string="Customer Partner", tracking=True)
    instance_id = fields.Many2one('zid.instance.ept', string="Instance", required=True, tracking=True)
    active = fields.Boolean(string="Active", default=True, tracking=True)

    def create(self, vals):
        # Check if customer present
        customer = self.search([('email','=', vals['email']), ('instance_id','=', vals['instance_id'])])
        if customer:
            # Update the customer details:
            customer.write(vals)
            _logger.info("Customer already exists! Hence updated")
            return customer
        # If not present create data in res.partner
        else:
            partner_obj = self.env['res.partner']
            customer_partner = partner_obj.sudo().search([('email', '=', vals['email'])], limit=1)
            if customer_partner:
                # Create the customer:
                vals['customer_partner_id'] = customer_partner.id
            else:
                # Create the customer in odoo:
                customer_partner =partner_obj.sudo().create({
                    'name': vals['name'],
                    'email': vals['email'],
                    'phone': vals['phone']
                })
                vals['customer_partner_id'] = customer_partner.id
        customer = super(ZidCustomer, self).create(vals)
        _logger.info("Customer created!")
        self.env.cr.commit()
        return customer

