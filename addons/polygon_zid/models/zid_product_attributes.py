# -*- coding: utf-8 -*-
from odoo import models, fields
import requests
from . import common_functions
import logging
_logger = logging.getLogger(__name__)



class ZidProductAttributes(models.Model):
    _name = 'zid.product.attributes'
    _description = 'Zid Product Attributes'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    zid_attribute_id = fields.Char('Zid Id', tracking=True)
    product_attribute_id = fields.Many2one('product.attribute', string="Product Attribute", required=False, tracking=True)

    def create_zid_product_attributes_sync_logs(self):
        """
        Creates task in zid.scheduler.log, with json data to sync product attribute for all the instances
        """
        instances = self.env['zid.instance.ept'].search([])
        for instance in instances:
            url = "https://api.zid.sa/v1/attributes/"
            headers = common_functions.fetch_authentication_details(self, instance.id)
            store_id = self.env['zid.tokens'].search(
                [('access_token', '=', instance.access_token)]).zid_request_id.store_id

            headers['Access-Token'] = headers.pop('X-Manager-Token')
            headers['Store-Id'] = store_id
            headers = {
                "Access-Token": headers['Access-Token'],
                "Store-Id": headers['Store-Id'],
                "Accept": "application/json"
            }

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                json_data = {'data': response.json()['results']}
                common_functions.create_log_in_scheduler(self, instance, ['product_attributes'], json_data=json_data)
                _logger.info("Product Attribute Sync Task Created!")
            else:
                _logger.error("Product Attribute Sync Log Creation Failed!!")