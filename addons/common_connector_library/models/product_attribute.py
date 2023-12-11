# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    def get_attribute(self, attribute_string, attribute_type='radio', create_variant='always', auto_create=False):
       
        attributes = self.search([('name', '=ilike', attribute_string),
                                  ('create_variant', '=', create_variant)], limit=1)
        if not attributes and auto_create:
            return self.create(({'name': attribute_string, 'create_variant': create_variant,
                                 'display_type': attribute_type}))
        return attributes
