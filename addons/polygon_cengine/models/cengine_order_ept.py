from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

import logging

_logger = logging.getLogger("Conversion Engine - Order Model")

class CengineOrderEpt(models.Model):
    _name = 'cengine.order.ept'
    _description = 'Conversion Engine Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Order Name", required=True, tracking=True)
    online_order_id = fields.Integer(string="Online Order ID", tracking=True, required=True, index=True)
    invoice_no = fields.Char(string="Invoice No", tracking=True, required=True, index=True)
    order_partner_id = fields.Many2one('cengine.customer.ept', string="Order Partner", tracking=True)
    partner_location_id = fields.Many2one('res.partner', string="Partner Location", tracking=True)
    so_id = fields.Many2one('sale.order', string="Sale Order", tracking=True, required=False, index=True)
    instance_id = fields.Many2one('cengine.instance.ept', string="Instance", tracking=True, required=True, index=True)
    schedule_id = fields.Many2one('cengine.scheduler.ept', string="Schedule", tracking=True, index=True)
    item_id = fields.Integer(string="Item ID", tracking=True, required=True, index=True)
    order_datetime = fields.Datetime(string="Order Date", tracking=True)
    fulfillment_status = fields.Selection([('fulfilled', 'Fulfilled'), ('unfulfilled', 'Unfulfilled')], string="Fulfillment Status", tracking=True, default='unfulfilled')
    financial_status = fields.Boolean(string="Financial Status", tracking=True)
    currency = fields.Many2one('res.currency', string="Currency", tracking=True, default=lambda self: self.env.company.currency_id.id)
    payment_method = fields.Char(string="Payment Method", tracking=True)
    subtotal_price = fields.Float(string="Subtotal Price", tracking=True)
    discount_code = fields.Char(string="Discount Code", tracking=True)
    discount_type = fields.Char(string="Discount Type", tracking=True)
    total_discount = fields.Float(string="Total Discount", tracking=True)
    shipping_method = fields.Char(string="Shipping Method", tracking=True, default='polygon_shipping')
    shipping_price = fields.Float(string="Shipping Price", tracking=True)
    taxes = fields.Char(string="Taxes", tracking=True)
    total_tax = fields.Float(string="Total Tax", tracking=True)
    total_price = fields.Float(string="Total Price", tracking=True)


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Check if the order already exists:
            order = self.env['cengine.order.ept'].sudo().search([('online_order_id', '=', vals['online_order_id']), 
                                                                ('instance_id', '=', vals['instance_id'])])

            if order:
                _logger.info("Order already exists!")
                return (order.id, order.so_id.id)
            else:
                customer_id = self.env['cengine.customer.ept'].sudo().search([('id', '=', vals['order_partner_id'])]).customer_partner_id.id
                delivery_address_id = self.env['cengine.customer.locations'].sudo().search([('id', '=', vals['delivery_address_id'])])
                del vals['delivery_address_id']
                invoice_address_id = self.env['cengine.customer.locations'].sudo().search([('id', '=', vals['invoice_address_id'])])
                del vals['invoice_address_id']
                delivery_deadline = datetime.utcnow() + timedelta(hours=2)
                instance = self.env['cengine.instance.ept'].sudo().search([('id', '=', vals['instance_id'])])
                # Generate an order name based on count with prefilled zeros:
                vals['name'] = instance.name + ' - ' + str(self.env['cengine.order.ept'].sudo().search_count([('instance_id', '=', vals['instance_id'])]) + 1).zfill(8)
                sales_team_id = instance.sales_team_id

                if vals['paid'] == True:
                    payment_terms = 'Postpaid'
                    vals['financial_status'] = True
                else:
                    payment_terms = 'COD'
                    vals['financial_status'] = False

                del vals['paid']
                payment_term_id = self.env['account.payment.term'].sudo().search([('name', '=', payment_terms)], limit=1)

                instance = self.env['cengine.instance.ept'].sudo().search([('id', '=', vals['instance_id'])])

                delivery_carrier_id = self.env['delivery.carrier'].sudo().search([('shipping_method', '=', 'express')]).id

                invoice_vals = {
                                'partner_id': customer_id,
                                'partner_invoice_id': invoice_address_id.address_id.id,
                                'partner_shipping_id': delivery_address_id.address_id.id,
                                'state': 'draft',
                                'commitment_date': delivery_deadline,
                                'online_order_id': vals['online_order_id'],
                                'owner_id': instance.polygon_client_id.partner_id.id,
                                'product_owner_id': instance.polygon_client_id.partner_id.id,
                                'online_source': 'conversion_engine',
                                'instance_id': instance.polygon_instance_id.id,
                                'company_id': instance.company_id.id,
                                'warehouse_id': instance.warehouse_id.id,
                                'team_id': sales_team_id.id,
                                'payment_term_id': payment_term_id.id,
                                'client_order_ref': vals['invoice_no'],
                                'delivery_carrier_id': delivery_carrier_id,
                                'fiscal_position_id': vals['fiscal_position_id']
                            }
                
                _logger.info("Creating SO with vals - %s", invoice_vals)
                
                # Create the order in odoo:
                so = self.env['sale.order'].with_user(user=instance.default_user.id).create(invoice_vals)
                
                vals['so_id'] = so.id
                del vals['owner_id']
                del vals['taxes']
                del vals['fiscal_position_id']

                # Create the order:
                order = super(CengineOrderEpt, self).create(vals)
                _logger.info("Order created!")

        self.env.cr.commit()
                
        return (order, vals['so_id'])
        
