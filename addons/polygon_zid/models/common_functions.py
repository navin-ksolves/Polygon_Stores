# -*- coding: utf-8 -*-
from . import common_functions
import requests


def fetch_authentication_details(self, instance_id):
    """
    Function to fetch headers for api calls
    :param instance: id of the zid instance
    :return: headers
    """
    instance = self.env['zid.instance.ept'].search([('id', '=', instance_id)], limit=1)
    if instance:
        access_token = instance.access_token
        authorization = self.env['zid.tokens'].search([('access_token', '=', access_token)]).authorization
        headers = {
            "Authorization": f"Bearer {authorization}",
            "X-Manager-Token": access_token,
            "Accept-Language": "en",
            "Accept": "application/json"
        }
        return headers
    return False

def log_for_store_locations(self, zid_instance):
    """
    Helper function to create log for store locations
    :param self: self
    :param zid_instance: zid instance object
    :return: json data
    """
    if zid_instance.has_multi_inventory:
        url = "https://api.zid.sa/v1/locations/"
        headers = fetch_authentication_details(self, zid_instance.id)
        store_id = self.env['zid.tokens'].search(
            [('access_token', '=', zid_instance.access_token)]).zid_request_id.store_id
        headers['Access-Token'] = headers.pop('X-Manager-Token')
        headers['Store-Id'] = store_id
        headers['Role'] = 'Manager'
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return {'data': response.json()['results']}
    elif not zid_instance.has_multi_inventory:
        url = "https://api.zid.sa/v1/managers/store/inventory-addresses"
        headers = common_functions.fetch_authentication_details(self, zid_instance.id)
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return {'data': response.json()['inventory_addresses']}
        return {}

def log_for_currency(self, zid_instance):
    """
    Helper function to create log for currency
    :param self: self
    :param zid_instance: zid instance object
    :return: json data
    """
    url = "https://api.zid.sa/v1/managers/account/profile"
    headers = common_functions.fetch_authentication_details(self, zid_instance.id)
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        if response.status_code == 200:
            return {'data': response.json().get('user', {}).get('store', {}).get('currencies', [])}
        return {}
def log_for_product_attributes(self, zid_instance):
    """
    Helper function to create log for product attributes
    :param self: self
    :param zid_instance: instance object
    :return: json data
    """
    url = "https://api.zid.sa/v1/attributes/"
    headers = fetch_authentication_details(self, zid_instance.id)
    store_id = self.env['zid.tokens'].search(
        [('access_token', '=', zid_instance.access_token)]).zid_request_id.store_id

    headers['Access-Token'] = headers.pop('X-Manager-Token')
    headers['Store-Id'] = store_id
    headers = {
        "Access-Token": headers['Access-Token'],
        "Store-Id": headers['Store-Id'],
        "Accept": "application/json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return {'data': response.json()['results']}
    return {}

def log_for_product(self, zid_instance):
    """
    Helper function to create log for products
    :param self: self
    :param zid_instance: zid instance object
    :return: json data
    """
    url = "https://api.zid.sa/v1/products/"
    headers = common_functions.fetch_authentication_details(self, zid_instance.id)
    store_id = self.env['zid.tokens'].search(
        [('access_token', '=', zid_instance.access_token)]).zid_request_id.store_id
    headers['Access-Token'] = headers.pop('X-Manager-Token')
    headers['Store-Id'] = store_id
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return {'data': response.json()['results']}
    return {}
def log_for_order(self, zid_instance):
    """
    Helper function to create order log
    :param self: self
    :param zid_instance: zid instance object
    :return: json data
    """
    url = "https://api.zid.sa/v1/managers/store/orders"
    querystring = {"page": "1", "per_page": "10"}
    headers = common_functions.fetch_authentication_details(self, zid_instance.id)
    response = requests.get(url, headers=headers, params=querystring)
    data_json = {}
    if response.status_code == 200:
        data_json = {'data': response.json()['orders']}
        total_order_count = response.json().get('total_order_count', 0)
        if total_order_count > 10:
            order_left_to_sync = response.json()['total_order_count'] - 10
            page = 2
            while order_left_to_sync != 0:
                url = "https://api.zid.sa/v1/managers/store/orders"
                querystring = {"page": page, "per_page": "10"}
                headers = fetch_authentication_details(self, zid_instance.id)
                new_response = requests.get(url, headers=headers, params=querystring)
                if new_response.status_code == 200:
                    data_for_log = {
                        'scheduler_type': 'order',
                        'instance_id': zid_instance.id,
                        'status': 'draft',
                        'attempts': 0,
                        'json': data_json
                    }
                    self.env['zid.scheduler.log.line'].sudo().create(data_for_log)
                    page += 1
                    order_left_to_sync -= 10
        return data_json
def log_for_category(self, zid_instance):
    """
    Helper function to create log for category
    :param self: self
    :param zid_instance: zid instance object
    :return: json data
    """
    url = "https://api.zid.sa/v1/managers/store/categories"
    headers = fetch_authentication_details(self, zid_instance.id)
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return {'data': response.json()['categories']}
    return {}

def create_log_in_scheduler(self, zid_instance, create_log_for, json_data=False):
    """
    Function to create log in zid_scheduler
    :param create_log_for: list of scheduler types
    :param zid_instance: zid instance object
    :return:
    """
    for log in create_log_for:
        data_json = {}
        if log == 'store_locations':
            data_json = log_for_store_locations(self, zid_instance)

        elif log == 'currency':
            data_json = log_for_currency(self, zid_instance)

        elif log == 'product_attributes':
            data_json = log_for_product_attributes(self, zid_instance)

        elif log == 'product':
            data_json = log_for_product(self, zid_instance)

        elif log == 'order':
            data_json = log_for_order(self, zid_instance)

        elif log == 'category':
            if not json_data:
                data_json = log_for_category(self, zid_instance)
            else:
                data_json = json_data

        elif log == 'sync_states':
            data_json = json_data

        data_for_log = {
            'scheduler_type': log,
            'instance_id': zid_instance.id,
            'status': 'draft',
            'attempts': 0,
            'json': data_json
        }
        self.env['zid.scheduler.log.line'].sudo().create(data_for_log)
    return True

def update_scheduler_log_state(scheduler_log_record):
    """
    Function to update the status of scheduler log record to Done if total lines == completed lines
    :param scheduler_log_record: record of scheduler log that has to be updated
    :return:
    """
    if scheduler_log_record.total_lines == scheduler_log_record.completed_lines:
        scheduler_log_record.status = 'done'
