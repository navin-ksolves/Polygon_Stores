from odoo import models, fields, api
from odoo.exceptions import ValidationError
from .webhooks import create_webhook, delete_webhook
from .cengine_order_cron import CengineSchedulerOrder
from .cengine_products_cron import CengineSchedulerProduct

import logging
import hmac
import hashlib
import datetime

_logger = logging.getLogger("Conversion Engine Webhooks")

class ConversionEngineWebhookEpt(models.Model):
    _name = 'cengine.webhook.ept'
    _description = 'Conversion Engine Webhook EPT'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, copy=False)
    instance_id = fields.Many2one('cengine.instance.ept', string='Instance', required=True, copy=False)
    url = fields.Char(string='URL', required=True, copy=False)
    webhook_type = fields.Selection([('product', 'Product'), ('order', 'Order')],
                                    string='Webhook Type', required=True, copy=False)
    webhook_purpose = fields.Selection([('create', 'Create'), ('update', 'Update'), ('delete', 'Delete')],
                                    string='Webhook Purpose', required=True, copy=False)
    response_webhook_id = fields.Char(string='Response Webhook ID', required=False, copy=False)
    last_run = fields.Datetime(string='Last Run', required=False, copy=False)
    active = fields.Boolean(string='Active', default=True, copy=False)

    _sql_constraints = [('instance_webhook_unique_constraint', 'unique(instance_id, webhook_type, webhook_purpose)', 'Instance and webhook type must be unique.'),
                        ('url_webhook_unique_constraint', 'unique(response_webhook_id)', 'Server side webhook ID must be unique.')]

# When option to create webhooks is selected, create webhooks for each type
class CengineInstanceEpt(models.Model):
    _inherit = 'cengine.instance.ept'

    @api.model
    def cengine_create_product_webhook(self, record):

        record = self.env['cengine.instance.ept'].browse(record)

        # Get hostname from instance:
        hostname = record.host_name + '/api/site/webhooks'

        # Use odoo hostname:
        host = self.env['ir.config_parameter'].sudo().get_param('web.base.url') + '/webhook_cengine/product'
        # host = 'https://webhook.site/6abbce10-5b00-495e-abb7-39a4bfe968ba'

        response = create_webhook(record.secret_key,
                                'product_created',
                                host,
                                hostname,
                                record.access_token)

        if response is not False:
            _logger.info('Product Create webhook created successfully')
            record.webhook_ids = [(0, 0, {'name': 'Product Create Webhook - ' + record.name, 'instance_id': record.id, 
                                            'url': host, 'webhook_type': 'product', 'webhook_purpose': 'create', 'response_webhook_id': response})]
        else:
            _logger.error('Serverside error creating product webhook')
            raise ValidationError('Serverside error creating product webhook')
        
        response = create_webhook(record.secret_key,
                                'product_updated',
                                host,
                                hostname,
                                record.access_token)

        if response is not False:
            _logger.info('Product Update webhook created successfully')
            record.webhook_ids = [(0, 0, {'name': 'Product Create Webhook - ' + record.name, 'instance_id': record.id, 
                                            'url': host, 'webhook_type': 'product', 'webhook_purpose': 'update', 'response_webhook_id': response})]
            return True
        else:
            _logger.error('Serverside error creating product webhook')
            raise ValidationError('Serverside error creating product webhook')
    
    @api.model
    def cengine_create_order_webhook(self, record):

        record = self.env['cengine.instance.ept'].browse(record)
        
        hostname = record.host_name + '/api/site/webhooks'

        # Use odoo hostname:
        host = self.env['ir.config_parameter'].sudo().get_param('web.base.url') + '/webhook_cengine/order'
        # host = 'https://webhook.site/6abbce10-5b00-495e-abb7-39a4bfe968ba'

        response = create_webhook(record.secret_key,
                                'order_created',
                                host,
                                hostname,
                                record.access_token)

        if response is not False:
            _logger.info('Order Create webhook created successfully')
            record.webhook_ids = [(0, 0, {'name': 'Order Create Webhook - ' + record.name, 'instance_id': record.id, 
                                            'url': host, 'webhook_type': 'order', 'webhook_purpose': 'create', 'response_webhook_id': response})]
        else:
            _logger.error('Serverside error creating order webhook')
            raise ValidationError('Serverside error creating order webhook')
        
        response = create_webhook(record.secret_key,
                                'order_updated',
                                host,
                                hostname,
                                record.access_token)

        if response is not False:
            _logger.info('Order Update webhook created successfully')
            record.webhook_ids = [(0, 0, {'name': 'Order Updated Webhook - ' + record.name, 'instance_id': record.id, 
                                            'url': host, 'webhook_type': 'order', 'webhook_purpose': 'update', 'response_webhook_id': response})]
            return True
        else:
            _logger.error('Serverside error creating order webhook')
            raise ValidationError('Serverside error creating order webhook')

    @api.model
    def cengine_delete_order_webhook(self, record):

        record = self.env['cengine.instance.ept'].browse(record)
        
        hostname = record.host_name + '/api/site/webhooks'

        webhook_id = record.webhook_ids.filtered(lambda x: x.webhook_type == 'order')

        for webhook in webhook_id:
            response = delete_webhook(webhook.response_webhook_id, hostname, record.access_token)

            if response is not False:
                _logger.info('Order webhook deleted successfully')
                webhook.unlink()
            
            else:
                _logger.error('Serverside error deleting order webhook')
                raise ValidationError('Serverside error deleting order webhook')

    
    @api.model
    def cengine_delete_product_webhook(self, record):

        record = self.env['cengine.instance.ept'].browse(record)
        
        hostname = record.host_name + '/api/site/webhooks'

        webhook_id = record.webhook_ids.filtered(lambda x: x.webhook_type == 'product')

        for webhook in webhook_id:
            response = delete_webhook(webhook.response_webhook_id, hostname, record.access_token)

            if response is not False:
                _logger.info('Product webhook deleted successfully')
                webhook.unlink()
            
            else:
                _logger.error('Serverside error deleting product webhook')
                raise ValidationError('Serverside error deleting product webhook')
        
    @api.model
    def create_cengine_webhooks(self, record):
        self.cengine_create_order_webhook(record)
        self.cengine_create_product_webhook(record)
        return True
    
    @api.model
    def delete_cengine_webhooks(self, record):
        self.cengine_delete_order_webhook(record)
        self.cengine_delete_product_webhook(record)
        return True
    
