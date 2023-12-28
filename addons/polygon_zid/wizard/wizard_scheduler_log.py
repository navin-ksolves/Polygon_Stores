from odoo import models, fields
from ..models import common_functions
import requests

class Create_Scheduler_log(models.TransientModel):
    _name =  'wizard.scheduler.log'
    _description = 'Wizard to create log in zid scheduler'

    scheduler_type = fields.Selection([('product', 'Product'),('store_locations', 'Store Locations'),
                                       ('product_attributes', 'Product Attributes'),('category', 'Category'),
                                       ('order', 'Order'),('currency', 'Currency'),
                                       ('sync_states', 'States')],
                                      string="Scheduler Type", tracking=True)
    date_from = fields.Date('From', default=fields.Datetime.now())
    date_to = fields.Date('To', default=fields.Datetime.now())

    def create_scheduler_log(self):
        """
        Function to create log in scheduler_log from the data given in wizard
        """
        if self.scheduler_type != 'sync_states':
            create_log_for = [self.scheduler_type]
            zid_instance = self.env['zid.instance.ept'].browse(self.env.context.get('active_id'))
            common_functions.create_log_in_scheduler(self, zid_instance, create_log_for)
        else:
            countries = self.env['zid.country.master'].search([])
            for country in countries:
                instances = self.env['zid.instance.ept'].browse(self.env.context.get('active_id'))
                for instance in instances:
                    country_id = country.zid_country_id
                    url = f"https://api.zid.sa/v1/managers/cities/by-country-id/{country_id}"
                    headers = common_functions.fetch_authentication_details(self, instance.id)
                    response = requests.get(url, headers=headers)
                    if response.status_code == 200:
                        json_data = {'data': response.json()}
                        common_functions.create_log_in_scheduler(self, instance, create_log_for=['sync_states'],
                                                                 json_data=json_data)
