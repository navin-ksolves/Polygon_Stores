from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools import image_to_base64

import logging
import base64
import requests

_logger = logging.getLogger("Conversion Engine Product Template")

class CengineProductTemplate(models.Model):
    _name = 'cengine.product.template'
    _description = 'Conversion Engine Product Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    description = fields.Text(string='Description', tracking=True)
    owner_id = fields.Many2one('res.partner', string='Owner', required=True, tracking=True, domain="[('is_company', '=', True)]")
    instance_id = fields.Many2one('cengine.instance.ept', string='Instance', required=True, tracking=True)
    cengine_product_categ_id = fields.Many2one('cengine.product.category', string='Conversion Engine Product Category', required=True, tracking=True)
    cengine_product_template_id = fields.Char(string='Conversion Engine Product Template ID', required=True, tracking=True)
    product_id = fields.Many2one('product.product', string='Product ID - Base Variant', required=True, tracking=True)
    cengine_product_template_url = fields.Char(string='Conversion Engine Product Template URL', required=False, tracking=True)
    cengine_product_template_type = fields.Char(string='Conversion Engine Product Template Type', required=False, tracking=True)
    cengine_product_template_status = fields.Char(string='Conversion Engine Product Template Status', required=False, tracking=True)
    has_variants = fields.Boolean(string='Has Variants', required=False, default=False, tracking=True)
    default_shipping = fields.Boolean(string='Default Shipping Product', required=False, default=False, tracking=True)
    default_discount = fields.Boolean(string='Default Discount Product', required=False, default=False, tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)

    @api.model
    def create(self, vals):
        _logger.info("Creating Conversion Engine Product Template")
        _logger.info(vals)
        vals['name'] = vals['name'] + " - " + str(vals['cengine_product_template_id'])
        # Check if product template exists:
        product_template = self.env['cengine.product.template'].search([('owner_id', '=', vals['owner_id']),
                                                                        ('cengine_product_template_id', '=', vals['cengine_product_template_id'] )])
        if product_template:
            product_template.write({'name': vals['name'],
                                    'description': vals['description'],
                                    'owner_id': vals['owner_id']})
            
            product_template.product_id.product_tmpl_id.write({'name': vals['name'],
                                                                'description': vals['description'],
                                                                'product_owner': vals['owner_id']})
            
            return product_template
        
        cengine_product_categ_id = self.env['cengine.product.category'].search([('id', '=', vals['cengine_product_categ_id'])])

        _logger.info(cengine_product_categ_id, exc_info=True, stack_info=True)
        
        # Create odoo product template:
        if vals['cengine_product_template_type'] == 'physical':
            product_type = 'product'
        else:
            product_type = 'service'

        # Check if product_template and owner combination exists:
        product_template = self.env['product.template'].search([('name', '=', vals['name']),
                                                ('product_owner', '=', vals['owner_id'])], limit=1)

        if product_template:

            # Update values in the product template:
            product_template.write({'name': vals['name'],
                                    'description': vals['description'],
                                    'type': product_type,
                                    'product_owner': vals['owner_id'],
                                    'is_online_product': True,
                                    'sale_ok': True,
                                    'purchase_ok': True,
                                    'invoice_policy': 'delivery',
                                    'list_price': 0.0,
                                    'product_owner': vals['owner_id'],
                                    'tracking': 'lot',
                                    'use_expiration_date': True,
                                    'expiration_time': 0,
                                    'use_time': 7,
                                    'removal_time': 7,
                                    'alert_time': 14,
                                    'categ_id': cengine_product_categ_id.category_id.id
                                    })
            
            _logger.info("Product template and owner combination already exists. Values updated.")

        else:
            product_template = self.env['product.template'].create({'name': vals['name'],
                                                                'description': vals['description'],
                                                                'type': product_type,
                                                                'product_owner': vals['owner_id'],
                                                                'is_online_product': True,
                                                                'sale_ok': True,
                                                                'purchase_ok': True,
                                                                'invoice_policy': 'delivery',
                                                                'list_price': 0.0,
                                                                'product_owner': vals['owner_id'],
                                                                'tracking': 'lot',
                                                                'use_expiration_date': True,
                                                                'expiration_time': 0,
                                                                'use_time': 7,
                                                                'removal_time': 7,
                                                                'alert_time': 14,
                                                                'categ_id': cengine_product_categ_id.category_id.id
                                                                })
            
        product_id = self.env['product.product'].search([('product_tmpl_id', '=', product_template.id)], limit=1)
        
        vals['product_id'] = product_id.id

        product_template = super(CengineProductTemplate, self).create(vals)

        return product_template
    
    def create_defaults_first(self, vals):
        return super(CengineProductTemplate, self).create_defaults(vals)
    
