from odoo import models, fields, api
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger("Polygon Connector Clients")

class PolygonConnectorClients(models.Model):
    _name = 'polygon.connector.clients'
    _description = 'Polygon Connector Clients List'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Client Name', copy=False, index=True)
    client_id = fields.Many2one('polygon.client.company', string='Client ID', required=True, tracking=True, copy=False, index=True, domain="[('active', '=', True)]")
    connector_id = fields.Many2one('polygon.connector.types', string='Connector ID', required=True, tracking=True, copy=False, index=True, domain="[('active', '=', True)]")
    active = fields.Boolean(string='Active', default=True, copy=False, tracking=True)

    # Client cannot have duplicate connectors
    @api.model
    def create(self, vals):
        connector = self.env['polygon.connector.clients'].search([('client_id', '=', vals['client_id']), ('connector_id', '=', vals['connector_id'])])
        if connector:
            _logger.info("Client cannot have duplicate connectors")
            raise ValidationError("Client cannot have duplicate connectors")
        
        # Get the client name
        client_name = self.env['polygon.client.company'].browse(vals['client_id'])

        connector_name = self.env['polygon.connector.types'].browse(vals['connector_id'])

        # Generate a connector integration name
        vals['name'] = client_name.name + " - " + connector_name.name
        
        return super(PolygonConnectorClients, self).create(vals)