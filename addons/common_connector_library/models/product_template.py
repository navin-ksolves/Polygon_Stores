# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    ept_image_ids = fields.One2many('common.product.image.ept', 'template_id', string='Product Images')
    x_product_owner = fields.Many2one('res.partner', string="Product Owner")

    
    def prepare_template_common_image_vals(self, vals):
        
        image_vals = {"sequence": 0,
                      "image": vals.get("image_1920", False),
                      "name": self.name,
                      "template_id": self.id}
        return image_vals

    @api.model
    def create(self, vals):
        
        res = super(ProductTemplate, self).create(vals)
        if vals.get("image_1920", False) and res:
            image_vals = res.prepare_template_common_image_vals(vals)
            self.env["common.product.image.ept"].with_context(main_image=True).create(image_vals)
        return res

    def write(self, vals):
       
        res = super(ProductTemplate, self).write(vals)
        if vals.get("image_1920", False) and self:
            common_product_image_obj = self.env["common.product.image.ept"]
            for record in self:
                if vals.get("image_1920"):
                    image_vals = record.prepare_template_common_image_vals(vals)
                    common_product_image_obj.with_context(main_image=True).create(image_vals)
        return res
