# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ZidSchedulerOrderLine(models.Model):
    _name = 'zid.scheduler.order.line'
    _description = 'Zid Order Line Scheduler '
    _inherit = ['mail.thread', 'mail.activity.mixin']

    status = fields.Selection([('draft', 'Draft'), ('progress', 'In Progess'), ('done', 'Done'), ('failed', 'Failed')],
                              string="Status", tracking=True, default='draft', readonly=True)
    data = fields.Text(string="Json Data", readonly=True)
    scheduler_order_id = fields.Many2one('zid.scheduler.order', 'Order', readonly=True)
    locations = fields.Char('Location', readonly=True) # TODO: verify fields
    header = fields.Char('Header', readonly=True)
    lines = fields.Integer('Lines', readonly=True)
    order_id = fields.Many2one('zid.order.ept','Zid Order')

