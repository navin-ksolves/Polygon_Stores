# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)


class ZidProductVariants(models.Model):
    _name = 'zid.product.variants'
    _description = 'Zid Product Variants'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    name = fields.Char('Name')
    description = fields.Html(string='Description', tracking=True, translate=False)
    owner_id = fields.Many2one('res.partner', string='Owner', required=True, tracking=True, domain="[('is_company', '=', True)]")
    zid_instance_id	= fields.Many2one('zid.instance', string='Instance', required=True, tracking=True)
    zid_id = fields.Char('Zid Id')
    zid_sku = fields.Char(string='Zid SKU', required=True, tracking=True)
    zid_category_id = fields.Many2one('zid.product.category', string='Category')
    zid_parent_id = fields.Char('Zid Parent Id')
    zid_product_template_id = fields.Many2one('zid.product.template', string='Zid Product Template',
                                              required=True, tracking=True)
    zid_attribute_id = fields.Char('Attribute Id')
    options = fields.Char('Options')
    html_url = fields.Text('Html Url')
    requires_shipping = fields.Boolean(string='Requires Shipping',default=False, tracking=True)
    is_taxable = fields.Boolean(string='Is Taxable', default=False)
    structure = fields.Char('Structure')
    is_published = fields.Boolean('Published')
    product_variant_id = fields.Many2one('product.product', string='Product ID - Base Variant', required=False, tracking=True,
                                         index=True)
    product_template_id = fields.Many2one('product.template', string='Product Template')

    price = fields.Float(string='Price', required=True, tracking=True)
    sale_price = fields.Float(string='Sale Price', required=False, tracking=True)
    on_sale = fields.Boolean(string='On Sale', required=False, tracking=True)
    quantity = fields.Integer(string='Quantity', required=False, tracking=True)
    weight = fields.Float(string='Weight', required=False, tracking=True)
    unit = fields.Char('Unit')
    product_image = fields.Image("Image", related='product_template_id.image_1920', compute_sudo=True)

    active = fields.Boolean(string='Active', default=True, tracking=True)
    zid_stock_id = fields.Char('Zid Stock Id')
    @api.model
    def create(self, vals):
        """
        Overrided this function to prevent duplication
        :param vals:
        :return:
        """
        _logger.info("Creating Zid Product Variant")
        _logger.info(vals)
        # vals['name'] = vals['name'] + " - " + str(vals['zid_id'])

        product_variant = self.search([('zid_instance_id', '=', vals['zid_instance_id']),
                                       ('zid_id', '=', vals['zid_id'])])
        if product_variant:
            product_variant.write({'name': vals['name'],
                                   'description': vals['description'],
                                   'owner_id': vals['owner_id']})

            product_variant.product_template_id.write({'description': vals['description'],
                                                       'product_owner': vals['owner_id']})

            product_variant.product_variant_id.write({'description': vals['description'],
                                                      'product_owner': vals['owner_id']})

            return product_variant
        else:
            odoo_product_variant = self.search_correct_odoo_variant(vals)
            if odoo_product_variant and  'quantity' in vals.keys():
                stock_id = self.env['stock.location'].browse(8)
                self.env['stock.quant']._update_available_quantity(odoo_product_variant, stock_id, vals[
                    'quantity'])  #TODO: make warehose dynamic

            if not odoo_product_variant:
                raise ValidationError("Suitable Variant Combination For Product Doesn't Exists!!")
            else:
                #If variant with same combination is found then just write details in it
                del vals['attributes']
                if vals['requires_shipping']:
                    product_type = 'product'
                else:
                    product_type = 'service'

                # remove description if it's an empty dictionary
                if not isinstance(vals['description'], dict):
                    description = vals['description']
                else:
                    description = False
                    del vals['description']
                odoo_product_variant.write({
                    'detailed_type': product_type,
                    # 'name' : 'Zid '+ vals['name'],
                    'company_id': self.env.user.company_id.id,
                    'currency_id': self.env.user.company_id.currency_id.id,
                    'sale_ok': True,
                    'purchase_ok': False,
                    'invoice_policy': 'order',
                    'product_variant_owner': vals['owner_id'],
                    'description': description,
                    'standard_price': vals['sale_price'] or vals['price'],
                })
                zid_product_template = self.env['zid.product.template'].search(
                    [('zid_id', '=', vals['zid_parent_id']),
                     ('instance_id', '=', vals['zid_instance_id'])])
                vals['zid_product_template_id'] = zid_product_template.id
                vals['product_variant_id'] = odoo_product_variant.id
                vals['product_template_id'] = odoo_product_variant.product_tmpl_id.id
        return super(ZidProductVariants,self).create(vals)

    def search_correct_odoo_variant(self, values):
        """
        Helper function which takes the values and finds the odoo variant that
        matches with zid variant
        :param values: value dictionary
        :return: record of product_product that matches the zid varinat
        """
        zid_product_template = self.env['zid.product.template'].search([('zid_id','=', values['zid_parent_id']),
                                                                        ('instance_id','=',values['zid_instance_id'])])
        if zid_product_template:
            odoo_product_template = zid_product_template.product_template_id
            odoo_att_dict = {}
            for odoo_att_line in odoo_product_template['attribute_line_ids']:
                odoo_att_dict[odoo_att_line.attribute_id.name] = {
                    value.name: value.id for value in odoo_att_line.product_template_value_ids
                }
            combination_dict = {}
            for attribute in odoo_att_dict.keys():
                present = list(filter(lambda attr: attr['name'] == attribute, values['attributes']))
                if len(present):
                    present = present[0]
                    combination_dict[attribute] = present['value']['en']
                else:
                    combination_dict[attribute] = 'None'
            if len(combination_dict):
                combination = ''
                for att,val in combination_dict.items():
                    combination += f"{odoo_att_dict[att][val]},"
                combination_indice = combination.rstrip(',')
                odoo_product_variant = list(filter(lambda variants: variants['combination_indices'] == combination_indice, odoo_product_template.product_variant_ids))
                if len(odoo_product_variant):
                    return odoo_product_variant[0]
                else:
                    raise ValidationError(f"Product Variant With Combination Indice {combination_indice} Does Not Exists!! ")
            else:
                raise ValidationError("Parent Product Does Not Exist!!")


