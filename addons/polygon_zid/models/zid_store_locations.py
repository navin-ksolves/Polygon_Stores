# -*- coding: utf-8 -*-
from odoo import models, fields, api
from . import common_functions
import requests

class ZidStoreLocations(models.Model):
    _name = 'zid.store.locations'
    _description = 'Zid Store Locations'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    zid_instance_id = fields.Many2one('zid.instance.ept', string="Zid Instance", required=True, tracking=True)
    zid_location_id = fields.Char('Zid Location Id')
    name = fields.Char("Name")
    country_master_id = fields.Many2one('zid.country.master', string="Country")
    state_master_id = fields.Many2one('zid.state.master', string="State")
    latitude = fields.Char("Latitude")
    longitude = fields.Char("Longitude")
    full_address = fields.Text("Address")
    fulfillment_priority = fields.Integer(" Fulfillment Priority")
    is_default = fields.Boolean("Default", default = False)
    is_private = fields.Boolean("Private", default = False)
    is_enabled = fields.Boolean("Enabled", default = False)
    has_stock = fields.Boolean("Has Stock", default = False)
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")

    #TODO: Might have to remove it later
    # def create_store_location_sync_logs(self):
    #     instances = self.env['zid.instance.ept'].search([])
    #     for instance in instances:
    #         url = "https://api.zid.sa/v1/locations/"
    #         headers = common_functions.fetch_authentication_details(self,instance.id)
    #         store_id = self.env['zid.tokens'].search([('access_token', '=', instance.access_token)]).zid_request_id.store_id
    #         headers['Access-Token'] = headers.pop('X-Manager-Token')
    #         headers['Store-Id'] = store_id
    #
    #         response = requests.get(url, headers=headers)
    #         if response.status_code == 200:
    #             json_data = {'data':response.json()['results']}
    #             common_functions.create_log_in_scheduler(self,instance,['store_locations'], json_data=json_data )
    #
    #
    #
