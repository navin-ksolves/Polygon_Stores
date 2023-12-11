from odoo import api, fields, models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    shopify_instance_id = fields.Many2one('shopify.instance.ept', compute="_shopify_instance_id", store=True)

    @api.depends()
    def _shopify_instance_id(self):
        self.shopify_instance_id = self.env['shopify.instance.ept'].search([('id', '=', self.product_variant_id.shopify_instance_id.id)])
