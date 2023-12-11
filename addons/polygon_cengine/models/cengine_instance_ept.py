from odoo import models, fields, api
from odoo.exceptions import ValidationError

import logging
import uuid
import datetime
import pytz
import json
import requests

_logger = logging.getLogger("Conversion Engine Instance Ept")

class ConversionEngineInstanceEpt(models.Model):
    _name = 'cengine.instance.ept'
    _description = 'Conversion Engine Instance EPT'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, copy=False, tracking=True)
    polygon_instance_id = fields.Many2one('polygon.instance', string='Polygon Instance', required=True, copy=False, tracking=True)
    polygon_connector_id = fields.Many2one('polygon.connector.clients', string='Polygon Connector', required=False, copy=False, readonly=True, tracking=True)
    polygon_client_id = fields.Many2one('polygon.client.company', string='Polygon Client', required=False, copy=False, readonly=True, tracking=True)
    sales_team_id = fields.Many2one('crm.team', string='Sales Team', required=False, copy=False, readonly=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, copy=False, default=lambda self: self.env.company.id, tracking=True, readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Primary Warehouse', required=True, copy=False, 
                                   default=lambda self: self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1),
                                   tracking=True, readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', required=False, copy=False, readonly=True, tracking=True)
    access_token = fields.Char(string='Access Token', required=True, copy=False, tracking=True)
    secret_key = fields.Char(string='Secret Key', required=False, copy=False, readonly=True, tracking=True)
    host_name = fields.Char(string='Host Name', required=True, copy=False, tracking=True)
    last_customer_import = fields.Datetime(string='Last Customer Import', required=False, copy=False, readonly=True)
    last_product_import = fields.Datetime(string='Last Product Import', required=False, copy=False, readonly=True)
    last_order_import = fields.Datetime(string='Last Order Import', required=False, copy=False, readonly=True)
    last_product_export = fields.Datetime(string='Last Product Export', required=False, copy=False, readonly=True)
    import_orders_after_date = fields.Datetime(string='Date to begin order import', required=True, copy=False, default=fields.Datetime.now)
    notify_customer = fields.Boolean(string='Notify Customer', default=True, copy=False, tracking=True)
    default_user = fields.Many2one('res.users', string='Default User', required=False, copy=False, readonly=True, tracking=True)
    sync_with_images = fields.Boolean(string='Sync with Images', default=True, copy=False, tracking=True)
    webhook_ids = fields.One2many('cengine.webhook.ept', 'instance_id', string='Webhooks', copy=False, readonly=True, tracking=True)
    create_customer_webhook = fields.Boolean(string='Create Customer Webhook', default=False, copy=False, tracking=True)
    orders_today = fields.Integer(string='Orders Today', compute='order_count_for_day', store=True)
    orders_this_week = fields.Integer(string='Orders This Week', compute='order_count_for_week', store=True)
    orders_this_month = fields.Integer(string='Orders This Month', compute='order_count_for_month', store=True)
    orders_this_year = fields.Integer(string='Orders This Year', compute='order_count_for_year', store=True)
    orders_yesterday = fields.Integer(string='Orders Yesterday', compute='order_count_yesterday', store=True)
    orders_last_week = fields.Integer(string='Orders Last Week', compute='order_count_last_week', store=True)
    orders_last_month = fields.Integer(string='Orders Last Month', compute='order_count_last_month', store=True)
    orders_last_year = fields.Integer(string='Orders Last Year', compute='order_count_last_year', store=True)
    active = fields.Boolean(string='Active', default=True, copy=False)

    _sql_constraints = [('secret_key_unique_constraint', 'unique(secret_key)', 'Secret key must be unique.')]

    # On create generate a unique secret key
    @api.model
    def create(self, vals):

        # Host_name cannot end with forward slash:
        if vals['host_name'][-1] == '/':
            vals['host_name'] = vals['host_name'][:-1]

        vals['secret_key'] = str(uuid.uuid4())

        # Check if secret key already exists:
        while self.env['cengine.instance.ept'].search([('secret_key', '=', vals['secret_key'])]):
            vals['secret_key'] = str(uuid.uuid4())

        # Check if host already exists:
        if self.env['cengine.instance.ept'].search([('host_name', '=', vals['host_name'])]):
            _logger.error('Host name already exists.')
            raise ValidationError('Host name already exists.')
        
        polygon_instance = self.env['polygon.instance'].search([('id', '=', vals['polygon_instance_id'])])

        primary_user = self.env['polygon.client.users'].search([('client_id', '=', polygon_instance.connector_id.client_id.id), ('is_primary', '=', True)]).user_id

        vals['default_user'] = primary_user.id

        if vals['default_user'] == False:
            _logger.error('No primary user found for the client.')
            raise ValidationError('No primary user found for the client.')
        
        # Get the client_id from the polygon_instance_id:
        vals['polygon_client_id'] = polygon_instance.connector_id.client_id.id

        vals['polygon_connector_id'] = polygon_instance.connector_id.id

        if vals['polygon_client_id'] == False:
            _logger.error('No client found for the polygon instance.')
            raise ValidationError('No client found for the polygon instance.')
        
        vals['company_id'] = self.env.company.id
        
        # Get the sales team from the polygon_instance_id:
        vals['sales_team_id'] = primary_user.partner_id.team_id.id

        instance = super(ConversionEngineInstanceEpt, self).create(vals)

        # Create the product price list:
        pricelist_id = self.env['product.pricelist'].create({'name': vals['name'] + ' Pricelist',
                                                                'company_id': vals['company_id'],
                                                                'currency_id': self.env.company.currency_id.id,
                                                                'polygon_instance_id': polygon_instance.id,
                                                                'client_id': vals['polygon_client_id'],
                                                                'sales_team_id': vals['sales_team_id']
                                                                })
        
        vals['pricelist_id'] = pricelist_id.id

        vals['owner_id'] = polygon_instance.connector_id.client_id.partner_id.id
        
        # Create an All category in Cengine:
        product_category = self.env['cengine.product.category'].search([('name', '=', 'All'),
                                                                        ('owner_id', '=', vals['owner_id'])])
        
        if not product_category:
            product_category = self.env['cengine.product.category'].create({'name': 'All',
                                                                            'owner_id': vals['owner_id'],
                                                                            'parent_category_id': 0,
                                                                            'cengine_product_category_id': 1,
                                                                            'cengine_product_category_url': 'default'})
        
        # Check if default_shipping and default_discount products are created:
        default_shipping = self.env['product.template'].search([('name', '=', 'Default Shipping'),
                                                   ('company_id', '=', vals['company_id']),
                                                   ('product_owner', '=', vals['owner_id'])])

        if not default_shipping:    
            # Create default shipping product:
            product_template_id = self.env['cengine.product.template'].create({'name': 'Default Shipping',
                                                                            'description': 'Default Shipping',
                                                                            'cengine_product_template_type': 'service',
                                                                            'instance_id': instance.id,
                                                                            'default_shipping': True,
                                                                            'active': True,
                                                                            'owner_id': vals['owner_id'],
                                                                            'cengine_product_categ_id': product_category.id,
                                                                            'cengine_product_template_id': 'default_shipping',
                                                                            'default_shipping': True
                                                                            })
            
        _logger.info('Default shipping product created. Product ID: ' + str(product_template_id.id))

        default_discount = self.env['product.template'].search([('name', '=', 'Default Discount'),
                                                   ('company_id', '=', vals['company_id']),
                                                   ('product_owner', '=', vals['owner_id'])])
            
        if not default_discount:
            # Create default discount product:
            product_id = self.env['cengine.product.template'].create({'name': 'Default Discount',
                                                                        'description': 'Default Discount',
                                                                        'cengine_product_template_type': 'service',
                                                                        'instance_id': instance.id,
                                                                        'default_shipping': True,
                                                                        'active': True,
                                                                        'owner_id': vals['owner_id'],
                                                                        'cengine_product_categ_id': product_category.id,
                                                                        'cengine_product_template_id': 'default_discount',
                                                                        'default_discount': True
                                                                        })
        
        _logger.info('Default discount product created. Product ID: ' + str(product_id.id))

        return instance
    
    # Order count for the day:
    def order_count_for_day(self):
        
        datetime_now = datetime.datetime.now()
        
        # Make the time as 00:00:00:
        datetime_now = datetime_now.replace(hour=0, minute=0, second=0)

        # Make the datetime without any tz info:
        datetime_now = datetime_now.replace(tzinfo=None)

        return self.env['sale.order'].search_count([('instance_id', '=', self.polygon_instance_id.id), 
                                                    ('date_order', '>=', datetime_now),
                                                    ('state', 'in', ['sale', 'done'])])
    
    # Order count for the week:
    def order_count_for_week(self):

        datetime_now = datetime.datetime.now()
        
        # Make the time as 00:00:00:
        datetime_now = datetime_now.replace(hour=0, minute=0, second=0)

        # Make the datetime without any tz info:
        datetime_now = datetime_now.replace(tzinfo=None)

        # Date 7 days ago:
        datetime_7_days = datetime_now - datetime.timedelta(days=7)

        return self.env['sale.order'].search_count([('instance_id', '=', self.polygon_instance_id.id), 
                                                    ('date_order', '>=', datetime_7_days),
                                                    ('date_order', '<=', datetime_now.replace(hour=23, minute=59, second=59)),
                                                    ('state', 'in', ['sale', 'done'])])
    
    # Order count for the month:
    def order_count_for_month(self):

        datetime_now = datetime.datetime.now()
        
        # Make the time as 00:00:00:
        datetime_now = datetime_now.replace(hour=0, minute=0, second=0)

        # Make the datetime without any tz info:
        datetime_now = datetime_now.replace(tzinfo=None)

        # Date 30 days ago:
        datetime_30_days = datetime_now - datetime.timedelta(days=30)
        
        return self.env['sale.order'].search_count([('instance_id', '=', self.polygon_instance_id.id), 
                                                    ('date_order', '>=', datetime_30_days),
                                                    ('date_order', '<=', datetime_now.replace(hour=23, minute=59, second=59)),
                                                    ('state', 'in', ['sale', 'done'])])
    
    # Order count for the year:
    def order_count_for_year(self):

        datetime_now = datetime.datetime.now()
        
        # Make the time as 00:00:00:
        datetime_now = datetime_now.replace(hour=0, minute=0, second=0)

        # Make the datetime without any tz info:
        datetime_now = datetime_now.replace(tzinfo=None)

        # Date 65 days ago:
        datetime_1_year = datetime_now - datetime.timedelta(days=365)

        return self.env['sale.order'].search_count([('instance_id', '=', self.polygon_instance_id.id), 
                                                    ('date_order', '>=', datetime_1_year),
                                                    ('date_order', '<=', datetime_now.replace(hour=23, minute=59, second=59)),
                                                    ('state', 'in', ['sale', 'done'])])
    
    # Order count yesterday:
    def order_count_yesterday(self):

        datetime_now = datetime.datetime.now()
        
        # Make the time as 00:00:00:
        datetime_now = datetime_now.replace(hour=0, minute=0, second=0)

        # Make the datetime without any tz info:
        datetime_now = datetime_now.replace(tzinfo=None)

        # Date 1 day ago:
        datetime_now = datetime_now - datetime.timedelta(days=1)

        return self.env['sale.order'].search_count([('instance_id', '=', self.polygon_instance_id.id), 
                                                    ('date_order', '>=', datetime_now),
                                                    ('date_order', '<=', datetime_now.replace(hour=23, minute=59, second=59)),
                                                    ('state', 'in', ['sale', 'done'])])
    
    # Order count last week:
    def order_count_last_week(self):
        
        datetime_now = datetime.datetime.now()
        
        # Make the time as 00:00:00:
        datetime_now = datetime_now.replace(hour=0, minute=0, second=0)

        # Make the datetime without any tz info:
        datetime_now = datetime_now.replace(tzinfo=None)

        # Date 7 day ago:
        datetime_end = datetime_now - datetime.timedelta(days=8)

        # Date 14 day ago:
        datetime_start = datetime_now - datetime.timedelta(days=15)

        return self.env['sale.order'].search_count([('instance_id', '=', self.polygon_instance_id.id), 
                                                    ('date_order', '>=', datetime_start),
                                                    ('date_order', '<=', datetime_end.replace(hour=23, minute=59, second=59)),
                                                    ('state', 'in', ['sale', 'done'])])
    
    # Order count last month:
    def order_count_last_month(self):
        
        datetime_now = datetime.datetime.now()
        
        # Make the time as 00:00:00:
        datetime_now = datetime_now.replace(hour=0, minute=0, second=0)

        # Make the datetime without any tz info:
        datetime_now = datetime_now.replace(tzinfo=None)

        # Date 30 day ago:
        datetime_end = datetime_now - datetime.timedelta(days=31)

        # Date 60 day ago:
        datetime_start = datetime_now - datetime.timedelta(days=61)

        return self.env['sale.order'].search_count([('instance_id', '=', self.polygon_instance_id.id), 
                                                    ('date_order', '>=', datetime_start),
                                                    ('date_order', '<=', datetime_end.replace(hour=23, minute=59, second=59)),
                                                    ('state', 'in', ['sale', 'done'])])
    
    # Order count last year:
    def order_count_last_year(self):
        
        datetime_now = datetime.datetime.now()
        
        # Make the time as 00:00:00:
        datetime_now = datetime_now.replace(hour=0, minute=0, second=0)

        # Make the datetime without any tz info:
        datetime_now = datetime_now.replace(tzinfo=None)

        # Date 365 day ago:
        datetime_end = datetime_now - datetime.timedelta(days=366)

        # Date 730 day ago:
        datetime_start = datetime_now - datetime.timedelta(days=731)

        return self.env['sale.order'].search_count([('instance_id', '=', self.polygon_instance_id.id), 
                                                    ('date_order', '>=', datetime_start),
                                                    ('date_order', '<=', datetime_end.replace(hour=23, minute=59, second=59)),
                                                    ('state', 'in', ['sale', 'done'])])
    
    @api.model_create_multi
    def force_products_category(self, vals_list):

        for vals in vals_list:
            schedule = self.env['cengine.scheduler.product.ept'].search([('id', '=', vals['id'])])
            schedule.with_user(user=schedule.instance_id.default_user.id).write({'state': 'progress'})
            schedule.schedule_id.with_user(user=schedule.instance_id.default_user.id).write({'state': 'progress'})
            # Parse the JSON in the data field:
            _logger.info("Schedule data - %s", schedule.data)
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
                        return vals_list
                    else:
                        raise ValidationError("Error while creating product category")

    @api.model_create_multi
    def force_products_import(self, vals_list):

        for vals in vals_list:
            # Run for all draft product schedules:
            schedule = self.env['cengine.scheduler.product.ept'].search([('id', '=', vals['id'])])
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
                                                                            'attempts': schedule.attempts + 1})
                schedule.schedule_id.with_user(user=schedule.instance_id.default_user.id).write({'state': 'failed'})

    @api.model
    def cengine_auth(self, url, headers, payload, limit, skip):
        
        url = url + "limit=" + str(limit) + "&skip=" + str(skip)
        
        # Make the request:
        response = requests.request("GET", url, headers=headers, data=payload)

        return response
    
    @api.model
    def force_products_scheduler(self, record):

        # Run for current active instances in cengine:
        instance = self.env['cengine.instance.ept'].search([('id', 'in', record)], limit=1)

        schedules = []

        host_name = instance.host_name
        api_key = instance.access_token
        owner_id = instance.polygon_client_id.partner_id.id
        time_now = datetime.datetime.now()
        datetime_now = pytz.utc.localize(time_now).astimezone(pytz.timezone(instance.default_user.tz or
                                                                        'UTC')).strftime('%Y-%m-%dT%H:%M:%S%z')
        datetime_now = int(datetime.datetime.strptime(datetime_now, '%Y-%m-%dT%H:%M:%S%z').timestamp())
        
        # Check if the hostname has https/http:
        if 'http://' in host_name or 'https://' in host_name:
            url = host_name + '/api/site/products?'
        else:
            url = 'https://' + host_name + '/api/site/products?'

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
            response = self.cengine_auth(url, headers, payload, limit=limit, skip=skip)

            # Create the schedule:
            schedule = self.env['cengine.scheduler.ept'].with_user(user=instance.default_user.id).create({
                'schedule_type': 'product',
                'instance_id': instance.id,
                'owner_id': owner_id,
                'data': '',
                'record_count': 0,
                'state': 'draft'
            })

            _logger.info("Response - %s", response.text)

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
                product_schedule = self.env['cengine.scheduler.product.ept'].with_user(user=instance.default_user.id).create({
                                                                'schedule_id': schedule.id,
                                                                'instance_id': instance.id,
                                                                'owner_id': owner_id,
                                                                'source': 'manual',
                                                                'data': response.text,
                                                                'record_count': record_count if record_count > 0 else 0,
                                                                'state': 'draft' if record_count > 0 else 'done'
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
                                                                'state': 'failed'
                                                            })
                # Update the schedule record count and state:
                schedule.with_user(user=instance.default_user.id).write({'record_count': 0, 'state': 'failed'})
                _logger.warning("Error while fetching products from Cengine for instance - %s", instance.name, exc_info=True)
                _logger.warning(response.status_code)
                _logger.warning(response.text)
            
            remaining_count = total_count - skip - limit
            skip = skip + limit

            schedules.append(product_schedule)
            self.env.cr.commit()

        instance.with_user(user=instance.default_user.id).write({'last_order_import': time_now})
        
        return schedules
                    
    @api.model
    def cengine_products_force(self, record):
        schedules = self.force_products_scheduler(record)
        self.force_products_category(schedules)
        self.force_products_import(schedules)
        return True

# If the instance is not active then mark the cengine instance as inactive:
class PolygonInstance(models.Model):
    _inherit = 'polygon.instance'

    @api.onchange('active')
    def _onchange_active(self):
        for record in self:
            if record.active == False:
                self.env['cengine.instance.ept'].search([('polygon_instance_id', '=', record.id)]).active = False
