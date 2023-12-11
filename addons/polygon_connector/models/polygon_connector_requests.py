from odoo import models, fields, api
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger("Polygon Connector Requests")

class PolygonConnectorRequests(models.Model):
    _name = 'polygon.connector.requests'
    _description = 'Polygon Connector Requests List'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    client_id = fields.Many2one('polygon.client.company', string='Client ID', required=False, copy=False, index=True, domain="[('active', '=', True)]")
    name = fields.Char(string='Request Name', required=True, copy=False, index=True)
    request_description = fields.Text(string='Request Description', required=True, copy=False, index=True)
    requested_by = fields.Selection([('client', 'Client'),
                                     ('polygon', 'Polygon')
                                ], string='Requested By', default='client', copy=False, required=False, tracking=True)
    status = fields.Selection([('pending', 'Pending'),
                               ('evaluation', 'Evaluation'),
                                ('approved', 'Approved'),
                                ('rejected', 'Rejected'),
                                ('completed', 'Completed'),
                                ('cancelled', 'Cancelled'),
                                ('existing', 'Existing')
                                ], string='Request Status', default='pending', copy=False, required=True, tracking=True)
    connector_id = fields.Many2one('polygon.connector.types', string='Connector ID', required=False, copy=False, index=True, tracking=True, domain="[('active', '=', True)]")
            
    
    @api.model
    def create(self, vals):
        # Get the user_id
        user = self.env.user

        if user.polygon_user_type == 'client_user':
            vals['requested_by'] = 'client'
        else:
            vals['requested_by'] = 'polygon'

        vals['status'] = 'pending'

        if vals['connector_id']:
            # Check if client_id is present
            if vals['client_id']:
                # Check if another request already exists for the same client and connector
                request = self.env['polygon.connector.requests'].search([('client_id', '=', vals['client_id']), ('connector_id', '=', vals['connector_id'])])

                if request:
                    raise ValidationError("Request already exists for the same client and connector!")

                
        return super(PolygonConnectorRequests, self).create(vals)