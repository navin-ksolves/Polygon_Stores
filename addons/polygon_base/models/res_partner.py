from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    client_type = fields.Selection([
        ('polygon_client', 'Polygon Client'),
        ('polygon_user', 'Polygon User'),
        ('customer', 'Customer'),
        ('supplier', 'Vendor'),
    ], string='Client Type', default='customer')

