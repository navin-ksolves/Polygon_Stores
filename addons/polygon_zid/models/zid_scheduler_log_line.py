# -*- coding: utf-8 -*-
from odoo import models, fields, api
import requests
import json
from . import common_functions
import ast
from datetime import date
import logging

_logger = logging.getLogger(__name__)


class ZidSchedulerLogLine(models.Model):
    _name = 'zid.scheduler.log.line'
    _description = 'Zid Scheduler Log Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _rec_name = "instance_id"

    scheduler_type = fields.Selection([('order', 'Order'), ('product', 'Product'), ('customer', 'Customer'),
                                       ('currency', 'Currency'), ('vat', 'Vat'),
                                       ('category', 'Category'), ('product_attributes', 'Product Attributes'),
                                       ('sync_states', 'States'), ('store_locations', 'Store Locations'),
                                       ('sync_do_countries_states', 'Sync Countries')],
                                      string="Scheduler Type", tracking=True)
    instance_id = fields.Many2one('zid.instance.ept', string="Instance", tracking=True, required=True, index=True)
    json = fields.Text(string="Json", readonly=True)
    attempts = fields.Integer(string="Attempts", tracking=True, required=True, index=True)
    status = fields.Selection([('draft', 'Draft'), ('progress', 'In Progess'), ('done', 'Done'), ('failed', 'Failed')],
                              string="Status", tracking=True, default='draft', readonly=True)
    total_lines = fields.Integer('Total Lines')
    completed_lines = fields.Integer('Completed Lines')
    scheduler_log_id = fields.Many2one('zid.scheduler.log', 'Scheduler Log')

    @api.model
    def create(self, vals_list):
        """
        Overrided the function to link the log line with current scheduler log
        and if there is no log for today, it will create one and link log line with it
        """
        scheduler_log_line = super(ZidSchedulerLogLine, self).create(vals_list)
        zid_scheduler_log_obj = self.env['zid.scheduler.log']
        if not scheduler_log_line.scheduler_log_id:
            scheduler_log_id = zid_scheduler_log_obj.search([('date', '=', date.today())])
            if scheduler_log_id:
                scheduler_log_line.scheduler_log_id = scheduler_log_id.id
            else:
                scheduler_log_id = zid_scheduler_log_obj.create({'date': date.today()})
                scheduler_log_line.scheduler_log_id = scheduler_log_id.id
        return scheduler_log_line

    def run_queue(self):
        """
        Function to process tasks present in the log
        """
        tasks = self.env['zid.scheduler.log.line'].search([('status', '=', 'draft')])

        for task in tasks:
            is_task_failed = self.is_task_failed(task)
            if is_task_failed:
                continue

            task.status = 'progress'
            task.attempts += 1

            if task.scheduler_type == "sync_states":
                self.sync_states(task)

            # For processing currency
            elif task.scheduler_type == "currency":
                self.create_zid_currency(task)

            elif task.scheduler_type == "product_attributes":
                self.create_product_attributes(task)

            # For syncing delivery option country and states
            elif task.scheduler_type == 'sync_do_countries_states':
                is_successful = self.create_zid_country_master(task)
                task.status = 'done' if is_successful else 'draft'

            # For syncing store locations
            elif task.scheduler_type == 'store_locations':
                self.create_store_location_scheduler(task)

            elif task.scheduler_type == "product":
                self.sync_products(task)

            elif task.scheduler_type == "category":
                self.sync_product_category(task)

            elif task.scheduler_type == "order":
                self.sync_orders(task)

    def sync_orders(self, task):
        """
        Function to sync orders
        :param task:queue task
        """
        _logger.info("Syncing Orders!!")
        try:
            input_string = task['json']
            # Convert string to dictionary
            result_dict = ast.literal_eval(input_string)
            for order in result_dict['data']:
                count = 0
                values = {
                    'status': 'draft',
                    'data': order,
                    'scheduler_log_id': task.id,
                }
                order_scheduler = self.env['zid.scheduler.order'].create(values)
                if order_scheduler:
                    count += 1
                task.total_lines += count
                _logger.info('Order Scheduler Record Created!!')
            return True
        except Exception as e:
            _logger.error(str(e))
            _logger.error('Order Scheduler Record Creation Failed!!')
            return False

    def sync_product_category(self, task):
        """
        Function to sync product category
        """
        _logger.info("Syncing Product Categories!!")
        try:
            input_string = task['json']
            # Convert string to dictionary
            result_dict = ast.literal_eval(input_string)
            for category in result_dict['data']:
                count = 0
                values = {
                    'status': 'draft',
                    'data': category,
                    'scheduler_log_id': task.id,
                }
                product_scheduler = self.env['zid.product.category.scheduler'].create(values)
                if product_scheduler:
                    count += 1
                task.total_lines += count
                _logger.info('Product Category Record Created!!')
            return True
        except Exception as e:
            _logger.error(str(e))
            _logger.error('Product Category Record Creation Failed!!')
            return False


    def sync_products(self, task):
        """
        Function to sync products of the instance
        :param task: current task in the queue
        """
        _logger.info("Syncing Products!!")
        try:
            input_string = task['json']
            # Convert string to dictionary
            result_dict = ast.literal_eval(input_string)
            for product in result_dict['data']:
                count = 0
                values = {
                    'status': 'draft',
                    'data': product,
                    # 'category': True if len(product.get('categories')) else False,
                    # 'attribute': True if len(product.get('attributes')) else False,
                    # 'images': True if len(product.get('images')) else False,
                    'scheduler_log_id': task.id,
                }
                product_scheduler = self.env['zid.scheduler.products'].create(values)
                if product_scheduler:
                    count += 1
                task.total_lines += count
                _logger.info('Product Scheduler Record Created!!')
            return True
        except Exception as e:
            _logger.error(str(e))
            _logger.error('Product Scheduler Record Creation Failed!!')
            return False

    def create_product_attributes(self, task):
        """
        Function to create record in zid.attribute.scheduler and zid.attribute.value.scheduler
        :param task: task
        :return:
        """
        try:
            input_string = task['json']
            # Convert string to dictionary
            result_dict = ast.literal_eval(input_string)
            for attribute in result_dict['data']:
                count = 0
                values = {
                    'status': 'draft',
                    'data': attribute,
                    'scheduler_log_id': task.id,
                }
                product_attribute_scheduler = self.env['zid.product.attributes.scheduler'].create(values)
                if product_attribute_scheduler:
                    count += 1
                task.total_lines += count
            _logger.info('Product Attribute Scheduler Record Created!!')
            return True
        except Exception as e:
            _logger.error(str(e))
            _logger.error('Product Attribute Scheduler Record Creation Failed!!')
            return False

    def create_store_location_scheduler(self, task):
        """
        Function to create data in store location scheduelr
        :param task: task
        :return:
        """
        try:
            input_string = task['json']
            # Convert string to dictionary
            result_dict = ast.literal_eval(input_string)
            for store_location in result_dict['data']:
                count = 0
                values = {
                    'status': 'draft',
                    'data': store_location,
                    'scheduler_log_id': task.id,
                    'zid_instance_id': task.instance_id.id
                }
                store_location_scheduler = self.env['zid.store.locations.scheduler'].create(values)
                if store_location_scheduler:
                    count += 1
                task.total_lines += count
            return True
        except Exception as e:
            _logger.info(str(e))
            return False

    def is_task_failed(self, task):
        """
        Function to check if task has failed and if failed, change its status to failed
        :return: True if task has failed, False otherwise
        """
        if task.attempts == 3:
            task.status = 'failed'
            return True
        return False

    def create_zid_currency(self, task):
        """
        Function to create data in zid currency scheduler
        :param task: task in queue
        :return: True if creation successfull, else False
        """
        try:
            input_string = task['json']
            # Convert string to dictionary
            result_dict = ast.literal_eval(input_string)
            currencies = result_dict['data']
            for currency in currencies:
                count = 0
                data_for_zid_currency_scheduler = {
                    'status': 'draft',
                    'data': currency,
                    'scheduler_log_id': task.id
                }
                currency_scheduler = self.env['zid.scheduler.currency'].create(data_for_zid_currency_scheduler)
                if currency_scheduler:
                    count += 1
                task.total_lines += count
            return True
        except Exception as e:
            _logger.info(str(e))
            return False

    def sync_states(self, task):
        """
        Function to create data in zid_scheduler_state according to json data present in the task
        :return:
        """
        try:
            input_string = task['json']
            # Convert string to dictionary
            result_dict = ast.literal_eval(input_string)
            cities = result_dict['data']['cities']
            for city in cities:
                count = 0
                data_for_zid_state_scheduler = {
                    'status': 'draft',
                    'data': city,
                    'scheduler_log_id': task.id
                }
                scheduler_state = self.env['zid.scheduler.state'].create(data_for_zid_state_scheduler)
                if scheduler_state:
                    count += 1
                task.total_lines += count
            return True
        except Exception as e:
            _logger.info(str(e))
            return False

    def sync_states_1(self, task):
        """
        Calls the state api for instance and creates new line in scheduler with the received json for each country
        :param task:
        :return:
        """
        try:
            countries = self.env['zid.country.master'].search([])
            for country in countries:
                country_id = country.zid_country_id
                url = f"https://api.zid.sa/v1/managers/cities/by-country-id/{country_id}"
                headers = common_functions.fetch_authentication_details(self, task.instance_id.id)
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    json_data = {'data': country.zid_country_id}
                    common_functions.create_log_in_scheduler(self, task.instance_id, create_log_for=['sync_states'],
                                                             json_data=json_data)
            return True
        except Exception as e:
            _logger.info(str(e))
            return False

    def create_delivery_options(self, task):
        """
        Function to create delivery options
        :return: True if successful, False otherwise
        """
        try:
            # url = "https://api.zid.sa/v1/managers/store/delivery-options"
            url = "https://stoplight.io/mocks/zid/zid-merchant-api/38696028/managers/store/delivery-options"
            # FIXME: Not use mock server currently using only to fetch dummy data
            querystring = {"payload_type": "simple"}
            headers = common_functions.fetch_authentication_details(self, task.instance_id.id)
            response = requests.get(url, headers=headers)
            response = requests.get(url, headers=headers, params=querystring)
            data = response.json()
            # Handle the response as needed
            if response.status_code == 200:
                for delivery_option in data.get('delivery_options', []):
                    delivery_option_data = {
                        'zid_instance_id': task['instance_id'].id,
                        'zid_delivery_option_id': delivery_option['id'],
                        'name': delivery_option['name'],
                    }
                    # creation of delivery option in Odoo
                    new_delivery_option = self.env['zid.delivery.options'].create(delivery_option_data)
                    # creation of delivery option cities for the current delivery option
                    self.create_delivery_option_cities(delivery_option['select_cities'], task,
                                                       new_delivery_option['id'])
                    if not new_delivery_option:
                        return False
                    _logger.info("Delivery Option created!")
                    return True
            else:
                # Error handling
                print(f"Error: {response.status_code}")
                print(response.text)
                return False
        except Exception as e:
            _logger.info(str(e))
            return False

    def create_delivery_option_cities(self, delivery_option_cities, task, delivery_option_id):
        """
        Funtion to create delivery option cities
        :param delivery_option_id: odoo id of the created delivery option
        :param task: task data from log queue
        :param delivery_option_cities: delivery option cities received from json
        :return:
        """
        for city in delivery_option_cities:
            data_for_delivery_option_cities = {
                'zid_instance_id': task['instance_id'].id,
                'zid_delivery_option_id': delivery_option_id,
                'zid_country_id': city['country_id'],
                'zid_country_name': city['country_code'],
                'zid_state_name': city['en_name'],
                'zid_state_id': city['id']
            }
            zid_country_master = self.env['zid.country.master'].search([('zid_country_id', '=', city['country_id'])])
            if zid_country_master: data_for_delivery_option_cities['zid_country_master'] = zid_country_master.id
            zid_state_master = self.env['zid.state.master'].search([('zid_state_id', '=', city['id'])])
            if zid_state_master: data_for_delivery_option_cities['zid_state_master'] = zid_state_master.id
            self.env['zid.delivery.options.cities'].create(data_for_delivery_option_cities)

    def create_zid_country_master(self, task):
        """
        Funtion to create data in zid country master and state master
        :param task: data of the process
        :param city: json data of city
        :return: if synced successfully then True, else False
        """
        try:
            task_json = task['json']
            delivery_option_id = json.loads(task_json.replace("'", "\""))['delivery_option_id']
            delivery_option_cities = self.env['zid.delivery.options.cities'].search(
                [('zid_delivery_option_id', '=', delivery_option_id)])
            for delivery_option_city in delivery_option_cities:
                zid_country_master = self.env['zid.country.master'].search(
                    [('zid_country_id', '=', delivery_option_city['zid_country_id'])])
                zid_country_master = zid_country_master or self.create_zid_country_master(delivery_option_city)

                zid_state_master = self.env['zid.state.master'].search(
                    [('zid_state_id', '=', delivery_option_city['zid_state_id'])])
                zid_state_master = zid_state_master or self.create_zid_state_master(delivery_option_city,
                                                                                    zid_country_master)
                # link delivery option city with master data
                delivery_option_city.write(
                    {'zid_country_master': zid_country_master.id, 'zid_state_master': zid_state_master.id})
            _logger.info("Country & City Synced Successfully!")
            return True
        except Exception as e:
            _logger.info(str(e))
            return False

    def create_country_master(self, delivery_option_city):
        """
            Helper function to create zid_country_master
            :param delivery_option_city: data of the city
            :return: created zid_country_master record
            """
        data_for_country_master = {
            'zid_country_id': delivery_option_city['zid_country_id'],
            'name': delivery_option_city['zid_country_name']
        }
        return self.env['zid.country.master'].create(data_for_country_master)

    def create_zid_state_master(self, city, new_zid_country_master):
        """
         Helper function to create zid_state_master
        :param delivery_option_city: data of the city
        :param zid_country_master: related zid_country_master record
        :return: created zid_state_master record
        """
        data_for_state_master = {
            'zid_state_id': city['zid_state_id'],
            'name': city['zid_state_name'],
            'zid_country_id': new_zid_country_master['id']
        }
        zid_state_master_record = self.env['zid.state.master'].create(data_for_state_master)
        return zid_state_master_record
