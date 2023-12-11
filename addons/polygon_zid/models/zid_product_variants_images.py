# -*- coding: utf-8 -*-
from odoo import models, fields


class ZidProductVariantsImages(models.Model):
    _name = 'zid.product.variants.images'
    _description = 'Zid Product Variants Images'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    url = fields.Char(string='URL', required=True, copy=False)
    active = fields.Boolean(string="Active", default=True, tracking=True)

    zid_id = fields.Char('Zid Id')
    thumbnail_image_url = fields.Char('ThumbNail')
    medium_image_url = fields.Char('Medium Image')
    small_image_url = fields.Char('Small Image')
    full_size_image_url = fields.Char('Full Size Image')
    large_image_url = fields.Char('Large Image')
    alt_text = fields.Char('Alternate Text')
    display_order = fields.Integer('Display Order')
    zid_product_id = fields.Many2one('zid.product.variants', string='Product Variant')

