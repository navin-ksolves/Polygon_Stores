from odoo import models, fields, api

import logging

_logger = logging.getLogger("Conversion Engine Log")

class CengineLogBookEpt(models.Model):
    _name = "cengine.log.book"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = 'id desc'
    _description = "Common log book Ept"

    name = fields.Char(readonly=True)
    type = fields.Selection([('import', 'Import'), ('export', 'Export')], string="Operation")
    log_lines = fields.One2many('common.log.lines.ept', 'log_book_id')
    message = fields.Text()
    model_id = fields.Many2one("ir.model", help="Model Id", string="Model")
    res_id = fields.Integer(string="Record ID", help="Process record id")
    attachment_id = fields.Many2one('ir.attachment', string="Attachment")
    file_name = fields.Char()
    sale_order_id = fields.Many2one(comodel_name='sale.order', string='Sale Order')

    @api.model
    def create(self, vals):
      
        seq = self.env['ir.sequence'].next_by_code('common.log.book.ept') or '/'
        vals['name'] = seq
        return super(CengineLogBookEpt, self).create(vals)

    def create_common_log_book(self, process_type, instance_field, instance, model_id, module):
       
        log_book_id = self.create({"type": process_type,
                                   #"module": module,
                                   instance_field: instance.id,
                                   "model_id": model_id,
                                   "active": True})
        return log_book_id
