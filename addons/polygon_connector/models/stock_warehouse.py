from odoo import models, fields

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    warehouse_incharge = fields.Many2one('res.users', string='Warehouse Incharge', copy=False, index=True)