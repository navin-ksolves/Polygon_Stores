from odoo import models, fields

import logging

_logger = logging.getLogger("Conversion Engine Log Lines")

class CengineLogLinesEpt(models.Model):
    _name = 'cengine.log.lines'
    _description = 'Conversion Engine Log Lines'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    product_id = fields.Many2one('product.product', 'Product')
    ce_product_id = fields.Char('Product ID')
    order_ref = fields.Char('Order Reference')
    ce_order_ref = fields.Char('Order Reference')
    default_code = fields.Char('SKU')
    ce_product_code = fields.Char('SKU')
    log_book_id = fields.Many2one('cengine.log.book')
    message = fields.Text()
    res_id = fields.Integer("Record ID")
    mismatch_details = fields.Boolean(string='Mismatch Detail', help="Mismatch Detail of process order")
    file_name = fields.Char()
    sale_order_id = fields.Many2one(comodel_name='sale.order', string='Sale Order')
    log_line_type = fields.Selection(selection=[('success', 'Success'), ('fail', 'Fail')],default='fail')

    def create_log_lines(self, message, model_id, res_id, log_book_id, default_code='', order_ref='', product_id=False, ce_product_id='', ce_order_ref='', ce_product_code=''):
        
        vals = {'message': message,
                'model_id': model_id,
                'res_id': res_id.id if res_id else False,
                'log_book_id': log_book_id.id if log_book_id else False,
                'default_code': default_code,
                'order_ref': order_ref,
                'product_id': product_id,
                'ce_product_id': ce_product_id,
                'ce_order_ref': ce_order_ref,
                'ce_product_code': ce_product_code,
                }
        log_line = self.create(vals)
        return log_line