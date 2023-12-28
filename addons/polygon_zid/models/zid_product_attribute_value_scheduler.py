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
    attempts = fields.Integer("Scheduler Attempts")

    def create_zid_product_attribute_value_record(self, args={}):
        """
        Fuction to create record in zid.product.attribute.value
        :return: 
        """
        record_limit = args.get('limit')
        draft_attributes = self.search(['|', '&', ('status','=','failed'),('attempts','<', 3),('status', '=', 'draft')], limit = record_limit)
        attribute_value_objs = self.env['zid.product.attributes.values']
        for attribute_value in draft_attributes:
            try:
                attribute_value.status = 'progress'
                attribute_value.attempts += 1
                input_string = attribute_value['data']
                attr_value = ast.literal_eval(input_string)
                zid_product_attribute_value = attribute_value_objs.search([('value', '=', attr_value['value']),
                                                                    ('zid_attribute_id','=', attr_value['attribute_id'])])
                # if product_option_value:
                #     attribute_value.status = 'done'
                #     attribute_value.product_attribute_value_id =product_option_value.id
                #     attribute_value.attribute_scheduler_id.completed_attribute_value += 1
                #     _logger.info('Product Attribute Value Created!!')
                #     continue
                if not zid_product_attribute_value:
                    vals = {
                        'zid_attribute_id': attr_value['attribute_id'],
                        'value': attr_value['value'],
                    }
                    zid_product_attribute_value = attribute_value_objs.create(vals)

                if zid_product_attribute_value:
                    attribute_value.status = 'done'
                    # Updating attempt of attribute scheduler record
                    common_functions.update_log_line_attempts(self, 'zid.product.attribute.value.scheduler',
                                                              attribute_value.attribute_scheduler_id,
                                                              'attribute_scheduler_id')

                    # Update scheduler log line attempts
                    common_functions.update_log_line_attempts(self, 'zid.product.attributes.scheduler',
                                                              attribute_value.scheduler_log_id,
                                                              'scheduler_log_id')

                    # incrementing completed line of attribute scheduler
                    attribute_value.attribute_scheduler_id.completed_attribute_value += 1
                    # Checking if attribute completed & total line equal, if equal then status = 'done'
                    if attribute_value.attribute_scheduler_id.attribute_value_count==attribute_value.attribute_scheduler_id.completed_attribute_value:
                        attribute_value.attribute_scheduler_id.status = 'done'
                        # Incrementing scheduler log line completed log lines
                        attribute_value.scheduler_log_id.completed_lines += 1
                        # Updating status of scheduler log line
                        common_functions.update_scheduler_log_state(attribute_value.scheduler_log_id)

                _logger.info('Product Attribute Value Created!!')
            except Exception as e:
                attribute_value.status = 'failed'
                # Update attribute attempts
                common_functions.update_log_line_attempts(self, 'zid.product.attribute.value.scheduler',
                                                          attribute_value.attribute_scheduler_id,
                                                          'attribute_scheduler_id')
                # Update scheduler attempts
                common_functions.update_log_line_attempts(self, 'zid.product.attributes.scheduler',
                                                          attribute_value.scheduler_log_id,
                                                          'scheduler_log_id')

                _logger.error(str(e))
                _logger.info('Product Attribute Value Creation Failed!!')


    
    