class CengineProductTemplateImage(models.Model):
    _name = 'cengine.product.template.image'
    _description = 'Conversion Engine Product Template Image'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    url = fields.Char(string='URL', required=True, tracking=True)
    cengine_product_template_id = fields.Many2one('cengine.product.template', string='Conversion Engine Product Template', required=True, tracking=True)
    common_image_ept_id = fields.Many2one('common.product.image.ept', string='Common Product Image', required=True, tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        # Create image data from URL
        _logger.info("Creating Conversion Engine Product Template Image")
        for vals in vals_list:
            # Extract the values for the create method
            image = vals.get('images', [])
            cengine_product_template_id = vals.get('cengine_product_template_id')
            # Check if image_url already exists with owner combination:
            image_data = self.env['cengine.product.template.image'].search([('url', '=', image), 
                                                                ('cengine_product_template_id', '=', cengine_product_template_id)])
            
            if image_data:
                _logger.info('Image URL already exists with owner combination.')
                return image_data
            else:
                product_template = self.env['cengine.product.template'].search([('id', '=', cengine_product_template_id)])
                # Get the file name from the url "https://content.app-sources.com/s/59296987493503125/uploads/Images/intense-body-product01-3999810.jpg"
                file_name = image.split('/')[-1]
                # Create product images in odoo product template:
                image_id = self.env['common.product.image.ept'].create({'name': file_name,
                                                'url': image,
                                                'template_id': product_template.product_id.product_tmpl_id.id})
                
                image_id = self.env['common.product.image.ept'].create({'name': file_name,
                                                'url': image,
                                                'template_id': product_template.product_id.product_tmpl_id.id})
                
                common_image_ept_id = image_id.id

                product_image = super(CengineProductTemplateImage, self).create({'url': image,
                                                                                'cengine_product_template_id': cengine_product_template_id,
                                                                                'common_image_ept_id': common_image_ept_id})

            return product_image
        
    @api.model_create_multi
    def realign_images(self, vals_list):

        count = 0
        for vals in vals_list:
            if count == 0:
                # Extract the values for the create method
                image = vals.get('images', [])
                cengine_product_template_id = vals.get('cengine_product_template_id')

                if image:
                    product_template = self.env['cengine.product.template'].search([('id', '=', cengine_product_template_id)])
                    
                    response = requests.get(image)
                    if response.status_code == 200:
                        image_data = response.content
                        image_data_base64 = base64.encodebytes(image_data)
                        # _logger.info("Encoded Image Data:", image_data_base64)
                        if image_data_base64:
                            product_template.product_id.product_tmpl_id.image_1920 = image_data_base64
                            count = 1

        _logger.info("Realigning Conversion Engine Product Template Image")

        return True
    
class CengineProductCategory(models.Model):
    _name = 'cengine.product.category'
    _description = 'Conversion Engine Product Category'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    cengine_product_category_id = fields.Integer(string='Conversion Engine Product Category ID', required=True, tracking=True)
    cengine_product_category_url = fields.Char(string='Conversion Engine Product Category URL', required=True, tracking=True)
    parent_category_id = fields.Char(string='Parent Category',required=False, tracking=True, default=0)
    category_id = fields.Many2one('product.category', string='Category', required=True, tracking=True)
    owner_id = fields.Many2one('res.partner', string='Owner', required=True, tracking=True, domain="[('is_company', '=', True)]")
    active = fields.Boolean(string='Active', default=True, tracking=True)

    @api.model
    def create(self, vals):
        _logger.info("Creating Conversion Engine Product Category")
        # Check if parent category exists:
        if vals['parent_category_id'] != 0:
            if not self.env['cengine.product.category'].search([('cengine_product_category_id', '=', vals['parent_category_id'])]):
                raise ValidationError('Parent category does not exist.')
        # Check if category and owner combination exists:
        product_category = self.env['cengine.product.category'].search([('name', '=', vals['name']),
                                                        ('owner_id', '=', vals['owner_id'])])
        if product_category:
            product_category.write({'name': vals['name'],
                                    'owner_id': vals['owner_id'],
                                    'parent_category_id': vals['parent_category_id']})
            return product_category
        
        # Create odoo product category:
        # Check if category exists:
        category = self.env['product.category'].search([('name', '=', vals['name']),
                                                ('product_category_owner', '=', vals['owner_id']),
                                                ('is_online_product_category', '=', True)])
        parent_category = category.parent_id.id

        if category:
            vals['category_id'] = category.id
        else:
            category = self.env['product.category'].create({'name': vals['name'],
                                                            'product_category_owner': vals['owner_id'],
                                                            'is_online_product_category': True,
                                                            'parent_id': parent_category})
            vals['category_id'] = category.id
        
        product_category = super(CengineProductCategory, self).create(vals)
        _logger.info('Product Category created - %s', product_category)

        return product_category

class CengineProductOptions(models.Model):
    _name = 'cengine.product.options'
    _description = 'Conversion Engine Product Options'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    advanced = fields.Boolean(string='Advanced', required=True, tracking=True)
    product_attribute = fields.Many2one('product.attribute', string='Product Attribute', required=False, tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)

    @api.model
    def create(self, vals):
        _logger.info("Creating Conversion Engine Product Options")
        
        # Check if product.attribute exists and associate with it:
        product_attribute = self.env['product.attribute'].search([('name', '=', vals['name'])])
        if not product_attribute:
            # Create product.attribute:
            product_attribute = self.env['product.attribute'].create({'name': vals['name'],
                                                                      'create_variant': 'always',
                                                                      'display_type': 'select'})
        vals['product_attribute'] = product_attribute.id

        _logger.info(vals)
        # Check if option and owner combination exists:
        product_option = self.env['cengine.product.options'].search([('name', '=', vals['name'])], limit=1)
        if not product_option:
            product_option = super(CengineProductOptions, self).create(vals)

        _logger.info(product_option)

        return product_option

class CengineProductOptionValues(models.Model):
    _name = 'cengine.product.option.values'
    _description = 'Conversion Engine Product Option Values'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Value Name', required=True, tracking=True)
    cengine_product_options_id = fields.Many2one('cengine.product.options', string='Conversion Engine Product Options', required=True, tracking=True)
    product_attribute_value = fields.Many2one('product.attribute.value', string='Product Attribute Value', required=False, tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)

    @api.model
    def create(self, vals):
        _logger.info("Creating Conversion Engine Product Option Values")
        # Check if option value and option combination exists:
        product_option_value = self.env['cengine.product.option.values'].search([('name', '=', vals['name']), 
                                                              ('cengine_product_options_id', '=', vals['cengine_product_options_id'])])
        if product_option_value:
            return product_option_value
        
        product_option = self.env['cengine.product.options'].search([('id', '=', vals['cengine_product_options_id'])])
            
        product_attribute_value = self.env['product.attribute.value'].create({'name': vals['name'],
                                                                                  'attribute_id': product_option.product_attribute.id})

        vals['product_attribute_value'] = product_attribute_value.id
        
        _logger.info(vals)
        product_option_value = super(CengineProductOptionValues, self).create(vals)

        return product_option_value

class CengineProductVariants(models.Model):
    _name = 'cengine.product.variants'
    _description = 'Conversion Engine Product Variants'
    
    sku = fields.Char(string='SKU', required=True, tracking=True)
    price = fields.Float(string='Price', required=True, tracking=True)
    sale_price = fields.Float(string='Sale Price', required=False, tracking=True)
    on_sale = fields.Boolean(string='On Sale', required=False, tracking=True)
    quantity = fields.Integer(string='Quantity', required=False, tracking=True)
    weight = fields.Float(string='Weight', required=False, tracking=True)
    cengine_product_template_id = fields.Many2one('cengine.product.template', string='Conversion Engine Product Template', required=True, tracking=True)
    combination_indices_internal = fields.Char(string='Combination Indices Internal', required=False, tracking=True, index=True)
    combination_indices_external = fields.Char(string='Combination Indices External', required=False, tracking=True, index=True)
    product_variant_id = fields.Many2one('product.product', string='Product Variant', required=False, tracking=True, index=True)
    owner_id = fields.Many2one('res.partner', string='Owner', required=True, tracking=True, domain="[('is_company', '=', True)]")
    active = fields.Boolean(string='Active', default=True, tracking=True)

    @api.model
    def create(self, vals):
        _logger.info("Creating Conversion Engine Product Variants")

        product_template = self.env['cengine.product.template'].search([('id', '=', vals['cengine_product_template_id']),
                                                                        ('owner_id', '=', vals['owner_id'])])
        product_template_id = product_template.product_id.product_tmpl_id
        
        if vals['options'] != None:
            combination_indices_external = []
            combination_indices_internal = []
            for option in vals['options']:
                option_value_id = self.env['cengine.product.option.values'].search([('name', '=', option)])
                attribute_value_id = option_value_id.product_attribute_value.id
                attribute_id = option_value_id.cengine_product_options_id.product_attribute.id

                product_template_attribute_line_id = self.env['product.template.attribute.value'].search([('product_tmpl_id', '=', product_template_id.id),
                                                                        ('attribute_id', '=', attribute_id),
                                                                        ('product_attribute_value_id', '=', attribute_value_id)])

                combination_indices_external.append(product_template_attribute_line_id.id)
                combination_indices_internal.append(option_value_id.id)

            # Convert list to string:
            combination_indices_external = ','.join(map(str, combination_indices_external))
            combination_indices_internal = ','.join(map(str, combination_indices_internal))

            cengine_variant = self.env['cengine.product.variants'].search([('cengine_product_template_id', '=', vals['cengine_product_template_id']),
                                                                            ('combination_indices_external', '=', combination_indices_external),
                                                                            ('combination_indices_internal', '=', combination_indices_internal)])
            
            if cengine_variant:
                _logger.info("Cengine Variant - %s", cengine_variant)
                cengine_variant.write({'sku': vals['sku'],
                                        'price': vals['price'] if vals['price']>0 else 0.0,
                                        'sale_price': vals['sale_price'] if vals['price']>0 else 0.0,
                                        'on_sale': vals['sale_price'],
                                        'quantity': vals['quantity'] if vals['price']>0 else 0.0,
                                        'weight': vals['weight'] if vals['price']>0 else 0.0})
                product_template.write({'has_variants': True})
                variant_id = cengine_variant.id           
            
            else:
                for option in vals['options']:
                    option_value_id = self.env['cengine.product.option.values'].search([('name', '=', option)])
                    attribute_value_id = option_value_id.product_attribute_value.id
                    vals['option_name'] = option_value_id.cengine_product_options_id.name
                    vals['option_value'] = option_value_id.name
                    attribute_id = option_value_id.cengine_product_options_id.product_attribute.id
                                
                    _logger.info("Product Template - %s",product_template_id)

                    attribute_line_check = self.env['product.template.attribute.line'].search([('product_tmpl_id', '=', product_template_id.id),
                                                                            ('attribute_id', '=', attribute_id)])

                    # Check if option_id and option_value_id combination exists:
                    variant_check = self.env['product.template.attribute.value'].search([('product_tmpl_id', '=', product_template_id.id),
                                                                            ('product_attribute_value_id', '=', attribute_value_id),
                                                                            ('attribute_id', '=', attribute_id)])
                    
                    product_variant = self.env['product.product'].search([('product_tmpl_id', '=', product_template.id),
                                                                                ('product_template_attribute_value_ids', '=', attribute_value_id),
                                                                                ('attribute_line_ids', '=', attribute_id)])
                    
                    options_vals = {option,
                                    vals['option_name'],
                                    vals['option_value'],
                                    product_template_id.id,
                                    attribute_id,
                                    attribute_value_id}
                    
                    _logger.info("Options Vals - %s", options_vals)

                    if not product_variant:
                        if not attribute_line_check:
                            # Create product.template.attribute.line:
                            product_template_id.write({'attribute_line_ids': [(0, 0, {'attribute_id': attribute_id,
                                                                                    'value_ids': [(4, attribute_value_id)]})]})
                            _logger.info("Attribute Line Check - %s", attribute_line_check)
                            
                        else:
                            if not variant_check:
                                # Create product.template.attribute.line:
                                attribute_line_check.write({'value_ids': [(4, attribute_value_id)]})

                self._cr.commit()

                combination_indices_external = []
                combination_indices_internal = []
                for option in vals['options']:
                    option_value_id = self.env['cengine.product.option.values'].search([('name', '=', option)])
                    attribute_value_id = option_value_id.product_attribute_value.id
                    attribute_id = option_value_id.cengine_product_options_id.product_attribute.id

                    product_template_attribute_line_id = self.env['product.template.attribute.value'].search([('product_tmpl_id', '=', product_template_id.id),
                                                                            ('attribute_id', '=', attribute_id),
                                                                            ('product_attribute_value_id', '=', attribute_value_id)])

                    combination_indices_external.append(product_template_attribute_line_id.id)
                    combination_indices_internal.append(option_value_id.id)

                # Convert list to string:
                combination_indices_external = ','.join(map(str, combination_indices_external))
                combination_indices_internal = ','.join(map(str, combination_indices_internal))

                product_variant_id = self.env['product.product'].search([('product_tmpl_id', '=', product_template_id.id),
                                                                        ('combination_indices', '=', combination_indices_external)])
                
                existing_variant = self.env['cengine.product.variants'].search([('product_variant_id', '=', product_variant_id.id)])
                
                if not existing_variant:
                    upload_vals = {
                        'sku': vals['sku'],
                        'price': vals['price'] if vals['price']>0 else 0.0,
                        'sale_price': vals['sale_price'] if vals['price']>0 else 0.0,
                        'on_sale': vals['sale_price'],
                        'quantity': vals['quantity'] if vals['price']>0 else 0.0,
                        'weight': vals['weight'] if vals['price']>0 else 0.0,
                        'cengine_product_template_id': vals['cengine_product_template_id'],
                        'combination_indices_external': combination_indices_external,
                        'combination_indices_internal': combination_indices_internal,
                        'product_variant_id': product_variant_id.id,
                        'owner_id': vals['owner_id']
                    }

                    variant_id = super(CengineProductVariants, self).create(upload_vals)

                    product_template.write({'has_variants': True})
                    
                    _logger.info(variant_id)

                    return variant_id
                
                else:
                    existing_variant.write({'sku': vals['sku'],
                                            'price': vals['price'] if vals['price']>0 else 0.0,
                                            'sale_price': vals['sale_price'] if vals['price']>0 else 0.0,
                                            'on_sale': vals['sale_price'],
                                            'quantity': vals['quantity'] if vals['price']>0 else 0.0,
                                            'weight': vals['weight'] if vals['price']>0 else 0.0,
                                            'cengine_product_template_id': vals['cengine_product_template_id'],
                                            'combination_indices_external': combination_indices_external,
                                            'combination_indices_internal': combination_indices_internal})
                    return existing_variant