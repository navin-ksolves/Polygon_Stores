from odoo import models, fields, api
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger("Polygon Client Company")

class PolygonClientCompany(models.Model):
    _name = 'polygon.client.company'
    _description = 'Polygon Client'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Client Name', required=True, copy=False, index=True, tracking=True)
    sales_team_id = fields.Many2one('crm.team', string='Sales Team for Access Management', readonly=True, copy=False, tracking=True)
    is_b2b_enabled = fields.Boolean(string='B2B Enabled', default=False, copy=False, tracking=True)
    is_b2c_enabled = fields.Boolean(string='B2C Enabled', default=False, copy=False, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True, copy=False, 
                                 domain=[('is_company', '=', True), ('client_type', '=', 'polygon_client')], tracking=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True, copy=False, required=True, 
                                 default=lambda self: self.env.company.id, tracking=True)
    country_id = fields.Many2one('res.country', string='Country', copy=False, required=True, tracking=True)
    state_id = fields.Many2one('res.country.state', string='State', copy=False, required=True,
                               domain="[('country_id', '=', country_id)]", tracking=True)
    street = fields.Char(string='Street', required=False, copy=False)
    street2 = fields.Char(string='Street2', required=False, copy=False)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', readonly=True, copy=False, required=False,
                                    default=lambda self: self.env['stock.warehouse']
                                    .search([('company_id', '=', self.env.user.company_id.id)], limit=1).id, tracking=True)
    vat = fields.Char(string='VAT', required=False, copy=False, tracking=True)
    phone = fields.Char(string='Phone', required=False, copy=False, tracking=True)
    email = fields.Char(string='Email', required=False, copy=False, tracking=True)
    website = fields.Char(string='Website', required=False, copy=False, tracking=True)
    current_contract = fields.Many2one('polygon.client.contracts', string='Current Contract', readonly=True, copy=False, 
                                       domain=[('active', '=', True)], tracking=True)
    active = fields.Boolean(string='Active', default=True, copy=False, tracking=True)
    polygon_sales_id = fields.Many2one('res.users', string='Account Manager', readonly=True, copy=False, tracking=True)

    @api.model
    def create(self, vals):

        # Check if client already exists:
        client = self.env['polygon.client.company'].search([('name', '=', vals['name'])])
        client_vat = self.env['polygon.client.company'].search([('vat', '=', vals['vat'])])
        if client or client_vat:
            _logger.warning("Client already exists with Client - %s", vals['name'], exc_info=True)
            raise ValidationError("Client already exists with Client - %s", vals['name'])
        
        else:

            # Get the company id of the user trying to create the client
            company_id = self.env.user.company_id.id
            vals['company_id'] = company_id

            # Create a sales team
            sales_team = self.create_sales_team(vals)

            # Update the sales team in the client
            vals['sales_team_id'] = sales_team.id

            # Crate a contact in Res Partner
            contact_id = self.env['res.partner'].create({'name': vals['name'], 'is_company': True, 'company_id': self.env.user.company_id.id,
                                                         'client_type': 'polygon_client', 'country_id': vals['country_id'], 
                                                         'state_id': vals['state_id'], 'team_id': sales_team.id,
                                                         'street': vals['street'], 'street2': vals['street2'], 'vat': vals['vat'],
                                                         'phone': vals['phone'], 'email': vals['email'],
                                                         'website': vals['website']})

            vals['partner_id'] = contact_id.id

            # Create a client
            client = super(PolygonClientCompany, self).create(vals)

            # Update the client_id in the sales_team crm
            sales_team.client_id = client.id
            sales_team.is_polygon_client = True
            client.sales_team_id = sales_team.id

            _logger.info("Client Created - %s", vals['name'], exc_info=True)

        return client

    def create_sales_team(self, vals):
        
        # Create a sales team based on the client's name
        sales_team_name = f"{vals['name']}"
        sales_team = self.env['crm.team'].create({'name': sales_team_name, 
                                                  'company_id': self.company_id, 
                                                  'display_name': sales_team_name,
                                                  'is_polygon_client': True})

        _logger.info("Sales Team Created - %s", sales_team, exc_info=True)
        
        return sales_team