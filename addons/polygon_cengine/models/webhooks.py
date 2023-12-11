from odoo import api

import json
import requests

import logging

_logger = logging.getLogger("Webhooks Logs")

@api.model
def create_webhook(secret_key, webhook_type, url, hostname, api_key):
    # Create webhook:
    # Create the headers:
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
        'Cookie': ''
    }
    payload = json.dumps({"target": url, "secret": secret_key, "events": [webhook_type]})

    # Send request to Conversion Engine to create webhook:
    response = requests.request("POST", hostname, headers=headers, data=payload)

    # Check if webhook was created successfully:
    if response.status_code == 200:
        response_json = response.json()
        response_webhook_id = response_json['id']
        _logger.info('Webhook created successfully with id: ' + str(response_webhook_id))
        _logger.info('Webhook response: ' + response.text)
        return response_webhook_id

    else:
        _logger.error('Webhook creation failed with status code: ' + str(response.status_code) + ' and response: ' + str(response.text))
        return False
    
def delete_webhook(webhook_id, hostname, api_key):
    # Delete webhook:
    # Create the headers:
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
        'Cookie': ''
    }
    data = {}

    # Send request to Conversion Engine to delete webhook:
    response = requests.delete(hostname + '/' + str(webhook_id), headers=headers, data=json.dumps(data))

    # Check if webhook was deleted successfully:
    if response.status_code == 200:
        return True

    else:
        _logger.error('Webhook deletion failed with status code: ' + str(response.status_code) + ' and response: ' + str(response.text))
        return False