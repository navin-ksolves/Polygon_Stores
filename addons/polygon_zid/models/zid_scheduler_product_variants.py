# -*- coding: utf-8 -*-
from odoo import models, fields


class ZidProductVariantScheduler(models.Model):
    _name = 'zid.scheduler.products.variants'
    _description = 'Zid Product Variant Scheduler'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    status = fields.Selection([('draft', 'Draft'), ('progress', 'In Progess'), ('done', 'Done'), ('failed', 'Failed')],
                              string="Status", tracking=True, default='draft', readonly=True)
    data = fields.Text(string="Json Data", readonly=True)
    template = fields.Boolean('Template', readonly=True)
    attribute = fields.Boolean('Attribute', readonly=True)
    images = fields.Boolean('Images', readonly=True)
    scheduler_log_id = fields.Many2one('zid.scheduler.log.line', string="Scheduler Log", readonly=True)
    zid_product_variant_id = fields.Many2one('zid.product.variants', 'Product Variant', readonly=True)
    zid_product_scheduler_id = fields.Many2one('zid.scheduler.products', string='Product Scheduler', readonly=True)
