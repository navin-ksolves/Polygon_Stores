# -*- coding: utf-8 -*-
from . import common_functions
import requests
import datetime


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
            if response.json().get('results'):
                return {'data': response.json()['results']}
            elif response.json().get('inventory_addresses'):
                return {'data': response.json()['inventory_addresses']}
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
    if len(self.read()):
        wizard_rec = self.read()[0]
        if wizard_rec.get('date_from'):
            headers['date_from'] = wizard_rec.get('date_from').strftime("%Y-%m-%d")
        if wizard_rec.get('date_to'):
            headers['date_to'] = wizard_rec.get('date_to').strftime("%Y-%m-%d")
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

        elif log == 'update_product_quant':
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

def change_scheduler_log_status(scheduler_log_record, status):
    """
    Function to change status of scheduler log record to the provided status
    :param scheduler_log_record: record of scheduler log
    :param status: to the status
    """
    scheduler_log_record.status = status

def update_log_line_attempts(self, model, record_id, record_id_field_name):
    """
    Function to update attempts of parent records based on attempts of child record
    :param self: self
    :param model: child model name to search in
    :param record_id: parent model record in child model
    :param record_id_field_name: name of parent model record in child model
    :return:
    """
    total_records_done = self.env[model].search([(record_id_field_name,'=', record_id.id)])
    total_records_failed = self.env[model].search([(record_id_field_name,'=', record_id.id),('status','=','failed')])
    if total_records_failed:
        all_attempts = map(lambda x: x.attempts, total_records_failed)
        parent_attempt = min(list(all_attempts))
        record_id.attempts = parent_attempt
        if parent_attempt == 3:
            record_id.status = 'failed'
    else:
        all_attempts = map(lambda x: x.attempts, total_records_done)
        parent_attempt = min(list(all_attempts))
        record_id.attempts = parent_attempt

def update_zid_order_status_based_on_picking(self, related_so,picking, tracking_url=False, picking_cancelled = False):
    """
    Function to update status of zid order based on status of picking
    :param self: self
    :param picking: record of stock_picking
    :return:
    """
    # related_so = self.env['sale.order'].sudo().search([('name','=', picking.origin)])
    if related_so:
       zid_order = self.env['zid.order.ept'].sudo().search([('so_id','=', related_so.id),('instance_id','=',related_so.zid_instance_id.id)], limit=1)
       if zid_order:
        order_id = zid_order.online_order_id
        url = f"https://api.zid.sa/v1/managers/store/orders/{order_id}/change-order-status"

        if picking_cancelled:
            zid_status = 'cancelled'
        else:
            zid_status = get_zid_status(self, related_so.delivery_status,picking.state,tracking_url)
        # payload = "-----011000010111000001101001\r\nContent-Disposition: form-data; name=\"order_status\"\r\n\r\nnew\r\n-----011000010111000001101001\r\nContent-Disposition: form-data; name=\"inventory_address_id\"\r\n\r\n\r\n-----011000010111000001101001\r\nContent-Disposition: form-data; name=\"tracking_number\"\r\n\r\n456777\r\n-----011000010111000001101001\r\nContent-Disposition: form-data; name=\"tracking_url\"\r\n\r\nwww\r\n-----011000010111000001101001\r\nContent-Disposition: form-data; name=\"waybill_url\"\r\n\r\n\r\n-----011000010111000001101001--\r\n"


        if zid_status:
            payload = f"-----011000010111000001101001\r\nContent-Disposition: form-data; name=\"order_status\"\r\n\r\n{zid_status}\r\n-----011000010111000001101001\r\nContent-Disposition: form-data; name=\"inventory_address_id\"\r\n\r\n\r\n-----011000010111000001101001\r\nContent-Disposition: form-data; name=\"tracking_number\"\r\n\r\n{related_so.name}\r\n-----011000010111000001101001\r\nContent-Disposition: form-data; name=\"tracking_url\"\r\n\r\n{tracking_url}\r\n-----011000010111000001101001\r\nContent-Disposition: form-data; name=\"waybill_url\"\r\n\r\n\r\n-----011000010111000001101001--\r\n"
        else:
            payload = f"-----011000010111000001101001\r\nContent-Disposition: form-data; name=\"order_status\"\r\n\r\n\r\n-----011000010111000001101001\r\nContent-Disposition: form-data; name=\"inventory_address_id\"\r\n\r\n\r\n-----011000010111000001101001\r\nContent-Disposition: form-data; name=\"tracking_number\"\r\n\r\n{related_so.name}\r\n-----011000010111000001101001\r\nContent-Disposition: form-data; name=\"tracking_url\"\r\n\r\n{tracking_url}\r\n-----011000010111000001101001\r\nContent-Disposition: form-data; name=\"waybill_url\"\r\n\r\n\r\n-----011000010111000001101001--\r\n"
        headers = common_functions.fetch_authentication_details(self, related_so.zid_instance_id.id)
        headers['Content-Type'] = "multipart/form-data; boundary=---011000010111000001101001"
        response = requests.post(url, data=payload, headers=headers)

        print('HELLLOOO++++++',response.json())

def get_zid_status(self, order_status, picking_status,tracking_url=False):
    """
    Returns status to send to zid
    :param self: self
    :param order_status: status of related sale order
    :param picking_status: status of picking
    :return:
    """
    # Available order statuses are as follows: (new, preparing, ready, indelivery, delivered, cancelled)
    if tracking_url:
        if picking_status == 'ready_to_dispatch':
            event_status = 'ready'
        elif picking_status == 'in_transit':
            event_status = 'indelivery'
        elif picking_status == 'assigned':
            event_status = 'ready'
        elif picking_status == 'done' and order_status == 'full':
            event_status = 'delivered'
        elif picking_status == 'cancelled' and order_status == 'partial':
            event_status = 'cancelled'
    else:
        if picking_status == 'ready' and not tracking_url:
            event_status = 'preparing'
    return event_status

