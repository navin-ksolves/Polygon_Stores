# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo import models, fields, api, _

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    #shopify_instance_id = fields.Many2one("shopify.instance.ept", string="Instance")

    def write(self, vals):
        
        if 'active' in vals.keys():
            shopify_product_template_obj = self.env['shopify.product.template.ept']
            for template in self:
                shopify_templates = shopify_product_template_obj.search(
                    [('product_tmpl_id', '=', template.id)])
                if vals.get('active'):
                    shopify_templates = shopify_product_template_obj.search(
                        [('product_tmpl_id', '=', template.id), ('active', '=', False)])
                shopify_templates.write({'active': vals.get('active')})
        res = super(ProductTemplate, self).write(vals)
        return res


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    shopify_instance_id = fields.Many2one("shopify.instance.ept", string="Instance")
    seq = fields.Char(string='Number', copy=False)
    is_update_shopify_qty = fields.Boolean("Update QTY to Shopify",
                                           help="Internal field used to indentify the qty is to be updated to shopify "
                                                "or not. If True it will update the qty to shopify else will not")
    
    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            val['seq'] = self.env['ir.sequence'].next_by_code('product.product') or _('New')
            if not val.get('default_code'):
                val['default_code'] =  str(val.get('seq'))
            if  val.get('default_code'):
                val['default_code'] =  val.get('default_code') + str(val.get('seq'))
            if val.get('barcode'):
                val['barcode'] = val.get('barcode') + str(val.get('seq'))
            #else:
                #val['barcode'] =  str(val.get('seq'))
        return super(ProductProduct, self).create(vals)

    def write(self, vals):
        
        if 'active' in vals.keys():
            shopify_product_product_obj = self.env['shopify.product.product.ept']
            for product in self:
                shopify_product = shopify_product_product_obj.search(
                    [('product_id', '=', product.id)])
                if vals.get('active'):
                    shopify_product = shopify_product_product_obj.search(
                        [('product_id', '=', product.id), ('active', '=', False)])
                shopify_product.write({'active': vals.get('active')})
        res = super(ProductProduct, self).write(vals)
        return res
