import pytz
import requests
import json
import logging
#from datetime import datetime, timedelta

from datetime import timedelta
import datetime

from odoo import api, fields, models
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    # shipping_method = fields.Selection([('express', 'Instant 1 Hour'), ('same_day', 'Same Day'), ('next_day', 'Next Day')], default="express",
    #                                    string='Shipping Method', required=True)
    shipsy_order_no = fields.Char(string="Shipsy Order No.",
                                  help="The order number created for the delivery partner against the SO")
    driver_id = fields.Many2one('res.partner', string='Driver')
    product_owner_id = fields.Many2one('res.partner', string='Product Owner', store=True)
    delivery_order_ref = fields.Char(string='Delivery Order Reference', readonly=1, copy=False)
    flag = fields.Boolean(string="Flag", default=False)
    delivery_carrier_id = fields.Many2one('delivery.carrier', string="Shipping Methods")

    def get_order_line_items(self):
        """
        Returns the list of the order lines items/products for the pub/sub integration
        """
        self.ensure_one()
        products = []
        # print("SELF ==>>>>>>>>>>>>>>>>>>",self.order_line)
        picking_ids = self.picking_ids.filtered(lambda x: x.state not in ['cancel', 'done'])
        product_vals = {}
        for line in self.order_line:
            # print("LINE===>>>>>>>>>>",line)         Delivery Fees
            product_vals = {
                "menu_code": line.product_id.default_code or "",  # Internal Ref. of the product
                "menu_description": line.name or line.product_id.name or "",  # Product name/description 
                "size": 3,  # Todo: Need to finalized by the client
                "unit_price": line.price_unit,
                # "shipping_fees": 10,
                "discount": line.discount
            }
            if line.product_id.detailed_type == 'product':
                product_vals.update({
                    "quantity": line.qty_delivered,
                    "order_line_total": format((line.price_unit * line.qty_delivered), ".2f"),
                })
            else:
                product_vals.update({
                    "quantity": line.product_uom_qty,
                    "order_line_total": format((line.price_unit * line.product_uom_qty), ".2f"),
                    })
            
            products.append(product_vals)
        # print("PRODUCTS===>>>>>>>>>>>>>>>>",products)
        return products

    def get_order_details(self):
        """Prepare the order details for the logistiq api and return"""
        self.ensure_one()
        order_data = {}
        product_items = self.get_order_line_items()

        if product_items:
            picking_ids = self.picking_ids.filtered(lambda x: x.state not in ['cancel', 'done'])
            tz = self.warehouse_id.tz

            if self.delivery_carrier_id.shipping_method in ['same_day', 'next_day']:
                if self.delivery_carrier_id.shipping_method == 'same_day':
                    # slot_end = str((self.create_date + timedelta(hours=6)).strftime('%Y-%m-%d %H:%M:%S'))
                    for picking in picking_ids:
                        if not picking.date_deadline:
                            picking.write({
                                'date_deadline': picking.sale_id.commitment_date + timedelta(hours=1)
                            })
                        if picking.date_deadline:
                            slot_start = (picking.date_deadline + timedelta(hours=4))                     
                            slot_end = slot_start + timedelta(hours=1)
                            slot_start = slot_start
                        else:
                            raise UserError("Please Add the Delivery Order date in Sale Order")
                elif self.delivery_carrier_id.shipping_method == 'next_day':
                    
                    for picking in picking_ids:
                        if not picking.date_deadline:
                            picking.write({
                                'date_deadline': picking.sale_id.commitment_date + timedelta(hours=1)
                            })
                        if picking.date_deadline:
                            _logger.info("DEADLINE====>>>>>>>>>>>>>{}".format(picking.date_deadline))
                            # slot_start = (picking.date_deadline + timedelta(hours=4))
                            # slot_end = slot_start + timedelta(hours=1)
                            # slot_start = slot_start
                            slot_start_calc = self.create_date + datetime.timedelta(days=1)
                            slot_end_calc = datetime.time(hour=9, minute=00)
                            slot_start = datetime.datetime.combine(slot_start_calc, slot_end_calc)
                            slot_end = slot_start + timedelta(hours=6)
                        else:
                            raise UserError("Please Add the Delivery Order date in Sale Order")
                store_id = self.warehouse_id.store_id_planned
                order_type = 'planned'
            elif self.delivery_carrier_id.shipping_method == 'express':
                slot_start = self.create_date
                slot_end = (self.create_date + timedelta(hours=1))
                store_id = self.warehouse_id.store_id_express
                order_type = 'express'
            # if slot_start and slot_end:
            #     slot_start = (slot_start.astimezone(pytz.timezone(tz))).strftime('%Y-%m-%d %H:%M:%S')
            #     print(slot_start)
            #     slot_end = (slot_end.astimezone(pytz.timezone(tz))).strftime('%Y-%m-%d %H:%M:%S')
            #     print(slot_end)
            if self.env.context.get('attempt'):
                order_name = self.name + '-' + str(self.env.context.get('attempt'))
            else:
                order_name = self.name

            if self.payment_term_id.name == 'COD':
                payment_vals={
                            "mode": self.payment_term_id.name,  # Payment gateway
                            "value": 0
                        }
            else:
                payment_vals={
                            "mode": self.payment_term_id.name,  # Payment gateway
                            "value": float(self.amount_total)
                        }
            order_data = {
                "order": {
                    "order_number": order_name,  # We have - Shopify Order Number
                    "order_date": self.date_order.astimezone(pytz.timezone(tz)).strftime('%Y-%m-%d'),  # "2022-11-07",
                    "store_id": store_id,  # Shopify store/shopify instance
                    "final_amount": format(self.amount_total, ".2f"),
                    "service_type_id": "PREMIUM",
                    "customer_code": "POLYGONSTORE",
                    "action_type": "delivery",
                    "weight": format(picking_ids.shipping_weight, ".2f"),  # Client will give details
                    "volume": 0,
                    "order_saved": (self.create_date.astimezone(pytz.timezone(tz))).strftime('%Y-%m-%d %H:%M:%S'),  # "2022-06-07 08:11:09",  # Odoo creation time
                    "load_time": str((self.create_date.astimezone(pytz.timezone(tz))).strftime('%Y-%m-%d %H:%M:%S')),
                    "order_type": order_type,  # Client will confirm
                    "slot_start": str(slot_start),  # creation time
                    "slot_end": str(slot_end),  # 1 Hr from creation ("2022-06-07 14:59:59")
                    "instruction": "please do contact less delivery",  # ? Not needed as now
                    "pieces_detail": product_items,  # This will be the product items?
                },
                "customer": {  # We have
                    "latitude": self.partner_id.partner_latitude or 0.0,
                    "longitude": self.partner_id.partner_longitude or 0.0,
                    "customer_name": self.partner_id.name,
                    "phone_number": self.partner_id.phone or self.partner_id.mobile,
                    # "street_number": self.partner_id.street2,
                    "street_name": self.partner_id.street,
                    "address_line_2": self.partner_id.street2,
                    # "address_line_3": self.partner_id.state_id.name,
                    "address_line_4": self.partner_id.country_id.name,
                    "city_name": self.partner_id.state_id.name,
                },
                "payment": [
                    payment_vals
                ]
            }
        # print("ORDER DATA===========>>>>>>",order_data)
        return order_data

    def get_order_update_details(self):
        """Prepare the order update details for the shipsy api and return the data"""
        tz = self.warehouse_id.tz
        order_data = {}
        product_items = self.get_order_line_items()
        if self.delivery_carrier_id.shipping_method in ['same_day', 'next_day']:
            store_id = self.warehouse_id.store_id_planned
            order_type = 'planned'
        elif self.delivery_carrier_id.shipping_method == 'express':
            store_id = self.warehouse_id.store_id_express
            order_type = 'express'
        
        if self.payment_term_id.name == 'COD':
                payment_vals = {
                                    "mode": self.payment_term_id.name,  # Payment gateway
                                    "value": 0
                                 }
        else:
            payment_vals={
                        "mode": self.payment_term_id.name,  # Payment gateway
                        "value": float(self.amount_total)
                    }
        if product_items:
                order_data = {
                    "order_number": self.name,
                    "order_date": self.date_order.astimezone(pytz.timezone(tz)).strftime('%Y-%m-%d'),
                    "store_id": store_id,
                    "instruction": "TOTAL BAGS: 1. \n Please collect 1 insulated bag.",
                    "order_type": order_type, # Client will confirm
                    "final_amount": self.amount_total,
                    "payment": payment_vals,
                    "pieces_detail": product_items,
                    "destination_details": {
                        "latitude": self.partner_id.partner_latitude or 0.0,
                        "longitude": self.partner_id.partner_longitude or 0.0,
                        "customer_name": self.partner_id.name,
                        "street_number": self.partner_id.street2,
                        "street_name": self.partner_id.street,
                        "city_name": self.partner_id.city,
                        "address_line_2": self.partner_id.street,
                        "address_line_3": self.partner_id.state_id.name,
                        "address_line_4": self.partner_id.country_id.name,
                        "phone_number": self.partner_id.phone or self.partner_id.mobile,
                        "postal_code": self.partner_id.zip,
                    }
                }
            # if self.env.context('order_ready'):
            #     order_data.update({
            #         "order_ready": "1"
            #     })
        return order_data

    def action_shipsy_add_order(self):
        """Place the order in Shipsy delivery partner when an order is created in Odoo"""
        if not self.company_id.shipsy_api_key:
            raise UserError("The Shipsy API authorization token is not configured in the company!")
        # print("SELF====>>>>>>>>>>>",self)
        order_data = self.get_order_details()
        _logger.info("\n\n\n\nSHIPSY ORDER DATA===={}".format(order_data))

        if not order_data:
            _logger.info("There is no data to send to the shipsy api for the Order {}!".format(self.name))

        # Make requests to the Shipsy API end point to add the order
        
        url = "https://app.shipsy.in/api/client/integration/consignment/tms/ondemand"
        headers = {
            'x-api-key': '{}'.format(self.company_id.shipsy_api_key),
            'Content-Type': 'application/json',
        }

        response = requests.post(url, headers=headers, data=json.dumps(order_data))
        _logger.info("Response details", response.json())
        
        if response.status_code == 200:
            response_data = response.json()
            
            _logger.info("RESPONSE RAW===>>>>>>>>>>>>>>>{} status is 200 and value of response.json is: ", response_data)
            
            if response_data.get('status') == 1:
                self.update({'shipsy_order_no': response_data.get('order_number')})
                
                _logger.info("Order {} is successfully added to the Shipsy with order number {}...".format(
                    self.name, response_data.get('order_number')))
            else:
                _logger.info("An error occurred while creating the Order {} in Shipsy....!\nDetails:\n{}".format(
                    self.name, response_data))
        else:
            _logger.error('Order {} is not added to Shipsy ! Details below\n:'.format(response.text))
            
            # Response Format
            # {
            #     "status": 1,
            #     "order_number": 15,
            #     "order_date": "2020-06-10"
            # }

    def action_shipsy_update_order(self):
        """Update the order details to Shipsy when an order is updated in Odoo"""
        if not self.company_id.shipsy_api_key:
            raise UserError("The Shipsy API Key is not configured in the company!")

        order_data = self.get_order_update_details()
        _logger.info("SHIPSY UPDATE ORDER DATA===>>>>>>>>>>>>>{}".format(order_data))

        if not order_data:
            _logger.info("There is no data found to update the order in shipsy for the Order {}!".format(self.name))

        # Make requests to the Shipsy API end point to add the order
        url = "https://app.shipsy.in/api/client/integration/ondemand/update_order"
        headers = {
            'x-api-key': '{}'.format(self.company_id.shipsy_api_key),
            'Content-Type': 'application/json',
        }

        response = requests.post(url, headers=headers, data=json.dumps(order_data))
        _logger.error(response.json())
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('data')[0].get('success'):
                _logger.info("Order {} is successfully updated in Shipsy...".format(
                    self.name))
            else:
                _logger.info("An error occurred while updating the Order {} to the Shipsy....!\nDetails:\n{}".format(
                    self.name, response_data))

        else:
            _logger.error('Order {} is not updated in Shipsy ! Details below\n:'.format(response.text))

    def action_shipsy_cancel_order(self):
        """Cancel the order in Shipsy when an order is cancelled in Odoo"""
        tz = self.warehouse_id.tz
        if not self.company_id.shipsy_api_key:
            raise UserError("The Shipsy API authorization token is configured in the company!")
        if self.state != 'done':
            return
        if self.delivery_carrier_id.shipping_method in ['same_day', 'next_day']:
            store_id = self.warehouse_id.store_id_planned
        elif self.delivery_carrier_id.shipping_method == 'express':
            store_id = self.warehouse_id.store_id_express
        payload = [{
            "order_number": self.name,
            "order_date": self.date_order.astimezone(pytz.timezone(tz)).strftime('%Y-%m-%d'),
            "store_id": store_id,
            # "cancellation_reason": "Cancel Order"
        }]

        print(payload)

        # Make requests to the Shipsy API end point to add the order
        url = "https://app.shipsy.in/api/client/integration/ondemand/cancel_order"
        headers = {
            'x-api-key': '{}'.format(self.company_id.shipsy_api_key),
            'Content-Type': 'application/json',
        }

        response = requests.post(url, headers=headers, data=json.dumps(payload))
        _logger.error(response.json())
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('data')[0].get('success'):   # Here assuming that 1 is success
                _logger.info("Order {} is successfully cancelled in Shipsy...".format(self.name))
            else:
                _logger.info("An error occurred while cancelling the Order {} in Shipsy....!\nDetails:\n{}".format(self.name, response_data))
        else:
            _logger.error('Order {} is not cancelled in Shipsy ! Details below\n:'.format(response.text))

    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        # Trigger the update order api to update the details to Shipsy delivery partner
        # if self.shopify_order_id and vals.get('state') != 'cancel':
        if self.order_line:
            if vals.get('state'):
                if vals.get('state') != 'cancel':
                    if self.flag:
                        self.action_shipsy_update_order()
                    # else:
                    #     self.action_shipsy_add_order()
                    #     vals.update({
                    #         'flag': True
                    #     })
        return res

    def _action_cancel(self):
        res = super(SaleOrder, self)._action_cancel()
        # Trigger the cancel order api to cancel the order in Shipsy when order is cancelled in Odoo
        # if self.shopify_order_id:
        self.action_shipsy_cancel_order()
        return res
