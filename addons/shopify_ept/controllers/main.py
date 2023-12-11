# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import logging
from odoo import http
from odoo.http import request
from odoo.exceptions import Warning, UserError, ValidationError

_logger = logging.getLogger("Shopify Controller")


class Main(http.Controller):

    @http.route(['/shopify_odoo_webhook_for_product_update', '/shopify_odoo_webhook_for_product_delete'], csrf=False,
                auth="public", type="json")
    def create_update_delete_product_webhook(self):
       
        webhook_route = request.httprequest.path.split('/')[1]  # Here we receive two type of route
        # 1) Update and create product (shopify_odoo_webhook_for_product_update)
        # 2) Delete product (shopify_odoo_webhook_for_product_delete)

        res, instance = self.get_basic_info(webhook_route)
        host = request.httprequest.headers.get("X-Shopify-Shop-Domain")
        instance = request.env["shopify.instance.ept"].sudo().with_context(active_test=False).search(
            [("shopify_host", "ilike", host)], limit=1)
        for tags_id in instance.shopify_tag_ids:
            if not tags_id.name == res.get("tags"):
            #if not res.get("tags"):
                raise ValidationError('Please Add Product Tags.')
                return
                
            product_id = request.env["shopify.product.template.ept"].sudo().search([("shopify_tmpl_id","=",res.get("id"))])
            product_tm_id = request.env["shopify.product.product.ept"].sudo().search([("shopify_template_id","=",product_id.id)])
            if product_id and product_tm_id:
                product_id.product_tmpl_id.name = res.get("title")
                product_id.name = res.get("title")
                product_tm_id.name = res.get("title")
                
                product_id.description = res.get("body_html")
                product_id.product_tmpl_id.description = res.get("body_html")
                for line in res.get("variants"):
                    product_id.product_tmpl_id.list_price = line.get("price")
                
            else:    
                _logger.info("%s call for product: %s", webhook_route, res.get("title"))

                shopify_template = request.env["shopify.product.template.ept"].sudo().with_context(active_test=False).search(
                [("shopify_tmpl_id", "=", res.get("id")), ("shopify_instance_id", "=", instance.id)], limit=1)

                if webhook_route == 'shopify_odoo_webhook_for_product_update' and shopify_template or res.get("published_at"):
                    request.env["shopify.product.data.queue.ept"].sudo().create_shopify_product_queue_from_webhook(res,
                                                                                                           instance)

                if webhook_route == 'shopify_odoo_webhook_for_product_delete' and shopify_template:
                    shopify_template.write({"active": False})
                return

    @http.route(['/shopify_odoo_webhook_for_customer_create', '/shopify_odoo_webhook_for_customer_update'], csrf=False,
                auth="public", type="json")
    def customer_create_or_update_webhook(self):
       
        webhook_route = request.httprequest.path.split('/')[1]  # Here we receive two type of route
        # 1) Create Customer (shopify_odoo_webhook_for_customer_create)
        # 2) Update Customer(shopify_odoo_webhook_for_customer_update)

        res, instance = self.get_basic_info(webhook_route)

        if not res:
            return
        if res.get("first_name") and res.get("last_name"):
            customer = request.env["shopify.res.partner.ept"].sudo().search([("shopify_customer_id","=",res.get("id"))])
            if customer:
                customer.partner_id.name = res.get("first_name") + res.get("last_name")
                customer.partner_id.email = res.get("email")
                customer.partner_id.phone = res.get("phone")
                customer.partner_id.comment = res.get("note")
            else:
                _logger.info("%s call for Customer: %s", webhook_route,
                         (res.get("first_name") + " " + res.get("last_name")))
                self.customer_webhook_process(res, instance)
        return

    def customer_webhook_process(self, response, instance):
        process_import_export_model = request.env["shopify.process.import.export"].sudo()
        process_import_export_model.webhook_customer_create_process(response, instance)
        
        return True

    @http.route("/shopify_odoo_webhook_for_orders_partially_updated", csrf=False, auth="public", type="json")
    def order_create_or_update_webhook(self):
       
        res, instance = self.get_basic_info("shopify_odoo_webhook_for_orders_partially_updated")
        sale_order = request.env["sale.order"]
        if not res:
            return
            

        
        sale_order = request.env["sale.order"].sudo().search([("name","=",res.get("name"))])
        if sale_order:
            new_lines = []
            for line in res.get("line_items"):
            
                product_id = request.env["shopify.product.template.ept"].sudo().search([("shopify_tmpl_id","=",line.get("product_id"))])
                main_product_id = request.env["product.product"].sudo().search([("default_code","=",product_id.product_tmpl_id.default_code)])
                #for line_order in sale_order.order_line:
                    #line_order.unlink()
                new_lines.append((0, 0, {
                          'product_id' : main_product_id.id,
                          'name' : main_product_id.name,
                          'product_uom_qty' : line.get("quantity"),
                         
                          
                          
                 }))
            sale_order.order_line.unlink()
            sale_order.write({ 'order_line' : new_lines })         
        _logger.info("UPDATE ORDER WEBHOOK call for order: %s", res.get("name"))

        fulfillment_status = res.get("fulfillment_status") or "unfulfilled"
        if sale_order.sudo().search_read([("shopify_instance_id", "=", instance.id),
                                          ("shopify_order_id", "=", res.get("id")),
                                          ("shopify_order_number", "=",
                                           res.get("order_number"))],
                                         ["id"]):
            sale_order.sudo().process_shopify_order_via_webhook(res, instance, True)
        elif fulfillment_status in ["fulfilled", "unfulfilled", "partial"]:
            res["fulfillment_status"] = fulfillment_status
            
            sale_order.sudo().with_context({'is_new_order': True}).process_shopify_order_via_webhook(res,
                                                                                                     instance)
        return

    def get_basic_info(self, route):
       
        res = request.get_json_data()
        host = request.httprequest.headers.get("X-Shopify-Shop-Domain")
        instance = request.env["shopify.instance.ept"].sudo().with_context(active_test=False).search(
            [("shopify_host", "ilike", host)], limit=1)
        webhook = request.env["shopify.webhook.ept"].sudo().search([("instance_id", "=", instance.id)], limit=1)
        if not instance.active or not webhook.state == "active":
            _logger.info("The method is skipped. It appears the instance:%s is not active or that "
                         "the webhook %s is not active.", instance.name, webhook.webhook_name)
            res = False
        return res, instance
