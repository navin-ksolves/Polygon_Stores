from odoo import models, fields, api
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger("Polygon Client Products")

class PolygonClientProducts(models.Model):
    _name = 'polygon.client.products'
    _description = 'Polygon Contracts Products'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Product Name', required=True, copy=False, index=True)
    product_type = fields.Selection([
                                        ('fulfillment', 'Fulfillment Service'),
                                        ('logistics', 'Logistics Service')
                                    ], string='Product Type', default='logistics')
    odoo_product_id = fields.Many2one('product.product', string='Odoo Product', readonly=True, copy=False)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, copy=False, required=True, default=lambda self: self.env.company.currency_id.id)

    @api.model
    def create(self, vals):

        # Check if the product name already exists
        product = self.env['polygon.client.products'].search([('name', '=', vals['name'])])

        if product:
            raise ValidationError("Product Name already exists!")
        
        else:
            # Get current company_id and company_partner_id:
            company_id = self.env.user.company_id.id

            # Get the company_partner_id
            partner_id = self.env.user.company_id.partner_id.id

            # Create an odoo product
            odoo_product = self.env['product.product'].create({'name': vals['name'], 'type': 'service', 
                                                            'company_id': self.env.user.company_id.id, 
                                                            'currency_id': self.env.user.company_id.currency_id.id,
                                                            'sale_ok': True, 
                                                            'purchase_ok': False, 
                                                            'invoice_policy': 'order',
                                                            'product_variant_owner': partner_id,
                                                            'company_id': company_id})
            
            # Update the product template with the owner_id:
            odoo_product.product_tmpl_id.write({'product_owner': partner_id,
                                                'x_product_owner': partner_id})
            
            vals['odoo_product_id'] = odoo_product.id

            product = super(PolygonClientProducts, self).create(vals)

            return product