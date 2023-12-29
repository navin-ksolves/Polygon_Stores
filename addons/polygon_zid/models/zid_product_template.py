# -*- coding: utf-8 -*-
from odoo import models, fields, api
from . import common_functions
import requests
import logging
_logger = logging.getLogger(__name__)


class ZidProductTemplate(models.Model):
    _name = 'zid.product.template'
    _description = 'Zid Product Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    description = fields.Html(string='Description', tracking=True, translate=False)
    owner_id = fields.Many2one('res.partner', string='Owner', required=True, tracking=True,
                               domain="[('is_company', '=', True)]")
    zid_id = fields.Char('Zid Id')
    zid_sku = fields.Char('Sku')
    html_url = fields.Text('Url')
    instance_id = fields.Many2one('zid.instance.ept', string='Instance', required=True, tracking=True)
    zid_product_categ_id = fields.Many2one('zid.product.category', string='Product Category', required=False,
                                           tracking=True)
    has_variants = fields.Boolean(string='Has Variants', default=False, tracking=True)
    requires_shipping = fields.Boolean(string='Requires Shipping',default=False, tracking=True)
    is_taxable = fields.Boolean(string='Is Taxable', default=False)
    structure = fields.Char('Structure')
    is_published = fields.Boolean('Published')
    product_template_id = fields.Many2one('product.template', string='Product Id- Base Variant',
                                          required=True, tracking=True)
    primary_product_id = fields.Many2one('product.product', string='Product ID - Base Variant',
                                 required=True, tracking=True)
    default_shipping = fields.Boolean(string='Default Shipping Product', default=False, tracking=True)
    default_discount = fields.Boolean(string='Default Discount Product', default=False, tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)

    product_image = fields.Image("Image", related='primary_product_id.image_1920', compute_sudo=True)
    zid_stock_id = fields.Char('Zid Stock Id')
    @api.model
    def create(self, vals):
        """
        Overrided this function to prevent duplication
        :param vals:
        :return:
        """
        _logger.info("Creating Zid Product Template")
        _logger.info(vals)
        if isinstance(vals['name'], dict):
            vals['name'] = vals['name']['en'] + " - " + str(vals['zid_id'])
        # Check if product template exists:
        product_template = self.search([('instance_id', '=', vals['instance_id']),
                                        ('zid_id', '=',vals['zid_id'])])
        if product_template:
            product_template.write({'name': vals['name'],
                                    'description': vals['description'],
                                    'owner_id': vals['owner_id']})

            product_template.product_template_id.write({'name': vals['name'],'description': vals['description'],
                                                               'product_owner': vals['owner_id']})

            return product_template

        # Create odoo product template:
        if vals['requires_shipping']:
            product_type = 'product'
        else:
            product_type = 'service'

        product_template_obj = self.env['product.template']

        # Check if product_template and owner combination exists:
        product_template = product_template_obj.search([('name', '=', vals['name']),
                                                                ('product_owner', '=', vals['owner_id'])], limit=1)
        if product_template:
            if vals.get('quantity'):
                del vals['quantity']

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
                                    'tracking': 'lot',
                                    # 'use_expiration_date': True,
                                    # 'expiration_time': 0,
                                    # 'use_time': 7,
                                    # 'removal_time': 7,
                                    # 'alert_time': 14,
                                    # 'categ_id': cengine_product_categ_id.category_id.id
                                    })

            _logger.info("Product template and owner combination already exists. Values updated.")

        else:
            product_template = product_template_obj.create({'name': vals['name'],
                                                                    'description': vals['description'],
                                                                    'type': product_type,
                                                                    'product_owner': vals['owner_id'],
                                                                    'is_online_product': True,
                                                                    'sale_ok': True,
                                                                    'purchase_ok': True,
                                                                    'invoice_policy': 'delivery',
                                                                    'list_price': 0.0,
                                                                    'tracking': 'lot',
                                                                    # 'use_expiration_date': True,
                                                                    # 'expiration_time': 0,
                                                                    # 'use_time': 7,
                                                                    # 'removal_time': 7,
                                                                    # 'alert_time': 14,
                                                                    # 'categ_id': cengine_product_categ_id.category_id.id #TODO: create category for product
                                                                    })

            product_id = self.env['product.product'].search([('product_tmpl_id', '=', product_template.id)], limit=1)
            if product_id and vals.get('quantity'):
                stock_id = self.env['stock.location'].browse(8)
                self.env['stock.quant']._update_available_quantity(product_id, stock_id, vals[
                    'quantity'])  # TODO: ask where quantity to be updated
                del vals['quantity']
        product_id = self.env['product.product'].search([('product_tmpl_id', '=', product_template.id)], limit=1)
        vals['primary_product_id'] = product_id.id
        vals['product_template_id'] = product_template.id

        product_template = super(ZidProductTemplate, self).create(vals)

        return product_template

    # def create_zid_product_template_sync_logs(self):
    #     """
    #     function to create sync log for product in scheduler.log for each instance
    #     :return:
    #     """
    #     _logger.info("Creating Sync Logs For Products!!")
    #     instances = self.env['zid.instance.ept'].search([])
    #     for instance in instances:
    #         url = "https://api.zid.sa/v1/products/"
    #         headers = common_functions.fetch_authentication_details(self, instance.id)
    #         store_id = self.env['zid.tokens'].search([('access_token', '=', instance.access_token)]).zid_request_id.store_id
    #         headers['Access-Token'] = headers.pop('X-Manager-Token')
    #         headers['Store-Id'] = store_id
    #         response = requests.get(url, headers=headers)
    #         if response.status_code == 200:
    #             json_data = {'data': response.json()}
    #             common_functions.create_log_in_scheduler(self, instance, create_log_for=['product'],
    #                                                      json_data=json_data)
