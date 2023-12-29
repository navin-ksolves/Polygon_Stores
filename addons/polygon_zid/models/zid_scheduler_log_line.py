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
                                       ('currency', 'Currency'),('update_product_quant','Update Product Quant'),
                                       ('category', 'Category'), ('product_attributes', 'Product Attributes'),
                                       ('sync_states', 'States'), ('store_locations', 'Store Locations'),
                                       ('sync_do_countries_states', 'Sync Countries'), ('webhook', 'Webhook')],
                                      string="Scheduler Type", tracking=True)
    instance_id = fields.Many2one('zid.instance.ept', string="Instance", tracking=True, required=False, index=True)
    json = fields.Text(string="Json", readonly=True)
    attempts = fields.Integer(string="Attempts", tracking=True, required=True, index=True)
    status = fields.Selection([('draft', 'Draft'), ('progress', 'In Progess'), ('done', 'Done'), ('failed', 'Failed')],
                              string="Status", tracking=True, default='draft', readonly=True)
    total_lines = fields.Integer('Total Lines')
    completed_lines = fields.Integer('Completed Lines')
    scheduler_log_id = fields.Many2one('zid.scheduler.log', 'Scheduler Log')
    webhook_type = fields.Char('Webhook Type')

    @api.onchange('status')
    def onchange_status(self):
        """
        On change function to change status of scheduler log when log line's status
        becomes failed or progress
        :return:
        """
        if self.status in ['progress', 'failed']:
            self.scheduler_log_id.status = self.status

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

    # def run_queue(self):
    #     """
    #     Function to process tasks present in the log
    #     """
    #     tasks = self.env['zid.scheduler.log.line'].search([('status', '=', 'draft')])
    #
    #     for task in tasks:
    #         is_task_failed = self.is_task_failed(task)
    #         if is_task_failed:
    #             continue
    #
    #         task.status = 'progress'
    #         task.attempts += 1
    #
    #         if task.scheduler_type == "sync_states":
    #             self.sync_states(task)
    #
    #         # For processing currency
    #         elif task.scheduler_type == "currency":
    #             self.create_zid_currency(task)
    #
    #         elif task.scheduler_type == "product_attributes":
    #             self.create_product_attributes(task)
    #
    #         # For syncing delivery option country and states
    #         elif task.scheduler_type == 'sync_do_countries_states':
    #             is_successful = self.create_zid_country_master(task)
    #             task.status = 'done' if is_successful else 'draft'
    #
    #         # For syncing store locations
    #         elif task.scheduler_type == 'store_locations':
    #             self.create_store_location_scheduler(task)
    #
    #         elif task.scheduler_type == "product":
    #             self.sync_products(task)
    #
    #         elif task.scheduler_type == "category":
    #             self.sync_product_category(task)
    #
    #         elif task.scheduler_type == "order":
    #             self.sync_orders(task)
    #
    #         elif task.scheduler_type == "webhook":
    #             self.manage_webhooks(task)

    def manage_webhooks(self, task):
        """
        Helper function that manages
        :param task: scheduler_log_line object
        """
        if task.webhook_type in ['product.create', 'product.update', 'product.publish']:
            task.scheduler_type = 'product'
            task.status = 'draft'
            task.attempts = 0
        elif task.webhook_type in ['product.delete']:
            self.archive_zid_product(task)
        elif task.webhook_type == 'order.create':
            task.scheduler_type = 'order'
            task.status = 'draft'
            task.attempts = 0
        elif task.webhook_type in ['order.ready','order.canceled','order.status.update']:
            self.change_order_status(task)

    def archive_zid_product(self, task):
        """
        Function to archive zid product
        :param task: task
        :return:
        """
        input_string = task['json']
        # instance = task.instance_id
        # Convert string to dictionary
        result_dict = ast.literal_eval(input_string)
        product_details = result_dict['data']
        product_id = product_details['product_id']
        # find in zid_variant
        zid_products = self.env['zid.product.variants'].search(('zid_id','=',product_id))
        for zid_product in zid_products:
            if not zid_product:
                zid_product = self.env['zid.product.template'].search(('zid_id', '=', product_id))
                if zid_product:
                    # archive odoo variant and zid product
                    zid_product.active = False
                    zid_product.primary_product_id.active = False
            else:
                # archive zid product
                zid_product.active = False
                # archive the odoo variant
                zid_product.product_variant_id.active = False

    def change_order_status(self,task):
        """
        Helper function to update status of order
        :param task:
        :return:
        """
        input_string = task['json']
        instance = task.instance_id
        # Convert string to dictionary
        result_dict = ast.literal_eval(input_string)
        for order in result_dict['data']:
            zid_order = self.env['zid.order.ept'].search([('online_order_id','=',order['id']),('instance_id','=',instance.id)])
            #find zid order
            if zid_order:
                zid_order.order_status = order['order_status']['code']
        task.status = 'done'

    def update_product_qty(self, task):
        """
        Function to update quantity of products
        """
        input_string = task['json']
        instance = task.instance_id
        # Convert string to dictionary
        result_dict = ast.literal_eval(input_string)
        for product_id in result_dict['data']:
            try:
                zid_product = self.env['zid.product.variants'].search([('zid_instance_id', '=', instance.id),
                                                                       ('product_variant_id', '=', product_id)])
                if zid_product:
                    odoo_product = zid_product.product_variant_id
                    stock_id = zid_product.zid_stock_id
                else:
                    zid_product = self.env['zid.product.template'].search([('instance_id', '=', instance.id),
                                                                           ('primary_product_id', '=', product_id)])
                    if zid_product:
                        odoo_product = zid_product.primary_product_id
                        stock_id = zid_product.zid_stock_id
                    if not zid_product:
                        continue

                product_id = zid_product.zid_id
                headers = common_functions.fetch_authentication_details(self, instance.id)

                store_id = self.env['zid.tokens'].search(
                    [('access_token', '=', instance.access_token)]).zid_request_id.store_id
                headers['Access-Token'] = headers.pop('X-Manager-Token')
                headers['Store-Id'] = store_id
                headers['Role'] = 'Manager'
                # get stock_id for the product if not present in the product
                if not stock_id:
                    url = f"https://api.zid.sa/v1/products/{product_id}/stocks/"

                    response = requests.get(url, headers=headers)
                    if response.status_code ==  200:
                        stocks_info = response.json()['results']
                        for stock_info in stocks_info:
                            store_location_id = self.env['zid.store.locations'].search([('zid_instance_id','=', instance.id),('warehouse_id','!=',False)], limit=1)
                            if store_location_id:
                                zid_location_id = store_location_id.zid_location_id
                                if stock_info.get('location')['id'] == zid_location_id:
                                    stock_id = stock_info['id']
                                    zid_product.zid_stock_id = stock_id
                # Update stock quantity in zid
                url = f"https://api.zid.sa/v1/products/{product_id}/stocks/{stock_id}/"

                available_qty = odoo_product.virtual_available
                payload = {
                    "available_quantity": available_qty,
                    "is_infinite": False
                }
                response = requests.patch(url, json=payload, headers=headers)

                print(response.json())
            except Exception as e:
                print(str(e))
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
