# -*- coding: utf-8 -*-
from odoo import models, fields
from . import common_functions
import ast, logging

_logger = logging.getLogger(__name__)

class ZidProductCategoryScheduler(models.Model):
    _name = 'zid.product.category.scheduler'
    _description = 'Zid Product Category Scheduler'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    status = fields.Selection([('draft', 'Draft'), ('progress', 'In Progess'), ('done', 'Done'), ('failed', 'Failed')],
                              string="Status", tracking=True, default='draft', readonly=True)
    data = fields.Text(string="Json Data", readonly=True)
    product_category_id = fields.Many2one('zid.product.category', string='Product Category', readonly=True)
    scheduler_log_id = fields.Many2one('zid.scheduler.log.line', string="Scheduler Log", readonly=True)

    def create_zid_product_category(self):
        """
        Function to create record in zid product category
        :return:
        """
        draft_product_category = self.search([('status', '=', 'draft')])
        category_objs = self.env['zid.product.category']
        _logger.info("Creating Product Category")
        for product_category in draft_product_category:
            try:
                product_category.status = 'progress'
                input_string = product_category['data']
                category = ast.literal_eval(input_string)

                vals ={
                    'name' : category['name'],
                    'zid_category_id': category['id'],
                    'uuid' : category['uuid'],
                    'Zid_product_category_url' : category['url'],
                    'parent_category_id' : category['parent_id'],
                    'owner_id' : product_category.scheduler_log_id.instance_id.owner_id.id
                }

                zid_product_category = category_objs.create(vals)

                if zid_product_category:
                    product_category.product_category_id = zid_product_category.id
                    product_category.status = 'done'
                    product_category.scheduler_log_id.completed_lines += 1
                    _logger.info(f"Product Category with Zid Id {category['id']} created")
                    common_functions.update_scheduler_log_state(product_category.scheduler_log_id)
                    if len(category['sub_categories']):
                        instance = product_category.scheduler_log_id.instance_id
                        for sub_category in category['sub_categories']:
                            common_functions.create_log_in_scheduler(self, instance,['category'], json_data={'data':[sub_category]} )
                else:
                    product_category.status = 'failed'
            except Exception as e:
                _logger.error(str(e))
                _logger.error(f"Product Category with Zid Id {category['id']} creation failed")




