from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_online_product = fields.Boolean(string="Is Online Product", default=False)
    product_owner = fields.Many2one('res.partner', string="Product Owner", domain="[('is_company', '=', True)]")

class ProductProduct(models.Model):
    _inherit = "product.product"

    is_online_product_variant = fields.Boolean(string="Is Online Product Variant", default=False)
    product_variant_owner = fields.Many2one('res.partner', string="Product Owner", domain="[('is_company', '=', True)]")

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            product_owner = self.env['product.template'].browse(val['product_tmpl_id']).product_owner
            val['product_variant_owner'] = product_owner.id
        return super(ProductProduct, self).create(vals)

class ProductCategory(models.Model):
    _inherit = "product.category"

    is_online_product_category = fields.Boolean(string="Is Online Product Category", default=False)
    product_category_owner = fields.Many2one('res.partner', string="Product Owner", domain="[('is_company', '=', True)]")
