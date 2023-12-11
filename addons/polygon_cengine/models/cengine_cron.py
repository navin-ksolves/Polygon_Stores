from odoo import models, fields

class CengineScheduler(models.Model):
    _name = 'cengine.scheduler.ept'
    _description = 'Cengine Scheduler'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    schedule_type = fields.Selection([('order', 'Order'), ('product', 'Product'), ('contact', 'Contacts')], string="Schedule Type", tracking=True, readonly=True)
    instance_id = fields.Many2one('cengine.instance.ept', string="Instance", tracking=True, required=True, index=True, readonly=True)
    owner_id = fields.Many2one('res.partner', string="Owner", tracking=True, required=True, index=True, readonly=True)
    data = fields.Text(string="Data", readonly=True)
    record_count = fields.Integer(string="Record Count", tracking=True, required=True, index=True, readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('progress', 'In Progess'), ('done', 'Done'), ('failed','Failed')], string="State", tracking=True, default='draft', readonly=True)