class CengineOrderLinesEpt(models.Model):
    _name = 'cengine.order.lines.ept'
    _description = 'Conversion Engine Order Lines'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Order Line Name", required=True, tracking=True)
    order_line_id = fields.Integer(string="Order Line ID", tracking=True, required=True, index=True)
    order_id = fields.Many2one('cengine.order.ept', string="Order", tracking=True, required=True, index=True)
    so_line_count = fields.Integer(string="SO Line Count", tracking=True, required=True, index=True)
    so_line_id = fields.Many2one('sale.order.line', string="Sale Order Line", tracking=True, required=False, index=True)
    product_id = fields.Many2one('product.product', string="Product", tracking=True, required=True, index=True)
    item_id = fields.Many2one('cengine.product.template', string="Item", tracking=True, required=True, index=True)
    sku = fields.Char(string="SKU", tracking=True, required=False)
    quantity = fields.Float(string="Quantity", tracking=True)
    price = fields.Float(string="Price", tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        order_line = []
        for vals in vals_list:
            instance = self.env['cengine.instance.ept'].sudo().search([('id', '=', vals['instance_id'])])

            cengine_product_template = self.env['cengine.product.template'].sudo().search([('cengine_product_template_id', '=', vals['item_id']),
                                                                                            ('instance_id', '=', vals['instance_id'])])
            
            if not cengine_product_template:
                _logger.info("Product template not found!")
                raise ValidationError("Product template not found!")
            
            if cengine_product_template.has_variants == True:

                combination_indices_internal = []
            
                for variant in vals['variants']:

                    option = self.env['cengine.product.options'].search([('name', '=', variant['name'])])
                    option_value_id = self.env['cengine.product.option.values'].search([('name', '=', variant['value']),
                                                                                        ('cengine_product_options_id', '=', option.id)])

                    combination_indices_internal.append(option_value_id)
                    
                combination_indices_internal = ','.join(map(str, combination_indices_internal))
                _logger.info("Combination indices internal - %s", combination_indices_internal)
                cengine_product_variant = self.env['cengine.product.variants'].sudo().search([('cengine_product_template_id', '=', cengine_product_template.id),
                                                                                            ('combination_indices_internal', '=', combination_indices_internal)])
                
                product_id = cengine_product_variant.product_variant_id.id
                product_name = cengine_product_variant.product_variant_id.name

                if not product_id:
                    product_id = cengine_product_template.product_id.id
                    product_name = vals['name']

            else:
                
                product_id = cengine_product_template.product_id.id
                product_name = vals['name']
            
            order_line_id = self.env['cengine.order.lines.ept'].sudo().search([('order_line_id', '=', vals['order_line_id']),
                                                                                ('order_id', '=', vals['order_id']),
                                                                                ('product_id', '=', product_id),
                                                                                ('item_id', '=', cengine_product_template.id),
                                                                                ('so_line_count', '=', vals['so_line_count'])])
            
            if not order_line_id:
                vals_lines = {
                            'name': product_name,
                            'order_line_id': vals['order_line_id'],
                            'order_id': vals['order_id'],
                            'product_id': product_id,
                            'item_id': cengine_product_template.id,
                            'sku': vals['sku'] if vals['sku'] != None else product_name,
                            'quantity': vals['quantity'],
                            'price': vals['price'],
                            'so_line_count': vals['so_line_count']
                            }
                
                # Create the order line:
                _logger.info("Creating Order Line with vals - %s", vals_lines)
                order_line_id = super(CengineOrderLinesEpt, self).create(vals_lines)
                _logger.info("Order line created in EPT!")

                # Create the order line in odoo so_id:
                so_line = self.env['sale.order.line'].with_user(user=instance.default_user.id).create({
                                                                    'order_id': vals['so_id'],
                                                                    'product_id': product_id,
                                                                    'name': product_name,
                                                                    'product_uom_qty': vals['quantity'],
                                                                    'tax_id': [(6,0, [vals['tax_id']])],
                                                                    'price_unit': vals['price'],
                                                                    'customer_lead': 0
                                                                    })
                
                order_line_id.write({'so_line_id': so_line.id})

            else:
                if not order_line_id.so_line_id:
                    # Create the order line in odoo so_id:
                    so_line = self.env['sale.order.line'].with_user(user=instance.default_user.id).create({
                                                                        'order_id': vals['so_id'],
                                                                        'product_id': product_id,
                                                                        'name': product_name,
                                                                        'product_uom_qty': vals['quantity'],
                                                                        'tax_id': [(6,0, [vals['tax_id']])],
                                                                        'price_unit': vals['price'],
                                                                        'customer_lead': 0
                                                                        })
                    
                    order_line_id.write({'so_line_id': so_line.id})

            order_line.append(order_line_id.id)
        
        self.env.cr.commit()

        return order_line
            