from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    owner_id = fields.Many2one('res.partner', string='Product Owner', readonly=True, copy=False, domain=[('client_type', '=', 'polygon_client')])
    billed_id = fields.Integer(string='Billing Invoice', readonly=True, copy=False, default=None)
    online_order_id = fields.Char(string='Online Order ID', readonly=True, copy=False, default=None)
    online_source = fields.Char(string='Online Source', readonly=True, copy=False, default=None)
    attempts = fields.Integer(string='Attempts', readonly=True, copy=False, default=0)
    last_attempt = fields.Datetime(string='Last Attempt', readonly=True, copy=False, default=None)
    instance_id = fields.Many2one('polygon.instance', string='Instance', readonly=True, copy=False, default=None)
    zid_instance_id = fields.Many2one('zid.instance.ept', string='Zid Instance')

