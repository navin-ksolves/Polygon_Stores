from odoo import models, fields, api

import logging

_logger = logging.getLogger("Polygon Instance")

class PolygonInstance(models.Model):
    _name = 'polygon.instance'
    _description = 'Polygon Instance'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, copy=False)
    connector_id = fields.Many2one('polygon.connector.clients', string='Connector Access ID', required=True,
                                copy=False, domain="[('active', '=', True)]")
    active = fields.Boolean(string='Active', default=True, copy=False)

class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    polygon_instance_id = fields.Many2one('polygon.instance', string='Polygon Instance', readonly=True, copy=False)