from odoo import models, fields, api
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger("Polygon Connector Types")

class PolygonConnectorTypes(models.Model):
    _name = 'polygon.connector.types'
    _description = 'Polygon Connectors List'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Connector Name', required=True, copy=False, index=True, tracking=True)
    connector_type = fields.Selection([('internal', 'Internal Integration'),
                                    ('external', 'External Integration')
                                ], string='Connector Type', default='connector', copy=False, required=True, tracking=True)
    connector_description = fields.Text(string='Connector Description', required=True, copy=False)
    connector_url = fields.Char(string='Connector URL', required=True, copy=False, index=True, tracking=True)
    connector_model = fields.Many2one('ir.module.module', string='Connector Model', required=True, copy=False, index=True, tracking=True, ondelete='cascade', domain="[('state', '=', 'installed')]")
    active = fields.Boolean(string='Active', default=True, copy=False, tracking=True)
    connector_logo = fields.Binary(string='Connector Logo', copy=False)

    # Connector cannot have duplicate names
    @api.model
    def create(self, vals):
        connector = self.env['polygon.connector.types'].search([('connector_url', '=', vals['connector_url'])])
        if connector:
            _logger.info("Connector cannot have duplicate names")
            raise ValidationError("Connector cannot have duplicate names")
        return super(PolygonConnectorTypes, self).create(vals)