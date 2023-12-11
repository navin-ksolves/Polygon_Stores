# -*- coding: utf-8 -*-
from odoo import models, fields
from . import common_functions
import logging

_logger = logging.getLogger(__name__)


class ZidProductImage(models.Model):
    _name = 'zid.product.image'
    _description = 'Zid Product Image'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    zid_id = fields.Char('Zid Id')
    thumbnail_image_url = fields.Char('ThumbNail')
    medium_image_url = fields.Char('Medium Image')
    small_image_url = fields.Char('Small Image')
    full_size_image_url = fields.Char('Full Size Image')
    large_image_url = fields.Char('Large Image')
    alt_text = fields.Char('Alternate Text')
    display_order = fields.Integer('Display Order')
    zid_product_id = fields.Many2one('zid.product.template', string='Product')
