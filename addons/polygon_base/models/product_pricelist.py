from odoo import models, fields


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    client_id = fields.Many2one('polygon.client.company', string='Client', readonly=True, copy=False, domain=[('is_polygon_client', '=', True)])
    sales_team_id = fields.Many2one('crm.team', string='Sales Team', readonly=True, copy=False, domain=[('is_polygon_client', '=', True)])