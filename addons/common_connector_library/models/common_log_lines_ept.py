# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class CommonLogLineEpt(models.Model):
    _name = "common.log.lines.ept"
    _description = "Common log line"

    product_id = fields.Many2one('product.product', 'Product')
    order_ref = fields.Char('Order Reference')
    default_code = fields.Char('SKU')
    log_book_id = fields.Many2one('common.log.book.ept', ondelete="cascade")
    message = fields.Text()
    model_id = fields.Many2one("ir.model", string="Model")
    res_id = fields.Integer("Record ID")
    mismatch_details = fields.Boolean(string='Mismatch Detail', help="Mismatch Detail of process order")
    file_name = fields.Char()
    sale_order_id = fields.Many2one(comodel_name='sale.order', string='Sale Order')
    log_line_type = fields.Selection(selection=[('success', 'Success'), ('fail', 'Fail')],default='fail')

    @api.model
    def get_model_id(self, model_name):
       
        model = self.env['ir.model'].search([('model', '=', model_name)])
        if model:
            return model.id
        return False

    def create_log_lines(self, message, model_id, res_id, log_book_id, default_code='', order_ref='', product_id=False):
        
        vals = {'message': message,
                'model_id': model_id,
                'res_id': res_id.id if res_id else False,
                'log_book_id': log_book_id.id if log_book_id else False,
                'default_code': default_code,
                'order_ref': order_ref,
                'product_id': product_id
                }
        log_line = self.create(vals)
        return log_line


