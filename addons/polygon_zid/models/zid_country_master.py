# -*- coding: utf-8 -*-
from odoo import models, fields
import requests
import logging
from . import common_functions

_logger = logging.getLogger(__name__)


class ZidCountryMaster(models.Model):
    _name = 'zid.country.master'
    _description = 'Zid Country Master'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    zid_country_id = fields.Integer('Zid Country Id')
    name = fields.Char('Name')
    odoo_country = fields.Many2one('res.country', string='Odoo Country')
    is_state_synced = fields.Boolean(string='Is State Synced?', default=False)

    def create_state_sync_log(self):
        """
        Function to create log in scheduler to sync states for each instance,
        it fetches data for country for each instance using api
        :return:
        """
        countries = self.env['zid.country.master'].search([('is_state_synced','=',False)])
        for country in countries:
            instances = self.env['zid.instance.ept'].search([])
            for instance in instances:
                country_id = country.zid_country_id
                url = f"https://api.zid.sa/v1/managers/cities/by-country-id/{country_id}"
                headers = common_functions.fetch_authentication_details(self, instance.id)
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    json_data = {'data': response.json()}
                    common_functions.create_log_in_scheduler(self, instance, create_log_for=['sync_states'], json_data=json_data)
            country.is_state_synced = True

    def create_zid_state_master(self, city, zid_country_master):
        """
         Helper function to create zid_state_master
        :param delivery_option_city: data of the city
        :param zid_country_master: related zid_country_master record
        :return: created zid_state_master record
        """
        data_for_state_master = {
            'zid_state_id': city['id'],
            'name': city['en_name'],
            'zid_country_id': zid_country_master['id']
        }
        zid_state_master_record = self.env['zid.state.master'].create(data_for_state_master)
        return zid_state_master_record