class CengineWebhooksLogs(models.Model):
    _name = 'cengine.webhook.logs'
    _description = 'Conversion Engine Webhook Logs'

    instance_id = fields.Many2one('cengine.instance.ept', string='Instance', required=True, copy=False)
    webhook_id = fields.Char(string='Webhook ID', required=True, copy=False)
    webhook_source = fields.Char(string='Webhook Source', required=True, copy=False)
    webhook_signature = fields.Char(string='Webhook Signature', required=True, copy=False)
    webhook_topic = fields.Char(string='Event Type', required=True, copy=False)
    webhook_data = fields.Char(string='Webhook Data', required=True, copy=False)
    status = fields.Selection([('success', 'Success'),
                               ('wrong_id', 'Wrong Webhook ID'),
                               ('wrong_source', 'Wrong Webhook Source'),
                               ('wrong_signature', 'Wrong Webhook Signature'),
                               ('wrong_topic', 'Wrong Webhook Topic')], string='Status', required=True, copy=False)
    
    @api.model
    def push_webhook(self, record):
        if self.status == 'success':
            if self.webhook_topic == 'order_created':
                # Create the schedule:
                schedule = self.env['cengine.scheduler.ept'].with_user(user=self.instance_id.default_user.id).create({
                    'schedule_type': 'order',
                    'instance_id': self.instance_id.id,
                    'owner_id': self.instance_id.polygon_client_id.partner_id.id,
                    'data': self.webhook_data,
                    'record_count': 1,
                    'state': 'draft'
                })

                self.env['cengine.scheduler.order.ept'].with_user(user=self.instance_id.default_user.id).create({
                                                                    'schedule_id': schedule.id,
                                                                    'instance_id': self.instance_id.id,
                                                                    'owner_id': self.instance_id.polygon_client_id.partner_id.id,
                                                                    'data': self.webhook_data,
                                                                    'record_count': 1,
                                                                    'state': 'draft',
                                                                })
                
                self.instance_id.with_user(user=self.instance_id.default_user.id).write({'last_order_import': datetime.utcnow()})

                self.env.cr.commit()

                # Run the schedule:
                CengineSchedulerOrder.cengine_order_import()
            
            if self.webhook_topic == 'product_created' or self.webhook_topic == 'product_updated':
                # Create the schedule:
                schedule = self.env['cengine.scheduler.ept'].with_user(user=self.instance_id.default_user.id).create({
                    'schedule_type': 'product',
                    'instance_id': self.instance_id.id,
                    'owner_id': self.instance_id.polygon_client_id.partner_id.id,
                    'data': self.webhook_data,
                    'record_count': 1,
                    'state': 'draft'
                })

                self.env['cengine.scheduler.product.ept'].with_user(user=self.instance_id.default_user.id).create({
                                                                    'schedule_id': schedule.id,
                                                                    'instance_id': self.instance_id.id,
                                                                    'owner_id': self.instance_id.polygon_client_id.partner_id.id,
                                                                    'source': 'webhook',
                                                                    'data': self.webhook_data,
                                                                    'record_count': 1,
                                                                    'state': 'draft',
                                                                    'remarks': 'Webhook'
                                                                })
                
                self.instance_id.with_user(user=self.instance_id.default_user.id).write({'last_order_import': datetime.utcnow()})

                self.env.cr.commit()

                # Run the schedule:
                CengineSchedulerProduct.cengine_products_category()
                CengineSchedulerProduct.cengine_products_import()

    
    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            # Check if the webhook exists:
            webhook = self.env['cengine.webhook.ept'].sudo().search([('response_webhook_id', '=', val['webhook_id'])])
            
            host_name = webhook.instance_id.host_name

            secret_key = webhook.instance_id.secret_key

            # Remove the https:// or http:// from the host name:
            if host_name.startswith('https://'):
                host_name = host_name[8:]
            elif host_name.startswith('http://'):
                host_name = host_name[7:]
            
            if not webhook:
                val['status'] = 'wrong_id'
            elif host_name != val['webhook_source']:
                val['status'] = 'wrong_source'
            # The HMAC hex digest of the response body. The HMAC hex digest is generated using the SHA-512 hash function and the secret as the HMAC key
            elif hmac.new(secret_key.encode(), val['webhook_data'].encode(), hashlib.sha512).hexdigest() != val['webhook_signature']:
                val['status'] = 'wrong_signature'
            elif val['webhook_topic'] != 'order_created' or val['webhook_topic'] != 'order_updated' or val['webhook_topic'] != 'product_created' or val['webhook_topic'] != 'product_updated':
                val['status'] = 'wrong_topic'
            else:
                val['status'] = 'success'
            
            record = super(CengineWebhooksLogs, self).create(vals)

            self.env.cr.commit()
            # Send record to push_webhook:
            self.push_webhook(record)