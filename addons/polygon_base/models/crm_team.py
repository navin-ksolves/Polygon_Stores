from odoo import models, fields

class CrmTeam(models.Model):
    _inherit = 'crm.team'

    client_id = fields.Many2one('polygon.client.company', required=False, string='Client', readonly=True, copy=False, tracking=True)
    is_polygon_client = fields.Boolean(string='Is Polygon Client?', default=False, copy=False, tracking=True)