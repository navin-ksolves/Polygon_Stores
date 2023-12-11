from odoo import api, fields, models


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def action_apply_inventory(self):
        super(StockQuant, self).action_apply_inventory()
        self.mapped('product_id').write({'is_update_shopify_qty': True})
