# -*- coding: utf-8 -*-
from odoo import models, fields, api
from . import common_functions
import ast
import logging

_logger = logging.getLogger(__name__)


class ZidStoreLocationsScheduler(models.Model):
    _name = 'zid.store.locations.scheduler'
    _description = 'Zid Store Locations Scheduler'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    status = fields.Selection([('draft', 'Draft'), ('progress', 'In Progess'), ('done', 'Done'), ('failed', 'Failed')],
                              string="Status", tracking=True, default='draft', readonly=True)
    data = fields.Text(string="Json Data", readonly=True)
    store_location_id = fields.Many2one('zid.store.locations', string='Store Location', readonly=True)
    scheduler_log_id = fields.Many2one('zid.scheduler.log.line', string="Scheduler Log", readonly=True)
    zid_instance_id = fields.Many2one('zid.instance.ept', string="Zid Instance", tracking=True, readonly=True)

    @api.model
    def create_zid_store_location_record(self):
        """
        Function to create record in zid store location
        :return:
        """
        _logger.info("Processing Store Locations Queue!!")

        draft_store_locations = self.search([('status', '=', 'draft')])
        store_locations_objs = self.env['zid.store.locations']

        for store_location in draft_store_locations:
            try:
                store_location.status = 'progress'
                input_string = store_location['data']
                store_location_detail = ast.literal_eval(input_string)
                store_location_id = store_locations_objs.search([('zid_location_id', '=', store_location_detail['id']), (
                'zid_instance_id', '=', store_location.zid_instance_id.id)])

                if not store_location_id:
                    country_id = None
                    if store_location_detail['city'].get('country'):
                        country_id = store_location_detail['city']['country']['id']
                    elif store_location_detail['city'].get('country_id'):
                        country_id = store_location_detail['city'].get('country_id')

                    country_master_id = self.env['zid.country.master'].search(
                        [('zid_country_id', '=', country_id)], limit=1).id
                    state_master_id = self.env['zid.state.master'].search(
                        [('zid_state_id', '=', store_location_detail['city']['id'])], limit=1).id
                    data_for_store_locations = {
                        'zid_instance_id': store_location.zid_instance_id.id,
                        'zid_location_id': store_location_detail.get('id'),
                        'country_master_id': country_master_id,
                        'state_master_id': state_master_id,
                        'latitude': store_location_detail['coordinates'].get('latitude') or store_location_detail[
                            'coordinates'].get('lat'),
                        'longitude': store_location_detail['coordinates'].get('longitude') or store_location_detail[
                            'coordinates'].get('lon'),
                        'full_address': store_location_detail.get('full_address'),
                        'fulfillment_priority': store_location_detail.get('fulfillment_priority'),
                        'is_default': store_location_detail.get('is_default'),
                        'is_private': store_location_detail.get('is_private'),
                        'is_enabled': store_location_detail.get('is_enabled'),
                        'has_stock': store_location_detail.get('has_stocks'),
                        'name': store_location_detail['name']['en'],
                    }
                    store_location_id = store_locations_objs.create(data_for_store_locations)

                if store_location_id:
                    store_location.store_location_id = store_location_id.id
                    store_location.status = 'done'
                    store_location.scheduler_log_id.completed_lines += 1
                    common_functions.update_scheduler_log_state(store_location.scheduler_log_id)
                    _logger.info(f"Zid Store Location with zid id {store_location_detail.get('id')} created")
            except Exception as e:
                store_location.status = 'failed'
                _logger(str(e))
                _logger.error(f"Zid Store Location with zid id {store_location_detail.get('id')} failed")

