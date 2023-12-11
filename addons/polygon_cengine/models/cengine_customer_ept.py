from odoo import models, fields, api

import logging

_logger = logging.getLogger("Conversion Engine - Customer Model")

class CengineCustomerEpt(models.Model):
    _name = 'cengine.customer.ept'
    _description = 'Conversion Engine Customer'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Customer Name", required=True, tracking=True)
    email = fields.Char(string="Email", required=True, tracking=True)
    phone = fields.Char(string="Phone", tracking=True)
    customer_partner_id = fields.Many2one('res.partner', string="Customer Partner", tracking=True)
    instance_id = fields.Many2one('cengine.instance.ept', string="Instance", tracking=True)
    active = fields.Boolean(string="Active", default=True, tracking=True)

    # Email is always unique to instance_id:
    _sql_constraints = [
        ('unique_email', 'unique(email, instance_id)', 'Email must be unique per instance!'),
    ]

    @api.model
    def create(self, vals):
        # Check if the customer already exists:
        customer = self.env['cengine.customer.ept'].sudo().search([('email', '=', vals['email']), ('instance_id', '=', vals['instance_id'])])

        if customer:
            # Update the customer details:
            customer.write(vals)
            _logger.info("Customer already exists! Hence updated")
            return customer
        else:
            # Search for the customer in odoo:
            customer_partner = self.env['res.partner'].sudo().search([('email', '=', vals['email'])], limit=1)

            if customer_partner:
                # Create the customer:
                vals['customer_partner_id'] = customer_partner.id
            else:
                # Create the customer in odoo:
                customer_partner = self.env['res.partner'].sudo().create({
                    'name': vals['name'],
                    'email': vals['email'],
                    'phone': vals['phone']
                })
                vals['customer_partner_id'] = customer_partner.id

        customer = super(CengineCustomerEpt, self).create(vals)
        _logger.info("Customer created!")
        self.env.cr.commit()
        return customer

class CengineCustomerLocations(models.Model):
    _name = 'cengine.customer.locations'
    _description = 'Conversion Engine Customer Locations'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", required=True, tracking=True)
    customer_id = fields.Many2one('cengine.customer.ept', string="Customer", required=True ,tracking=True)
    address_id = fields.Many2one('res.partner', string="Address", required=True, tracking=True)
    street = fields.Char(string="Street", tracking=True)
    street2 = fields.Char(string="Street 2", tracking=True)
    city = fields.Char(string="City", tracking=True)
    state = fields.Char(string="State", tracking=True)
    country = fields.Char(string="Country", tracking=True)
    is_billing = fields.Boolean(string="Is Billing", default=False, tracking=True)
    is_shipping = fields.Boolean(string="Is Shipping", default=False, tracking=True)
    active = fields.Boolean(string="Active", default=True, tracking=True)

    @api.model
    def create(self, vals):
        parent_id = self.env['cengine.customer.ept'].sudo().search([('id', '=', vals['customer_id'])])
        if vals['is_billing'] == True:
            type = 'invoice'
            # Check if address already exists:
            address = self.env['cengine.customer.locations'].sudo().search([
                ('name', '=', vals['name']), ('customer_id', '=', vals['customer_id']),
                ('street', '=', vals['street']), ('street2', '=', vals['street2']),
                ('state', '=', vals['state']),
                ('country', '=', vals['country']),
                ('is_billing', '=', True)])
        elif vals['is_shipping'] == True:
            type = 'delivery'
            # Check if address already exists:
            address = self.env['cengine.customer.locations'].sudo().search([
                ('name', '=', vals['name']), ('customer_id', '=', vals['customer_id']),
                ('street', '=', vals['street']), ('street2', '=', vals['street2']),
                ('state', '=', vals['state']),
                ('country', '=', vals['country']),
                ('is_shipping', '=', True)])
        
        # Get the country id from odoo:
        country_id = self.env['res.country'].sudo().search([('code', '=', vals['country'])], limit=1)

        # Get the state id from odoo:
        state_id = self.env['res.country.state'].sudo().search([('code', '=', vals['state']), 
                                                                ('country_id', '=', country_id.id)], limit=1)

        if address:
            # Update the address in odoo:
            address_partner = self.env['res.partner'].sudo().search([('id', '=', address.address_id.id)])
            
            address_partner.write({
                'name': vals['name'],
                'street': vals['street'],
                'street2': vals['street2'],
                'phone': vals['phone'],
                'city': vals['city'],
                'state_id': state_id.id if state_id else False,
                'country_id': country_id.id,
                'type': type
            })

            del vals['phone']

            # Update the address details:
            address.write(vals)
            _logger.info("Address already exists! Hence updated")
            return address
        
        else:

            address = self.env['res.partner'].sudo().create({
                'name': vals['name'],
                'street': vals['street'],
                'street2': vals['street2'],
                'phone': vals['phone'],
                'city': vals['city'],
                'state_id': state_id.id if state_id else False,
                'country_id': country_id.id,
                'type': type,
                'parent_id': parent_id.customer_partner_id.id
            })

            del vals['phone']
            vals['address_id'] = address.id

            # Create the address in conversion engine:
            address = super(CengineCustomerLocations, self).create(vals)

            _logger.info("Address created! - %s", address)

        self.env.cr.commit()

        return address