from odoo import models, fields

import logging
import pytz
import datetime
import requests

_logger = logging.getLogger("Scheduling queue throug cron")

class CengineSchedulerContacts(models.Model):
    _name = 'cengine.scheduler.contacts.ept'
    _description = 'Cengine Scheduler Contacts'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    schedule_id = fields.Many2one('cengine.scheduler.ept', string="Schedule", tracking=True, required=True, index=True, readonly=True)
    instance_id = fields.Many2one('cengine.instance.ept', string="Instance", tracking=True, required=True, index=True, readonly=True)
    owner_id = fields.Many2one('res.partner', string="Owner", tracking=True, required=True, index=True, readonly=True)
    data = fields.Text(string="Data", readonly=True)
    record_count = fields.Integer(string="Record Count", tracking=True, required=True, index=True, readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done'), ('failed', 'Failed')], string="State", tracking=True, default='draft', readonly=True)

    def cengine_products_scheduler(self):

        # Run for all active instances in cengine:
        instances = self.env['cengine.instance.ept'].search([('active', '=', True)])

        for instance in instances:
            host_name = instance.host_name
            api_key = instance.api_key
            owner_id = instance.polygon_client_id.partner_id.id
            if instance.last_order_import:
                last_order_import = instance.last_order_import
            else:
                last_order_import = instance.import_orders_after_date

            # Convert to user timezone:
            last_order_import = pytz.utc.localize(last_order_import).astimezone(pytz.timezone(instance.default_user.tz or
                                                                          'UTC')).strftime('%Y-%m-%dT%H:%M:%S%z')
            
            datetime_now = pytz.utc.localize(datetime.datetime.now()).astimezone(pytz.timezone(instance.default_user.tz or
                                                                          'UTC')).strftime('%Y-%m-%dT%H:%M:%S%z')
            
            # Convert datetime to Unix epoch:
            last_order_import = int(datetime.datetime.strptime(last_order_import, '%Y-%m-%dT%H:%M:%S%z').timestamp())
            datetime_now = int(datetime.datetime.strptime(datetime_now, '%Y-%m-%dT%H:%M:%S%z').timestamp())

            # Create the schedule:
            schedule = self.env['cengine.scheduler.ept'].create({
                'schedule_type': 'order',
                'instance_id': instance.id,
                'owner_id': owner_id,
                'data': '',
                'record_count': 0,
                'state': 'draft'
            })

            # Check if the hostname has https/http:
            if 'http://' in host_name or 'https://' in host_name:
                url = host_name + '/api/site/orders?created_at_min=' + str(last_order_import) + '&created_at_max=' + str(datetime_now)
            else:
                url = 'https://' + host_name + '/api/site/orders?created_at_min=' + str(last_order_import) + '&created_at_max=' + str(datetime_now)

            # Create the headers:
            headers = {
                'X-Auth-Client': api_key,
                'Content-Type': 'application/json'
            }

            body = {}

            # Make the request:
            response = requests.request("GET", url, headers=headers, data=body)

            # Check if the response is 200:
            if response.status_code == 200:
                # Get the response data:
                data = response.json()

                # Get the total count of orders:
                total_count = data['totalCount']

                # Create the order schedule:
                self.env['cengine.scheduler.order.ept'].create({
                                                                'schedule_id': schedule.id,
                                                                'instance_id': instance.id,
                                                                'owner_id': owner_id,
                                                                'data': response.text,
                                                                'record_count': total_count,
                                                                'state': 'draft'
                                                            })

                # Update the schedule record count:
                schedule.write({'record_count': total_count})

            else:
                # Create the order schedule:
                self.env['cengine.scheduler.order.ept'].create({
                                                                'schedule_id': schedule.id,
                                                                'instance_id': instance.id,
                                                                'owner_id': owner_id,
                                                                'data': response.text,
                                                                'record_count': 0,
                                                                'state': 'failed'
                                                            })
                # Update the schedule record count and state:
                schedule.write({'record_count': 0, 'state': 'failed'})
                _logger.warning("Error while fetching orders from Cengine for instance - %s", instance.name, exc_info=True)

