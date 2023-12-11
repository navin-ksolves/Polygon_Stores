from odoo import models, fields, api
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger("Polygon Client Users")

class PolygonClientUsers(models.Model):
    _name = 'polygon.client.users'
    _description = 'Polygon Client Users'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='User Name', required=True, copy=False, index=True, tracking=True)
    email = fields.Char(string='Email', required=True, copy=False, index=True, tracking=True)
    phone = fields.Char(string='Mobile Number', required=True, copy=False, tracking=True)
    client_id = fields.Many2one('polygon.client.company', string='Client', copy=False, domain="[('active', '=', True)]", tracking=True)
    user_id = fields.Many2one('res.users', string='User', readonly=True, copy=False)
    is_primary = fields.Boolean(string='Primary User', default=False, copy=False, tracking=True)
    sales_team = fields.Many2one('crm.team', string='Client Sales Team', readonly=True, copy=False, tracking=True)
    user_type = fields.Selection([('client_user', 'Client User'),
                                    ('client_admin', 'Client Admin')
                                ], string='User Type', default='client_user', copy=False, required=True, tracking=True)

    @api.model
    def create(self, vals):

        _logger.info("Creating Client User - %s", vals, exc_info=True)

        # Check if client already has primary:
        primary_user = self.env['polygon.client.users'].search([('client_id', '=', vals['client_id']), ('is_primary', '=', True)])
        if primary_user and vals['is_primary']:
            _logger.info("Client already has a primary user - %s", primary_user.name)
            raise ValidationError("Client already has a primary user")
        
        if not primary_user and not vals['is_primary']:
            _logger.info("First user needs to be a primary user", exc_info=True)
            raise ValidationError("First user needs to be a primary user")
            

        # Check if user exists:
        user = self.env['res.users'].search([('login', '=', vals['email'])])

        if user:
                _logger.info("User already exists with email - %s", vals['email'])
                raise ValidationError("User already exists with email - %s", vals['email'])

        else:
            user = super(PolygonClientUsers, self).create(vals)
            _logger.info("Polygon User created - Polygon Client User ID - %s", user.id, exc_info=True)
            # Create the user
            user_id = self.create_user({'name': vals['name'], 
                                        'login': vals['email'],
                                        'client_id': vals['client_id'],
                                        'phone': vals['phone'],
                                        'is_primary': vals['is_primary']})

            user.user_id = user_id.id
            user.sales_team = user_id.partner_id.team_id.id

            return user

    @api.model
    def create_user(self, vals):
            
            # Get the company_id of the user trying to create the client
            company_id = self.env.user.company_id.id

            # Create a user based on the users's name
            user_name = f"{vals['name']}"
            user_id = self.env['res.users'].create({'name': user_name, 'login': vals['login'],
                                                 'company_ids' : [(6, 0, [company_id])],
                                                 'company_id': company_id, 
                                                 'groups_id': [(6, 0, [self.env.ref('polygon_base.group_client_user').id])],
                                                 'polygon_user_type':'client_user'})
            _logger.info("System User created - User ID - %s", user_id.id, exc_info=True)
            
            # Get the partner id of the user
            partner_id = user_id.partner_id

            vals['user_id'] = user_id.id

            # Update the partner country and city to the client's country and city

            client = self.env['polygon.client.company'].browse(vals['client_id'])

            partner_id.write({'country_id': client.country_id.id,
                            'state_id': client.state_id.id,
                            'company_id': company_id,
                            'parent_id': client.partner_id.id,
                            'phone': vals['phone']})
            _logger.info("Partner Updated - Partner ID - %s", partner_id.id, exc_info=True)

            # Get the sales team id in the partner_id
            sales_team_id = self.env['crm.team'].search([('client_id', '=', client.id), ('is_polygon_client', '=', True)], limit=1)
            _logger.info("Sales Team Found - Sales Team ID - %s", sales_team_id.id, exc_info=True)

            # Add the user to the sales_team
            user_id.sale_team_id = sales_team_id.id
            sales_team_id.write({'member_ids': [(4, user_id.id)]})

            if vals['is_primary']:
                # Update the sales_team in the client
                sales_team_id.user_id = user_id.id

            # Update the sales_team in the partner
            partner_id.team_id = sales_team_id.id
            _logger.info("CRM Updated - %s", sales_team_id, exc_info=True)
            
            return user_id