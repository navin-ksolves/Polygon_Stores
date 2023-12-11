# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ZidProductAttributesValues(models.Model):
    _name = 'zid.product.attributes.values'
    _description = 'Zid Product Attributes Values'
    _rec_name = 'value'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    value = fields.Char(string='Value', required=True, tracking=True)
    zid_attribute_id = fields.Char(string="Attribute Value Id")
    product_attribute_value = fields.Many2one('product.attribute.value', string='Product Attribute Value',
                                              required=False, tracking=False)

    @api.model
    def create(self, vals):
        product_option_value = self.search([('value', '=', vals['value']),
                                            ('zid_attribute_id', '=', vals['zid_attribute_id'])])
        if product_option_value:
            return product_option_value

        product_option = self.env['zid.product.attributes'].search(
            [('zid_attribute_id', '=', vals['zid_attribute_id'])])
        product_attr_value_obj = self.env['product.attribute.value']
        product_attribute_value = product_attr_value_obj.search(
            [('name', '=', vals['value']), ('attribute_id', '=', product_option.product_attribute_id.id)])
        if not product_attribute_value:
            product_attribute_value = product_attr_value_obj.create({'name': vals['value'],
                                                                     'attribute_id': product_option.product_attribute_id.id})

        vals['product_attribute_value'] = product_attribute_value.id

        product_option_value = super(ZidProductAttributesValues, self).create(vals)

        return product_option_value
