from odoo import http
from odoo.http import request

import logging
import json
import datetime

_logger = logging.getLogger("Conversion Engine - Order Controller")

class OrderController(http.Controller):

    @http.route('/webhook_cengine/order', type='json', auth='public', methods=['POST'], csrf=False)
    def create_order_from_webhook(self):

        host = request.httprequest.headers.get("x-webhook-source")
        
        secret = request.httprequest.headers.get("x-webhook-signature")

        event = request.httprequest.headers.get("x-webhook-topic")

        webhook_id = request.httprequest.headers.get("x-webhook-id")

        data = {'items': [request.jsonrequest],
                'total_count': 1,
                'limit': 25,
                'skip': 0}

        data = json.dumps(data)

        _logger.info('Webhook for orders received - %s', data)

        # Check if the webhook exists:
        webhook = request.env['cengine.webhook.ept'].sudo().search([('response_webhook_id', '=', webhook_id)])

        if webhook:
            self.env['cengine.webhook.logs'].sudo().create({
                'instance_id': webhook.instance_id.id,
                'webhook_id': webhook_id,
                'webhook_source': host,
                'webhook_signature': secret,
                'webhook_topic': event,
                'webhook_data': request.jsonrequest
            })

            webhook.write({'last_run': datetime.datetime.now()})
        else:
            _logger.error('Webhook not found')