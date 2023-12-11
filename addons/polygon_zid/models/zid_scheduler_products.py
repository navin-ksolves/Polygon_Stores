# -*- coding: utf-8 -*-
from odoo import models, fields
import logging, ast, requests
from . import common_functions
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ZidProductScheduler(models.Model):
    _name = 'zid.scheduler.products'
    _description = 'Zid Product Scheduler'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    status = fields.Selection([('draft', 'Draft'), ('progress', 'In Progess'), ('done', 'Done'), ('failed', 'Failed')],
                              string="Status", tracking=True, default='draft', readonly=True)
    data = fields.Text(string="Json Data", readonly=True)
    category = fields.Boolean('Category', readonly=True)
    product = fields.Boolean('Product Created', readonly=True)
    product_variant_list = fields.Boolean('Product Variant List', readonly=True)
    images = fields.Boolean('Images', readonly=True)
    scheduler_log_id = fields.Many2one('zid.scheduler.log.line', string="Scheduler Log", readonly=True)
    zid_product_id = fields.Many2one('zid.product.template', string='Product', readonly=True)
    attribute = fields.Boolean('Attribute', readonly=True)

    def create_zid_product_template(self):
        """
        Function to create record in zid product template if product template if not present
        :return:
        """
        _logger.info("Creating Zid Product Template!!")
        draft_records = self.search([('status', '=', 'draft')])
        product_objs = self.env['zid.product.template']

        for product in draft_records:
            try:
                product.status = 'progress'
                input_string = product['data']
                product_template = ast.literal_eval(input_string)

                # Creating product category
                product_category = self.execute_category_creation(product, product_template['categories'])
                if product_category:
                    product.category = True

                # Creating product(template) if product isn't a variant
                if not product_template['parent_id']:
                    vals = {
                        'name': product_template.get('name'),
                        'description': product_template.get('short_description'),
                        'owner_id': product.scheduler_log_id.instance_id.owner_id.id,
                        'zid_id': product_template.get('id'),
                        'zid_sku': product_template.get('sku'),
                        'html_url': product_template.get('html_url'),
                        'instance_id': product.scheduler_log_id.instance_id.id,
                        'zid_product_categ_id': product_category.id if product_category else False,
                        'has_variants': product_template.get('has_options'),
                        'requires_shipping': product_template.get('requies_shipping'),
                        'is_taxable': product_template.get('is_taxable'),
                        'structure': product_template.get('structure'),
                        'is_published': product_template.get('is_published')
                    }
                    zid_product_template = product_objs.create(vals)
                    if zid_product_template:
                        if len(product_template['attributes']):
                            self.create_variant_record(product_template)
                        product.product = True
                    else:
                        zid_product_template={}
                        product.product = False
                # Creating variants record in log
                if not product_template.get('parent_id'):
                    product_id = product_template['id']
                    product_variants = self.execute_product_variant_creation(product, product_id)
                    if product_variants:
                        product.product_variant_list = True
                else:
                    product.product_variant_list = True
                # creating zid.image data
                if len(product_template['images']):
                    images = self.execute_image_creation(product_template['images'], zid_product_template)
                    if images:
                        product.images = True
                else:
                    product.images = True

                if zid_product_template:
                    product.zid_product_id = zid_product_template.id
                    product.status = 'done'
                    product.scheduler_log_id.completed_lines += 1

                else:
                    product.status = 'failed'
                common_functions.update_scheduler_log_state(product.scheduler_log_id)

            except Exception as e:
                _logger.error(str(e))
                _logger.error("Product Creation Falied!!")
                return False

    def create_variant_record(self, product):
        """
        Helper function to link attributes and values of variants to the product template
        :param product: json data for product
        :return:
        """
        instance_id = product.scheduler_log_id.instance_id.id
        zid_product_template = self.env['zid.product.template'].search([('zid_id', '=', product['parent_id']),
                                                                        ('instance_id','=',instance_id)])
        if not zid_product_template:
            raise ValidationError('Product Template For Variant does not exist.')
        else:
            odoo_product_template = zid_product_template.product_template_id
            odoo_att_dict = {}
            for odoo_att_line in odoo_product_template['attribute_line_ids']:
                odoo_att_dict[odoo_att_line.attribute_id.id] = {'value_ids': odoo_att_line.value_ids.ids,
                                                                'line_id': odoo_att_line.id}
            for attribute in product['attributes']:
                zid_attribute = self.env['zid.product.attributes'].search([('name', '=', attribute['name'])], limit=1)

                if zid_attribute:
                    odoo_attribute = zid_attribute.product_attribute_id
                    # If attribute already present in template then check if value present, if value not present link with that line
                    if odoo_attribute.id in odoo_att_dict.keys():
                        attr = odoo_att_dict[odoo_attribute.id]
                        value_id = self.env['product.attribute.value'].search([('attribute_id', '=', odoo_attribute.id),
                                                                               ('name', '=', attribute['value']['en'])])
                        if value_id.id not in attr['value_ids']:
                            odoo_product_template.write({
                                'attribute_line_ids': [
                                    (1, attr['line_id'], {
                                        'value_ids': [(4, 0, value_id.id)]
                                    }),
                                ],
                            })
                    else:
                        # If attribute is not present in template then link it and it's values
                        value_id = self.env['product.attribute.value'].search([('attribute_id', '=', odoo_attribute.id),
                                                                               ('name', '=', attribute['value']['en'])])
                        odoo_product_template.write({
                            'attribute_line_ids': [
                                (0, 0, {
                                    'attribute_id': odoo_attribute.id,
                                    'value_ids': [(6, 0, [value_id.id])]
                                }),
                            ],
                        })

    def execute_image_creation(self, images, zid_product_template):
        """
        Helper function to create product images
        :param images:
        :return:
        """
        try:
            for image in images:
                data_for_image = {
                    'zid_id': image['id'],
                    'thumbnail_image_url': image['image']['thumbnail'],
                    'medium_image_url': image['image']['medium'],
                    'small_image_url': image['image']['small'],
                    'large_image_url': image['image']['large'],
                    'full_size_image_url': image['image']['full_size'],
                    'alt_text': image['alt_text'],
                    'display_order': image['display_order'],
                    'zid_product_id': zid_product_template.id
                }
                product_image = self.env['zid.product.image'].create(data_for_image)
                if product_image:
                    _logger.info("Product Image Created Successfully!!")
                    return product_image
        except Exception as e:
            _logger.error(str(e))
            _logger.error("Product Image Creation Falied!!")
            return False

    def execute_product_variant_creation(self, product, product_id):
        """
        Helper function to create log for variants in schedule.log
        :param variants: list of variants
        :return:
        """
        try:
            url = f"https://api.zid.sa/v1/products/{product_id}/"
            headers = common_functions.fetch_authentication_details(self, product.scheduler_log_id.instance_id.id)
            store_id = self.env['zid.tokens'].search(
                [('access_token', '=', product.scheduler_log_id.instance_id.access_token)]).zid_request_id.store_id
            headers['Access-Token'] = headers.pop('X-Manager-Token')
            headers['Store-Id'] = store_id
            headers['Role'] = 'Manager'

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                variants = response.json()['variants']
                for variant in variants:
                    data_for_log = {
                        'scheduler_type': 'product',
                        'instance_id': product.scheduler_log_id.instance_id.id,
                        'status': 'draft',
                        'attempts': 0,
                        'json': {'data': [variant]}
                    }
                    self.env['zid.scheduler.log.line'].create(data_for_log)
            return True
        except Exception as e:
            _logger.error(str(e))
            _logger.error("Product Variant Log Creation Falied!!")
            return False

    def execute_category_creation(self, product, categories):
        """
        Helper function to create catgory
        :param categories: list of categories
        :return:
        """
        try:
            category_objs = self.env['zid.product.category']
            for category in categories:
                vals = {
                    'name': category['name'],
                    'zid_category_id': category['id'],
                    # 'uuid': category['uuid'],
                    # 'Zid_product_category_url': category['url'],
                    # 'parent_category_id': category['parent_id'],
                    'owner_id': product.scheduler_log_id.instance_id.owner_id.id
                }

                zid_product_category = category_objs.create(vals)
                return zid_product_category
        except Exception as e:
            _logger.error(str(e))
            _logger.error("Product Category Creation Failed!!")
            return False
