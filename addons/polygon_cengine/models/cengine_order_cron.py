from odoo import models, fields, api
from datetime import datetime

import calendar
import logging
import requests
import json

_logger = logging.getLogger("Scheduling order queue through cron")

class CengineSchedulerOrder(models.Model):
    _name = 'cengine.scheduler.order.ept'
    _description = 'Cengine Scheduler Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    schedule_id = fields.Many2one('cengine.scheduler.ept', string="Schedule", tracking=True, required=True, index=True, readonly=True)
    instance_id = fields.Many2one('cengine.instance.ept', string="Instance", tracking=True, required=True, index=True, readonly=True)
    owner_id = fields.Many2one('res.partner', string="Owner", tracking=True, required=True, index=True, readonly=True)
    source = fields.Selection([('webhook', 'Webhook'), ('manual', 'Manual')], string="Source", required=True, index=True, readonly=True)
    data = fields.Text(string="Data", readonly=True)
    record_count = fields.Integer(string="Record Count", tracking=True, required=True, index=True, readonly=True)
    attempts = fields.Integer(string="Attempts", tracking=True, readonly=True, default=0)
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done'), ('failed', 'Failed')], string="State", tracking=True, default='draft', readonly=True)
    remarks = fields.Text(string="Remarks", readonly=True)

    @api.model
    def cengine_order_import(self):

        # Run for all draft order schedules:
        schedules = self.env['cengine.scheduler.order.ept'].search([('state', '=', 'draft')])

        for schedule in schedules:
            # Parse the JSON in the data field:
            data = json.loads(schedule.data)

            total_count = schedule.record_count
            completed_count = 0

            for item in data['items']:
                _logger.info('Processing item: %s' % item)

                _logger.info('Shipping required: %s' % item['shippingRequired'])
                if item['shippingRequired'] == True: 
                    # Convert order datetime from unix epoch to datetime:
                    order_datetime = datetime.fromtimestamp(item['created']).strftime('%Y-%m-%d %H:%M:%S%z')
                    order_id = item['id']
                    invoice_number = item['invoiceNo']
                    
                    customer = self.env['cengine.customer.ept'].sudo().search([('email', '=', item['customerEmail']),
                                                                             ('instance_id', '=', schedule.instance_id.id)])
                    
                    if not customer:
                        # Create the customer:
                        customer = self.env['cengine.customer.ept'].with_user(user=schedule.instance_id.default_user.id).create({
                                                                                            'name': item['customerName'],
                                                                                            'phone': item['billingAddress']['phone'],
                                                                                            'email': item['customerEmail'],
                                                                                            'instance_id': schedule.instance_id.id
                                                                                        })
                        
                    _logger.info('Customer created! Customer ID: %s' % customer.id)
                        
                    if customer:
                        # Check if billing and shipping address already exists:
                        billing_address = self.env['cengine.customer.locations'].sudo().search([('customer_id', '=', customer.id),
                                                                                        ('is_billing', '=', True),
                                                                                        ('street', '=', item['billingAddress']['address'])])
                        
                        shipping_address = self.env['cengine.customer.locations'].sudo().search([('customer_id', '=', customer.id),
                                                                                        ('is_shipping', '=', True),
                                                                                        ('street', '=', item['shippingAddress']['address'])])
                        
                        if not billing_address:
                            # Create the billing address:
                            billing_address = self.env['cengine.customer.locations'].with_user(user=schedule.instance_id.default_user.id).create({
                                'name': item['billingAddress']['name'],
                                'street': item['billingAddress']['address'],
                                'street2': item['billingAddress']['address2'],
                                'phone': item['billingAddress']['phone'],
                                'city': item['billingAddress']['city'],
                                'state': item['billingAddress']['state'],
                                'country': item['billingAddress']['country'],
                                'customer_id': customer.id,
                                'is_billing': True,
                                'is_shipping': False
                            })

                        if not shipping_address:
                            # Create the shipping address:
                            shipping_address = self.env['cengine.customer.locations'].with_user(user=schedule.instance_id.default_user.id).create({
                                'name': item['shippingAddress']['name'],
                                'street': item['shippingAddress']['address'],
                                'street2': item['shippingAddress']['address2'],
                                'phone': item['billingAddress']['phone'],
                                'city': item['shippingAddress']['city'],
                                'state': item['shippingAddress']['state'],
                                'country': item['shippingAddress']['country'],
                                'customer_id': customer.id,
                                'is_billing': False,
                                'is_shipping': True
                            })
                        
                        account_sale_tax = schedule.instance_id.company_id.account_sale_tax_id
                        
                        account_zero_tax = self.env['account.tax'].search([('company_id', '=', schedule.instance_id.company_id.id),
                                                                            ('real_amount', '=', '0'),
                                                                            ('type_tax_use', '=', 'sale')], limit=1)
                        
                        account_fiscal_position_default = self.env['account.fiscal.position'].search([('country_id', '!=', None),
                                                                                                   ('company_id', '=', schedule.instance_id.company_id.id)], limit=1)
                        
                        account_fiscal_position_zero = self.env['account.fiscal.position'].search([('country_id', '=', None),
                                                                                                   ('company_id', '=', schedule.instance_id.company_id.id)], limit=1)

                        if len (item['taxes']) > 0:
                            taxes = item['taxes'][0]

                            taxes_total = taxes['total']

                            if taxes_total > 0:
                                account_sale_tax_id = account_sale_tax.id
                                account_fiscal_position_id = account_fiscal_position_default.id
                                account_sale_tax_amount = account_sale_tax.amount
                                if taxes['applyToShipping'] == True:
                                    shipping_tax_id = account_sale_tax_id
                                    shipping_tax_value = account_sale_tax.amount
                                else:
                                    shipping_tax_id = account_zero_tax.id
                                    shipping_tax_value = account_zero_tax.amount
                            else:
                                account_sale_tax_id = account_zero_tax.id
                                account_fiscal_position_id = account_fiscal_position_zero.id
                                account_sale_tax_amount = account_zero_tax.amount
                                shipping_tax_id = account_zero_tax.id
                                shipping_tax_value = account_zero_tax.amount

                        else:
                            taxes_total = 0
                            account_sale_tax_id = account_zero_tax.id
                            account_sale_tax_amount = account_zero_tax.amount
                            shipping_tax_id = account_zero_tax.id
                            shipping_tax_value = account_zero_tax.amount

                        # Create the order:

                        vals = {
                                'name': item['invoiceNo'],
                                'online_order_id': order_id,
                                'order_partner_id': customer.id,
                                'delivery_address_id': shipping_address.id,
                                'invoice_address_id': billing_address.id,
                                'owner_id': schedule.owner_id.id,
                                'instance_id': schedule.instance_id.id,
                                'invoice_no': invoice_number,
                                'paid': item['paid'],
                                'total_tax': taxes_total if taxes_total > 0 else 0,
                                'order_datetime': order_datetime,
                                'payment_method': item['paymentMethod'],
                                'subtotal_price': item['subTotal'],
                                'discount_code': item['discountCode'],
                                'discount_type': item['discountType'],
                                'total_discount': item['discountAmount'],
                                'shipping_price': item['shippingAmount'],
                                'taxes': taxes['name'] if taxes else '',
                                'total_price': item['total'],
                                'schedule_id': schedule.id,
                                'item_id': item['id'],
                                'fiscal_position_id': account_fiscal_position_id,
                            }
                        _logger.info('Creating order with vals: %s' % vals)
                        order = self.env['cengine.order.ept'].with_user(user=schedule.instance_id.default_user.id).create(vals)
                        
                        _logger.info('Order created! Order ID: %s, processing other items' % order[0])

                        if order:
                            completed_count = completed_count + 1
                            order_id = order[0]
                            so_id = order[1]

                            line_count = 0
                            lines_completed = 0

                            # Create the order lines:
                            for line in item['items']:
                                if len(line['variation']) > 0 :
                                    for variant in line['variation']:
                                        line['name'] = line['name'] + ' - ' + variant['name'] + ' - ' + variant['value']

                                _logger.info('Creating order line with vals: %s' % line)

                                total_price = round(line['total'] / line['quantity'],2)
                                total_ex_tax = round(total_price / (1 + (account_sale_tax_amount/100)),2)

                                order_line = self.env['cengine.order.lines.ept'].with_user(user=schedule.instance_id.default_user.id).create({
                                                                                                                                    'order_id': int(order_id),
                                                                                                                                    'so_id': so_id,
                                                                                                                                    'name': line['name'],
                                                                                                                                    'order_line_id': line['id'],
                                                                                                                                    'item_id': line['productId'],
                                                                                                                                    'price': total_ex_tax,
                                                                                                                                    'quantity': line['quantity'],
                                                                                                                                    'options': line['variation'],
                                                                                                                                    'instance_id': schedule.instance_id.id,
                                                                                                                                    'variants': line['variation'],
                                                                                                                                    'sku': line['sku'],
                                                                                                                                    'so_line_count': line_count + 1,
                                                                                                                                    'tax_id': account_sale_tax_id,
                                                                                                                                    })
                                
                                if order_line:
                                    line_count = line_count + 1
                                    lines_completed = lines_completed + 1
                                else:
                                    line_count = line_count + 1
                                    lines_completed = lines_completed + 0
                                _logger.info('Order line created! Order line ID: %s' % order_line)
                        
                        _logger.info('Completed lines count: %s, Total lines count: %s' % (lines_completed, line_count))

                        self.env.cr.commit()

                        so = self.env['sale.order'].with_user(user=schedule.instance_id.default_user.id).search([('id', '=', so_id)])

                        if item['discountAmount'] > 0.0:
                            discount_product_template_ce = self.env['cengine.product.template'].search([('cengine_product_template_id', '=', 'default_discount'),
                                                    ('owner_id', '=', schedule.owner_id.id),
                                                    ('instance_id', '=', schedule.instance_id.id)], limit=1)
                            
                            discount_product_template = discount_product_template_ce.product_id.product_tmpl_id
                            
                            discount_product = discount_product_template_ce.product_id

                            # Check if the so_lines with discount_product alredy exist:
                            so_lines = self.env['sale.order.line'].search([('order_id', '=', so.id),
                                                                            ('product_id', '=', discount_product.id)])

                            if not so_lines:
                                so.with_user(user=schedule.instance_id.default_user.id).write({
                                                                                                'order_line': [(0, 0, {
                                                                                                    'name': discount_product_template.name,
                                                                                                    'product_id': discount_product.id,
                                                                                                    'product_uom_qty': 1,
                                                                                                    'price_unit': item["discountAmount"] * -1
                                                                                                })]
                                                                                            })
                            
                        if item['shippingAmount'] > 0.0:
                            shipping_product_template_ce = self.env['cengine.product.template'].search([('cengine_product_template_id', '=', 'default_shipping'),
                                                    ('owner_id', '=', schedule.owner_id.id),
                                                    ('instance_id', '=', schedule.instance_id.id)], limit=1)
                            
                            shipping_product_template = shipping_product_template_ce.product_id.product_tmpl_id
                            
                            shipping_product = shipping_product_template_ce.product_id

                            shipping_amount = round(item['shippingAmount'] / (1 + (shipping_tax_value/100)),2)

                            # Check if the so_lines with shipping_product alredy exist:
                            so_lines = self.env['sale.order.line'].search([('order_id', '=', so.id),
                                                                            ('product_id', '=', shipping_product.id)])
                            
                            if not so_lines:
                                so.with_user(user=schedule.instance_id.default_user.id).write({
                                                                                            'order_line': [(0, 0, {
                                                                                                'name': shipping_product_template.name,
                                                                                                'product_id': shipping_product.id,
                                                                                                'product_uom_qty': 1,
                                                                                                'price_unit': shipping_amount,
                                                                                                'tax_id': [(6,0, [shipping_tax_id])]
                                                                                            })]
                                                                                        })
                            
                            _logger.info('Confirming SO: %s' % so.id)
                        
                        if so.state == 'draft':
                            _logger.info('SO state: %s' % so.state)
                            so.with_user(user=schedule.instance_id.default_user.id).action_confirm()

            _logger.info('Completed count: %s, Total count: %s' % (completed_count, total_count))

            if completed_count == total_count and lines_completed == line_count:
                schedule.write({'state': 'done', 'attempts': schedule.attempts + 1})
                schedule.schedule_id.write({'state': 'done'})
            else:
                schedule.write({'state': 'draft','attempts': schedule.attempts + 1})
                schedule.schedule_id.write({'state': 'draft'})
        
        return True
    
    @api.model
    def cengine_order_auth(self, url, headers, payload, limit, skip):
        
        url = url + "&limit=" + str(limit) + "&skip=" + str(skip)
        
        # Make the request:
        response = requests.request("GET", url, headers=headers, data=payload)

        return response

    @api.model
    def cengine_order_scheduler(self):

        # Run for all active instances in cengine:
        instances = self.env['cengine.instance.ept'].search([('active', '=', True)])

        webhook_type = 'order'

        instances = instances.filtered(lambda x: webhook_type not in x.webhook_ids.mapped('webhook_type'))

        for instance in instances:
            host_name = instance.host_name
            api_key = instance.access_token
            owner_id = instance.polygon_client_id.partner_id.id
            time_now = datetime.utcnow()
            # Convert to unix epoch
            time_now_epoch = int(calendar.timegm(time_now.utctimetuple()))
            _logger.info("Last Order Import - %s", instance.last_order_import)
            if instance.last_order_import:
                last_order_import = instance.last_order_import
                # Convert to unix epoch:
                last_order_import = int(datetime.timestamp(last_order_import))
            else:
                last_order_import = instance.import_orders_after_date
                # Convert to unix epoch:
                last_order_import = int(datetime.timestamp(last_order_import))

            # Check if the hostname has https/http:
            if 'http://' in host_name or 'https://' in host_name:
                url = host_name + '/api/site/orders?created_at_min=' + str(last_order_import) + '&created_at_max=' + str(time_now_epoch)
            else:
                url = 'https://' + host_name + '/api/site/orders?created_at_min=' + str(last_order_import) + '&created_at_max=' + str(time_now_epoch)

            _logger.info("URL - %s", url)

            # Create the schedule:
            schedule = self.env['cengine.scheduler.ept'].with_user(user=instance.default_user.id).create({
                'schedule_type': 'order',
                'instance_id': instance.id,
                'owner_id': owner_id,
                'data': '',
                'record_count': 0,
                'state': 'draft'
            })

            # Create the headers:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}',
                'Cookie': ''
            }

            payload = json.dumps({})

            limit = 25
            skip = 0

            # Make the first request:
            response = self.cengine_order_auth(url, headers, payload, limit=limit, skip=skip)

            _logger.info("Response - %s", response.text)

            # Check if the response is 200:
            if response.status_code == 200:
                # Get the response data:
                data = response.json()
                # Get the total count of orders:
                total_count = data['totalCount']
                #Get the limit of data sent:
                limit = data['limit']
                # Create the order schedule:
                self.env['cengine.scheduler.order.ept'].with_user(user=instance.default_user.id).create({
                                                                'schedule_id': schedule.id,
                                                                'instance_id': instance.id,
                                                                'owner_id': owner_id,
                                                                'source': 'manual',
                                                                'data': response.text,
                                                                'record_count': total_count if total_count > 0 else 0,
                                                                'state': 'draft' if total_count > 0 else 'done'
                                                            })
                
                _logger.info("API Response - %s", response.text)

                # Update the schedule record count:
                schedule.with_user(user=instance.default_user.id).write({'record_count': total_count,
                                'data': response.text,
                                'state': 'draft' if total_count > 0 else 'done'
                                })
                
                instance.with_user(user=instance.default_user.id).write({'last_order_import': time_now})

                remaining_count = total_count - limit

            else:
                # Create the order schedule:
                self.env['cengine.scheduler.order.ept'].with_user(user=instance.default_user.id).create({
                                                                'schedule_id': schedule.id,
                                                                'instance_id': instance.id,
                                                                'owner_id': owner_id,
                                                                'source': 'manual',
                                                                'data': response.text,
                                                                'record_count': 0,
                                                                'state': 'failed'
                                                            })
                # Update the schedule record count and state:
                schedule.with_user(user=instance.default_user.id).write({'record_count': 0, 'state': 'failed'})
                _logger.warning("Error while fetching orders from Cengine for instance - %s", instance.name, exc_info=True)
                _logger.warning(response.status_code)
                _logger.warning(response.text)
                remaining_count = 0

            # Check if the total count is greater than the limit:
            while remaining_count > 0:
                skip = limit

                # Make the remaining request:
                response = self.cengine_order_auth(url, headers, payload, limit=limit, skip=skip)

                _logger.info("Response - %s", response.text)

                # Check if the response is 200:
                if response.status_code == 200:
                    # Get the response data:
                    data = response.json()
                    # Get the total count of orders:
                    total_count = data['totalCount']
                    #Get the limit of data sent:
                    limit = data['limit']
                    # Create the order schedule:
                    self.env['cengine.scheduler.order.ept'].with_user(user=instance.default_user.id).create({
                                                                    'schedule_id': schedule.id,
                                                                    'instance_id': instance.id,
                                                                    'owner_id': owner_id,
                                                                    'source': 'manual',
                                                                    'data': response.text,
                                                                    'record_count': total_count if total_count > 0 else 0,
                                                                    'state': 'draft' if total_count > 0 else 'done'
                                                                })

                    # Update the schedule record count:
                    schedule.with_user(user=instance.default_user.id).write({'record_count': total_count,
                                    'data': response.text,
                                    'state': 'draft' if total_count > 0 else 'done'
                                    })

                else:
                    # Create the order schedule:
                    self.env['cengine.scheduler.order.ept'].with_user(user=instance.default_user.id).create({
                                                                    'schedule_id': schedule.id,
                                                                    'instance_id': instance.id,
                                                                    'owner_id': owner_id,
                                                                    'source': 'manual',
                                                                    'data': response.text,
                                                                    'record_count': 0,
                                                                    'state': 'failed'
                                                                })
                    # Update the schedule record count and state:
                    schedule.with_user(user=instance.default_user.id).write({'record_count': 0, 'state': 'failed'})
                    _logger.warning("Error while fetching orders from Cengine for instance - %s", instance.name, exc_info=True)
                    _logger.warning(response.status_code)
                    _logger.warning(response.text)

                remaining_count = remaining_count - limit
                skip = skip + limit

            instance.with_user(user=instance.default_user.id).write({'last_order_import': time_now})

            self._cr.commit()
        
        return True
                    
    @api.model
    def cengine_order_cron(self):
        self.cengine_order_scheduler()
        self.cengine_order_import()
        _logger.info("Cengine Order Import Cron Finished")
        return True