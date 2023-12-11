from odoo import models, fields
from ..models import common_functions


class Create_Scheduler_log(models.TransientModel):
    _name =  'wizard.scheduler.log'
    _description = 'Wizard to create log in zid scheduler'

    scheduler_type = fields.Selection([('product', 'Product'),
                                       ('store_locations', 'Store Locations'),('product_attributes', 'Product Attributes'),
                                       ('category', 'Category')],
                                      string="Scheduler Type", tracking=True)

    def create_scheduler_log(self):
        create_log_for = [self.scheduler_type]
        zid_instance = self.env['zid.instance.ept'].browse(self.env.context.get('active_id'))
        common_functions.create_log_in_scheduler(self, zid_instance, create_log_for)
        # data_for_log = {
        #     'scheduler_type': self.scheduler_type,
        #     'instance_id': self.env.context.get('active_id'),
        #     'status': 'draft',
        #     'attempts': 0
        # }
        # self.env['zid.scheduler.log.line'].create(data_for_log)
        return True