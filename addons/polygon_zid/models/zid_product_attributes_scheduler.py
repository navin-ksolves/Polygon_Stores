# -*- coding: utf-8 -*-
from odoo import models, fields
import ast
from . import common_functions
import logging

_logger = logging.getLogger(__name__)

class ZidProductAttributeScheduler(models.Model):
    _name = 'zid.product.attributes.scheduler'
    _description = 'Zid Product Attributes Scheduler'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    status = fields.Selection([('draft', 'Draft'), ('progress', 'In Progess'), ('done', 'Done'), ('failed', 'Failed')],
                              string="Status", tracking=True, default='draft', readonly=True)
    data = fields.Text(string="Json Data", readonly=True)
    product_attribute_id = fields.Many2one('zid.product.attributes', string='Product Attribute', readonly=True)
    scheduler_log_id = fields.Many2one('zid.scheduler.log.line', string="Scheduler Log", readonly=True)
    attribute_value_count = fields.Integer('Value Count', readonly=True)
    completed_attribute_value = fields.Integer('Completed', readonly=True)
    attempts = fields.Integer("Scheduler Attempts")

    def create_zid_product_attributes_record(self, args={}):
        """
        Function to create record in zid product attributes
        :return:
        """
        record_limit = args.get('limit')
        draft_attributes = self.search(['|', '&', ('status','=','failed'),('attempts','<', 3),('status', '=', 'draft')], limit = record_limit)
        attribute_objs = self.env['zid.product.attributes']

        for attribute in draft_attributes:
            try:
                attribute.status = 'progress'
                # attribute.attempts += 1
                input_string = attribute['data']
                attr = ast.literal_eval(input_string)
                product_attribute = self.env['product.attribute'].search([('name', '=', attr['name'])])
                zid_product_attribute = attribute_objs.search([('zid_attribute_id', '=', attr['id'])])

                if not product_attribute:
                    # Creating product.attribute record
                    product_attribute = self.env['product.attribute'].create({'name': attr['name'],
                                                                              'create_variant': 'always',
                                                                              'display_type': 'select'})
                if not zid_product_attribute:
                    vals = {
                        'zid_attribute_id': attr['id'],
                        'name': attr['name'],
                        'product_attribute_id': product_attribute.id
                    }
                    zid_product_attribute = attribute_objs.create(vals)
                attribute_values = attr['presets']
                # creating attribute value scheduler record from presets in the data
                self.create_attribute_value_scheduler_record(attribute_values, attribute)

                if zid_product_attribute:
                    attribute.product_attribute_id = zid_product_attribute.id or zid_product_attribute.id
                    # attribute.scheduler_log_id.completed_lines += 1
                    attribute.attribute_value_count = attr['preset_count']
                    _logger.info('Product Attribute Created!!')
                    # common_functions.update_scheduler_log_state(attribute.scheduler_log_id)
            except Exception as e:
                attribute.status = 'failed'
                _logger.error(str(e))
                return False

    def create_attribute_value_scheduler_record(self, attribute_values, attribute):
        """
        Helper function to create record in attribute.value.scheduler from attribute.value data
        :param attribute_values: dictionary containing values of attribute
        """
        for attribute_value in attribute_values:
            values = {
                'status': 'draft',
                'data': attribute_value,
                'scheduler_log_id': attribute.scheduler_log_id.id,
                'attribute_scheduler_id': attribute.id
            }
            self.env['zid.product.attribute.value.scheduler'].create(values)
        return True



