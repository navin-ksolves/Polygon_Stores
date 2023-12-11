# -*- coding: utf-8 -*-
from odoo import models, fields

class ZidProductVariants(models.Model):
    _name = 'zid.product.variants'
    _description = 'Zid Product Variants'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    name = fields.Char('Name')
    description = fields.Html(string='Description', tracking=True, translate=False)
    owner_id = fields.Many2one('res.partner', string='Owner', required=True, tracking=True, domain="[('is_company', '=', True)]")
    zid_instance_id	= fields.Many2one('zid.instance', string='Instance', required=True, tracking=True)
    zid_id = fields.Char('Zid Id')
    zid_sku = fields.Char(string='Zid SKU', required=True, tracking=True)
    zid_category_id = fields.Many2one('zid.product.category', string='Category')
    zid_parent_id = fields.Char('Zid Parent Id')
    zid_product_template_id = fields.Many2one('zid.product.template', string='Zid Product Template',
                                              required=True, tracking=True)
    zid_attribute_id = fields.Char('Attribute Id')
    options = fields.Char('Options')
    html_url = fields.Text('Html Url')
    requires_shipping = fields.Boolean(string='Requires Shipping',default=False, tracking=True)
    is_taxable = fields.Boolean(string='Is Taxable', default=False)
    structure = fields.Char('Structure')
    is_published = fields.Boolean('Published')
    product_variant_id = fields.Many2one('product.product', string='Product ID - Base Variant', required=False, tracking=True,
                                         index=True)
    product_template_id = fields.Many2one('product.template', string='Product Template')



    price = fields.Float(string='Price', required=True, tracking=True)
    sale_price = fields.Float(string='Sale Price', required=False, tracking=True)
    on_sale = fields.Boolean(string='On Sale', required=False, tracking=True)
    quantity = fields.Integer(string='Quantity', required=False, tracking=True)
    weight = fields.Float(string='Weight', required=False, tracking=True)


    active = fields.Boolean(string='Active', default=True, tracking=True)
