from odoo import models, fields, api
from odoo.exceptions import ValidationError

import logging
import pytz
import datetime
import requests
import json

_logger = logging.getLogger("Scheduling queue throug cron")

class CengineSchedulerProduct(models.Model):
    _name = 'cengine.scheduler.product.ept'
    _description = 'Cengine Scheduler Product'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    schedule_id = fields.Many2one('cengine.scheduler.ept', string="Schedule", tracking=True, required=True, index=True, readonly=True)
    instance_id = fields.Many2one('cengine.instance.ept', string="Instance", tracking=True, required=True, index=True, readonly=True)
    owner_id = fields.Many2one('res.partner', string="Owner", tracking=True, required=True, index=True, readonly=True),
    source = fields.Selection([('webhook', 'Webhook'), ('manual', 'Manual')], string="Source", required=True, index=True, readonly=True)
    data = fields.Text(string="Data", readonly=True)
    record_count = fields.Integer(string="Record Count", tracking=True, required=True, index=True, readonly=True)
    attempts = fields.Integer(string="Attempts", tracking=True, readonly=True, default=0)
    state = fields.Selection([('draft', 'Draft'), ('progress', 'In Progress'), ('done', 'Done'), ('failed', 'Failed')], string="State", tracking=True, default='draft', readonly=True)
    remarks = fields.Text(string="Remarks", readonly=True)

    @api.model
    def cengine_products_category(self):
        # Run for all draft product schedules:
        schedules = self.env['cengine.scheduler.product.ept'].search([('state', '=', 'draft')])

        for schedule in schedules:
            schedule.with_user(user=schedule.instance_id.default_user.id).write({'state': 'progress'})
            schedule.schedule_id.with_user(user=schedule.instance_id.default_user.id).write({'state': 'progress'})
            # Parse the JSON in the data field:
            data = json.loads(schedule.data)

            for item in data['items']:
                
                # Check if product_category exists:
                for category in item['categories']:
                    if category['parentCategory'] != 0:
                        parent_cat = self.env['cengine.product.category'].search(['cengine_product_category_id', '=', category['parentCategory']], limit=1)

                        if not parent_cat:
                            parent_cat = self.env['cengine.product.category'].with_user(schedule.instance_id.default_user.id).create({
                                                                                        'cengine_product_category_id': category['parentCategory'],
                                                                                        'name': 'Temp_Name' + str(category['parentCategory']),
                                                                                        'cengine_product_category_url': 'Temp_URL' + str(category['parentCategory']),
                                                                                        'parent_category_id': 0,
                                                                                        'owner_id': schedule.owner_id.id,
                                                                                    })
                            product_cat = self.env['cengine.product.category'].with_user(schedule.instance_id.default_user.id).create({
                                                                                        'cengine_product_category_id': category['id'],
                                                                                        'name': category['name'],
                                                                                        'cengine_product_category_url': category['url'],
                                                                                        'parent_category_id': parent_cat.id,
                                                                                        'owner_id': schedule.owner_id.id,
                                                                                    })
                        else:
                            product_cat = self.env['cengine.product.category'].with_user(schedule.instance_id.default_user.id).create({
                                                                                        'cengine_product_category_id': category['id'],
                                                                                        'name': category['name'],
                                                                                        'cengine_product_category_url': category['url'],
                                                                                        'parent_category_id': parent_cat.id,
                                                                                        'owner_id': schedule.owner_id.id,
                                                                                    })
                    else:
                        product_cat = self.env['cengine.product.category'].with_user(schedule.instance_id.default_user.id).create({
                                                                                        'cengine_product_category_id': category['id'],
                                                                                        'name': category['name'],
                                                                                        'cengine_product_category_url': category['url'],
                                                                                        'parent_category_id': 0,
                                                                                        'owner_id': schedule.owner_id.id,
                                                                                    })
                        
                    if product_cat:
                        return product_cat
                    else:
                        raise ValidationError("Error while creating product category")
                    
            schedule.with_user(user=schedule.instance_id.default_user.id).write({'remarks': 'Product categories created'})

    @api.model
    def cengine_products_import(self):

        # Run for all draft product schedules:
        schedules = self.env['cengine.scheduler.product.ept'].search([('state', '=', 'progress')])

        for schedule in schedules:
            # Parse the JSON in the data field:
            data = json.loads(schedule.data)

            total_count = schedule.record_count
            done = 0
            for item in data['items']:
                # Check if product_category exists:
                product_category_ids = [self.env['cengine.product.category'].search([
                    ('cengine_product_category_id', '=', category['id']),
                    ('owner_id', '=', schedule.owner_id.id)], limit=1).id for category in item['categories']]

                # Check if product exists:
                product_template = self.env['cengine.product.template'].search([
                    ('cengine_product_template_id', '=', item['id']),
                    ('owner_id', '=', schedule.owner_id.id)], limit=1)
                
                if product_template:
                    product_template.write({'name': item['title'] + ' - ' + str(item['id']),
                                            'description': item['description'],
                                            'owner_id': schedule.owner_id.id})
                    
                    product_template.product_id.product_tmpl_id.write({'name': item['title'] + ' - ' + str(item['id']),
                                                                        'description': item['description'],
                                                                        'product_owner': schedule.owner_id.id})

                if not product_template:
                    product_template = self.env['cengine.product.template'].with_user(schedule.instance_id.default_user.id).create({
                        'name': item['title'],
                        'description': item['description'],
                        'owner_id': schedule.owner_id.id,
                        'instance_id': schedule.instance_id.id,
                        'cengine_product_template_id': item['id'],
                        'cengine_product_template_url': item['url'],
                        'cengine_product_template_type': item['type'],
                        'cengine_product_template_status': item['hidden'],
                        'cengine_product_categ_id': product_category_ids and product_category_ids[0] or False
                    })
                
                images = []
                images = item['images']
                cengine_product_template_id = product_template.id
                # Create a list of dictionaries for each image
                image_vals_list = [{'images': image, 'cengine_product_template_id': cengine_product_template_id} for image in images]
                self.env['cengine.product.template.image'].with_user(schedule.instance_id.default_user.id).create(image_vals_list)
                self.env['cengine.product.template.image'].with_user(schedule.instance_id.default_user.id).realign_images(image_vals_list)

                # Check if options exist and create them if necessary:
                for option in item['options']:
                    _logger.info("Option - %s", option)
                    option_search = self.env['cengine.product.options'].search([('name', '=', option['name'])])
                    if not option_search:
                        option_create = self.env['cengine.product.options'].with_user(schedule.instance_id.default_user.id).create({
                            'name': option['name'],
                            'advanced': option['advanced']
                        })
                        option_search = option_create

                        # Check if 'values' key exists in the 'option' dictionary
                        if 'values' in option:
                            for option_value in option['values']:
                                if option_value:
                                    self.env['cengine.product.option.values'].with_user(schedule.instance_id.default_user.id).create({
                                        'name': option_value,
                                        'cengine_product_options_id': option_search.id,
                                    })
                        else:
                            _logger.warning("No 'values' key found in option dictionary: %s", option)
                    else:
                        # Check if 'values' key exists in the 'option' dictionary
                        if 'values' in option:
                            for option_value in option['values']:
                                if option_value:
                                    option_value_search = self.env['cengine.product.option.values'].search([
                                        ('name', '=', option_value),
                                        ('cengine_product_options_id', '=', option_search.id)])
                                    if not option_value_search:
                                        self.env['cengine.product.option.values'].with_user(schedule.instance_id.default_user.id).create({
                                            'name': option_value,
                                            'cengine_product_options_id': option_search.id,
                                        })
                        else:
                            _logger.warning("No 'values' key found in option dictionary: %s", option)

                # Check if product variants exist and create them if necessary:
                for variant in item['variants']:
                    _logger.info("Variant being processed - %s", variant)
                    
                    self.env['cengine.product.variants'].with_user(schedule.instance_id.default_user.id).create({
                        'sku': variant['sku'],
                        'price': variant['price'],
                        'sale_price': variant.get('regularPrice', 0) if variant.get('regularPrice') is not None else 0,
                        'on_sale': variant.get('onSale', False),
                        'quantity': variant.get('quantity', 0) if variant.get('quantity') is not None else 0,
                        'weight': variant.get('weight', 0) if variant.get('weight') is not None else 0,
                        'options': variant['options'],
                        'owner_id': schedule.owner_id.id,
                        'cengine_product_template_id': product_template.id,
                    })

            done += 1

            product_category = self.env['cengine.product.category'].search([('name', '=', 'All'),
                                                                        ('owner_id', '=', schedule.owner_id.id)])
            
            if not product_category:
                product_category = self.env['cengine.product.category'].create({'name': 'All',
                                                                                'owner_id': schedule.owner_id.id,
                                                                                'parent_category_id': 0,
                                                                                'cengine_product_category_id': 1,
                                                                                'cengine_product_category_url': 'default'})
            
            # Check if default_shipping and default_discount products are created:
            default_shipping = self.env['product.template'].search([('name', '=', 'Default Shipping'),
                                                    ('company_id', '=', self.env.company.id),
                                                    ('product_owner', '=', schedule.owner_id.id)])

            if not default_shipping:
                # Create default shipping product:
                product_template_id = self.env['cengine.product.template'].create({'name': 'Default Shipping',
                                                                                'description': 'Default Shipping',
                                                                                'cengine_product_template_type': 'service',
                                                                                'instance_id': schedule.instance_id.id,
                                                                                'default_shipping': True,
                                                                                'active': True,
                                                                                'owner_id': schedule.owner_id.id,
                                                                                'cengine_product_categ_id': product_category.id,
                                                                                'cengine_product_template_id': 'default_shipping',
                                                                                'default_shipping': True
                                                                                })
                
                _logger.info('Default shipping product created. Product ID: ' + str(product_template_id.id))

            default_discount = self.env['product.template'].search([('name', '=', 'Default Discount'),
                                                    ('company_id', '=', self.env.company.id),
                                                    ('product_owner', '=', schedule.owner_id.id)])
                
            if not default_discount:
                # Create default discount product:
                product_id = self.env['cengine.product.template'].create({'name': 'Default Discount',
                                                                            'description': 'Default Discount',
                                                                            'cengine_product_template_type': 'service',
                                                                            'instance_id': schedule.instance_id.id,
                                                                            'default_shipping': True,
                                                                            'active': True,
                                                                            'owner_id': schedule.owner_id.id,
                                                                            'cengine_product_categ_id': product_category.id,
                                                                            'cengine_product_template_id': 'default_discount',
                                                                            'default_discount': True
                                                                            })
                
                _logger.info('Default discount product created. Product ID: ' + str(product_id.id))

            if done == total_count:
                schedule.with_user(user=schedule.instance_id.default_user.id).write({'state': 'done',
                                                                            'attempts': schedule.attempts + 1})
                schedule.schedule_id.with_user(user=schedule.instance_id.default_user.id).write({'state': 'done'})
            else:
                schedule.with_user(user=schedule.instance_id.default_user.id).write({'state': 'failed',
                                                                            'attempts': schedule.attempts + 1,
                                                                            'remarks': 'Failed to import products'})
                schedule.schedule_id.with_user(user=schedule.instance_id.default_user.id).write({'state': 'failed'})
    
    @api.model
    def cengine_auth_limit(self, url, headers, payload, limit, skip):
        
        url = url + "&limit=" + str(limit) + "&skip=" + str(skip)
        
        # Make the request:
        response = requests.request("GET", url, headers=headers, data=payload)

        return response
    
    @api.model
    def cengine_products_scheduler(self):

        # Run for all active instances in cengine:
        instances = self.env['cengine.instance.ept'].search([('active', '=', True)])

        for instance in instances:
            host_name = instance.host_name
            api_key = instance.access_token
            owner_id = instance.polygon_client_id.partner_id.id
            time_now = datetime.datetime.now()
            # Check if the hostname has https/http:
            if 'http://' in host_name or 'https://' in host_name:
                url = host_name + '/api/site/products'
            else:
                url = 'https://' + host_name + '/api/site/products'

            _logger.info("URL - %s", url)

            # Create the headers:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}',
                'Cookie': ''
            }

            payload = json.dumps({})

            limit = 25
            skip = 0
            remaining_count = 1

            # Check if the total count is greater than the limit:
            while remaining_count > 0:

                # Make the remaining request:
                response = self.cengine_auth_limit(url, headers, payload, limit=limit, skip=skip)

                # Create the schedule:
                schedule = self.env['cengine.scheduler.ept'].with_user(user=instance.default_user.id).create({
                    'schedule_type': 'product',
                    'instance_id': instance.id,
                    'owner_id': owner_id,
                    'data': '',
                    'record_count': 0,
                    'state': 'draft'
                })

                # Check if the response is 200:
                if response.status_code == 200:
                    record_count = 0
                    # Get the response data:
                    data = response.json()
                    # Get the total count of products:
                    total_count = data['totalCount']
                    #Get the limit of data sent:
                    limit = data['limit']
                    for item in data['items']:
                        record_count = record_count + 1
                    # Create the product schedule:
                    self.env['cengine.scheduler.product.ept'].with_user(user=instance.default_user.id).create({
                                                                    'schedule_id': schedule.id,
                                                                    'instance_id': instance.id,
                                                                    'owner_id': owner_id,
                                                                    'source': 'manual',
                                                                    'data': response.text,
                                                                    'record_count': record_count if record_count > 0 else 0,
                                                                    'state': 'draft' if record_count > 0 else 'done',
                                                                    'remarks': 'created'
                                                                })

                    # Update the schedule record count:
                    schedule.with_user(user=instance.default_user.id).write({'record_count': record_count,
                                    'data': response.text,
                                    'state': 'draft' if record_count > 0 else 'done'
                                    })
                    
                    instance.with_user(user=instance.default_user.id).write({'last_product_import': time_now})

                else:
                    # Create the product schedule:
                    self.env['cengine.scheduler.product.ept'].with_user(user=instance.default_user.id).create({
                                                                    'schedule_id': schedule.id,
                                                                    'instance_id': instance.id,
                                                                    'owner_id': owner_id,
                                                                    'source': 'manual',
                                                                    'data': response.text,
                                                                    'record_count': 0,
                                                                    'state': 'failed',
                                                                    'remarks': 'API response failed'
                                                                })
                    # Update the schedule record count and state:
                    schedule.with_user(user=instance.default_user.id).write({'record_count': 0, 'state': 'failed'})
                    _logger.warning("Error while fetching products from Cengine for instance - %s", instance.name, exc_info=True)
                    _logger.warning(response.status_code)
                    _logger.warning(response.text)
                
                remaining_count = total_count - skip - limit
                skip = skip + limit

                self._cr.commit()

            instance.with_user(user=instance.default_user.id).write({'last_product_import': time_now})
        
        return True
                    
    @api.model
    def cengine_products_cron(self):
        self.cengine_products_scheduler()
        self.cengine_products_category()
        self.cengine_products_import()
        return True