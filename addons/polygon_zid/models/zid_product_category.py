# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.exceptions import ValidationError
import ast, logging

_logger = logging.getLogger(__name__)

class ZidProductCategory(models.Model):
    _name = 'zid.product.category'
    _description = 'Zid Product Category'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    zid_category_id = fields.Char(string='Product Category ID', required=True, tracking=True)
    uuid = fields.Char(string='UUID')
    Zid_product_category_url = fields.Char(string='Product Category URL', required=False, tracking=True)
    parent_category_id = fields.Char(string='Parent Category', tracking=True)
    category_id = fields.Many2one('product.category', string='Category', tracking=True)
    owner_id = fields.Many2one('res.partner', string='Owner', required=True, tracking=True,
                               domain="[('is_company', '=', True)]")

    def create(self, vals):
        _logger.info("Creating Zid Product Category")
        # Check if parent category exists:
        if vals.get('parent_category_id'):
            parent_category = self.search([('zid_category_id', '=', vals['parent_category_id'])])
            if not parent_category:
                raise ValidationError('Parent category does not exist.')
        # Check if category and owner combination exists:
        product_category = self.search([('name', '=', vals['name']),('owner_id', '=', vals['owner_id'])])
        if product_category:
            product_category.write({'name': vals['name'],
                                    'owner_id': vals['owner_id'],
                                    'parent_category_id': vals.get('parent_category_id')})
            return product_category

        # Create odoo product category:
        # Check if category exists:
        product_category_obj = self.env['product.category']
        category = product_category_obj.search([('name', '=', vals['name']),
                                                ('product_category_owner', '=', vals['owner_id']),
                                                ('is_online_product_category', '=', True)])

        # parent_category = category.parent_id.id

        if category:
            vals['category_id'] = category.id
        else:
            product_category_vals = {'name': vals['name'],
                                     'product_category_owner': vals['owner_id'],
                                     'is_online_product_category': True,
                                    }

            if vals.get('parent_category_id'):
                parent_category = self.search([('zid_category_id', '=', vals['parent_category_id'])])
                if parent_category:
                    product_category_vals['parent_id'] = parent_category.category_id.id

            category = product_category_obj.create(product_category_vals)
            vals['category_id'] = category.id

        product_category = super(ZidProductCategory, self).create(vals)
        _logger.info('Product Category created - %s', product_category)

        return product_category


