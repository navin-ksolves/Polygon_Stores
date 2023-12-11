# -*- coding: utf-8 -*-
from odoo import models, fields
import ast
from . import common_functions
import logging

_logger = logging.getLogger(__name__)


class ZidProductAttributeValueScheduler(models.Model):
    _name = 'zid.product.attribute.value.scheduler'
    _description = 'Zid Product Attributes Value Scheduler'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    status = fields.Selection([('draft', 'Draft'), ('progress', 'In Progess'), ('done', 'Done'), ('failed', 'Failed')],
                              string="Status", tracking=True, default='draft', readonly=True)
    data = fields.Text(string="Json Data", readonly=True)
    product_attribute_value_id = fields.Many2one('zid.product.attributes.values', string='Product Attribute Value', readonly=True)
    scheduler_log_id = fields.Many2one('zid.scheduler.log.line', string="Scheduler Log", readonly=True)
    attribute_scheduler_id = fields.Many2one('zid.product.attributes.scheduler', string='Attribute Scheduler', readonly=True)

    def create_zid_product_attribute_value_record(self):
        """
        Fuction to create record in zid.product.attribute.value
        :return: 
        """
        draft_attributes = self.search([('status', '=', 'draft')])
        attribute_value_objs = self.env['zid.product.attributes.values']
        for attribute_value in draft_attributes:
            try:
                attribute_value.status = 'progress'
                input_string = attribute_value['data']
                attr_value = ast.literal_eval(input_string)
                product_option_value = attribute_value_objs.search([('value', '=', attr_value['value']),
                                                                    ('zid_attribute_id','=', attr_value['attribute_id'])])
                if product_option_value:
                    attribute_value.status = 'done'
                    attribute_value.product_attribute_value_id =product_option_value.id
                    attribute_value.attribute_scheduler_id.completed_attribute_value += 1
                    _logger.info('Product Attribute Value Created!!')
                    continue

                vals = {
                    'zid_attribute_id': attr_value['attribute_id'],
                    'value': attr_value['value'],
                }
                zid_product_attribute_value = attribute_value_objs.create(vals)

                if zid_product_attribute_value:
                    attribute_value.status = 'done'
                    attribute_value.attribute_scheduler_id.completed_attribute_value += 1
                    if attribute_value.attribute_scheduler_id.attribute_value_count==attribute_value.attribute_scheduler_id.completed_attribute_value:
                        attribute_value.attribute_scheduler_id.status = 'done'
                _logger.info('Product Attribute Value Created!!')
            except Exception as e:
                attribute_value.status = 'failed'
                _logger.error(str(e))
                _logger.info('Product Attribute Value Creation Failed!!')


    
    