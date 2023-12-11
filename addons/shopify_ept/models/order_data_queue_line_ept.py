# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import json
import logging
import time
from odoo import models, fields

_logger = logging.getLogger("Shopify Order Queue Line")


class ShopifyOrderDataQueueLineEpt(models.Model):
    _name = "shopify.order.data.queue.line.ept"
    _description = "Shopify Order Data Queue Line"

    shopify_order_data_queue_id = fields.Many2one("shopify.order.data.queue.ept",
                                                  ondelete="cascade")
    shopify_instance_id = fields.Many2one("shopify.instance.ept", string="Instance",
                                          help="Order imported from this Shopify Instance.")
    state = fields.Selection([("draft", "Draft"), ("failed", "Failed"), ("done", "Done"),
                              ("cancel", "Cancelled")], default="draft", copy=False)
    shopify_order_id = fields.Char(help="Id of imported order.", copy=False)
    sale_order_id = fields.Many2one("sale.order", copy=False,
                                    help="Order created in Odoo.")
    order_data = fields.Text(help="Data imported from Shopify of current order.", copy=False)

    customer_name = fields.Text(help="Shopify Customer Name", copy=False)

    customer_email = fields.Text(help="Shopify Customer Email", copy=False)

    processed_at = fields.Datetime(help="Shows Date and Time, When the data is processed",
                                   copy=False)
    shopify_order_common_log_lines_ids = fields.One2many("common.log.lines.ept",
                                                         "shopify_order_data_queue_line_id",
                                                         help="Log lines created against which line.")
    name = fields.Char(help="Order Name")

    def create_order_queue_line(self, order_dict, instance, order_data, customer_name, customer_email, order_queue_id):
        
        order_queue_line_vals = {"shopify_order_id": order_dict.get("id", False),
                                 "shopify_instance_id": instance.id,
                                 "order_data": order_data,
                                 "name": order_dict.get("name", ""),
                                 "customer_name": customer_name,
                                 "customer_email": customer_email,
                                 "shopify_order_data_queue_id": order_queue_id.id}
        return self.create(order_queue_line_vals)

    def create_order_data_queue_line(self, orders_data, instance, queue_type, created_by="import"):
        #print("22222222222222222222222222",orders_data)
        count = 0
        need_to_create_queue = True
        orders_data.reverse()
        order_queue_list = []
        is_new_order = bool(self._context.get('is_new_order'))
        for order in orders_data:
            if created_by == "webhook" and not is_new_order:
                order_queue, need_to_create_queue = self.search_webhook_order_queue(created_by, instance, order,
                                                                                    queue_type, need_to_create_queue)
            elif not is_new_order:
                order = order.to_dict()

            if need_to_create_queue:
                order_queue = self.shopify_create_order_queue(instance, queue_type, created_by)
                order_queue_list.append(order_queue.id)
                message = "Order Queue %s created." % order_queue.name
                self.generate_simple_notification(message)
                self._cr.commit()
                need_to_create_queue = False
                _logger.info(message)

            data = json.dumps(order)
            customer_name, customer_email = self.get_customer_name_and_email(order)
            self.create_order_queue_line(order, instance, data, customer_name, customer_email, order_queue)
            if created_by == "webhook" and len(order_queue.order_data_queue_line_ids) >= 50:
                order_queue.order_data_queue_line_ids.process_import_order_queue_data(update_order=True)

            count += 1
            if count == 50:
                count = 0
                need_to_create_queue = True
        if not order_queue.order_data_queue_line_ids:
            order_queue.unlink()
            order_queue_list.remove(order_queue.id)

        return order_queue_list

    def search_webhook_order_queue(self, created_by, instance, order, queue_type, need_to_create_queue):
        
        shopify_order_queue_obj = self.env["shopify.order.data.queue.ept"]

        order_queue = shopify_order_queue_obj.search(
            [("created_by", "=", created_by), ("state", "=", "draft"), ("shopify_instance_id", "=", instance.id),
             ("queue_type", "=", queue_type)], limit=1)
        if order_queue:
            message = "Order %s added into Order Queue %s." % (order.get("name"), order_queue.name)
            need_to_create_queue = False
            _logger.info(message)
        return order_queue, need_to_create_queue

    def generate_simple_notification(self, message):
        
        bus_bus_obj = self.env["bus.bus"]
        bus_bus_obj._sendone(self.env.user.partner_id, 'simple_notification',
                             {"title": "Shopify Connector",
                              "message": message, "sticky": False, "warning": True})

    def get_customer_name_and_email(self, order):
        
        try:
            customer_data = order.get("customer")
            customer_name = "%s %s" % (customer_data.get("first_name"),
                                       customer_data.get("last_name"))
            customer_email = customer_data.get("email")
            if customer_name == "None None":
                customer_name = customer_data.get("default_address").get("name")
        except:
            customer_name = False
            customer_email = False

        return customer_name, customer_email

    def shopify_create_order_queue(self, instance, queue_type, created_by="import"):
        
        order_queue_vals = {
            "shopify_instance_id": instance and instance.id or False,
            "created_by": created_by,
            "queue_type": queue_type,
        }

        return self.env["shopify.order.data.queue.ept"].create(order_queue_vals)

    def auto_import_order_queue_data(self):
        
        shopify_order_queue_obj = self.env["shopify.order.data.queue.ept"]
        order_queue_ids = []

        self.env.cr.execute(
            """update shopify_order_data_queue_ept set is_process_queue = False where is_process_queue = True""")
        self._cr.commit()

        query = """select queue.id
                from shopify_order_data_queue_line_ept as queue_line
                inner join shopify_order_data_queue_ept as queue on queue_line.shopify_order_data_queue_id = queue.id
                where queue_line.state='draft' and queue.is_action_require = 'False'
                ORDER BY queue_line.create_date ASC"""
        self._cr.execute(query)
        order_queue_list = self._cr.fetchall()
        if not order_queue_list:
            return True

        for result in order_queue_list:
            if result[0] not in order_queue_ids:
                order_queue_ids.append(result[0])

        queues = shopify_order_queue_obj.browse(order_queue_ids)
        self.filter_order_queue_lines_and_post_message(queues)

    def filter_order_queue_lines_and_post_message(self, queues):
        
        common_log_line_obj = self.env["common.log.lines.ept"]
        start = time.time()
        order_queue_process_cron_time = queues.shopify_instance_id.get_shopify_cron_execution_time(
            "shopify_ept.process_shopify_order_queue")

        for queue in queues:
            order_data_queue_line_ids = queue.order_data_queue_line_ids.filtered(lambda x: x.state == "draft")

            # For counting the queue crashes and creating schedule activity for the queue.
            queue.queue_process_count += 1
            if queue.queue_process_count > 3:
                queue.is_action_require = True
                note = "<p>Need to process this order queue manually.There are 3 attempts been made by " \
                       "automated action to process this queue,<br/>- Ignore, if this queue is already processed.</p>"
                queue.message_post(body=note)
                if queue.shopify_instance_id.is_shopify_create_schedule:
                    common_log_line_obj.create_crash_queue_schedule_activity(queue, "shopify.order.data.queue.ept",
                                                                             note)
                continue

            self._cr.commit()
            order_data_queue_line_ids.process_import_order_queue_data()
            if time.time() - start > order_queue_process_cron_time - 60:
                return True

    def process_import_order_queue_data(self, update_order=False):
       
        sale_order_obj = self.env["sale.order"]

        queue_id = self.shopify_order_data_queue_id if len(self.shopify_order_data_queue_id) == 1 else False
        if queue_id:
            instance = queue_id.shopify_instance_id
            if not instance.active:
                _logger.info("Instance %s is not active.", instance.name)
                return True

            queue_id.is_process_queue = True
            # Below two line used for When the update order webhook calls.
            if update_order or queue_id.created_by == "webhook":
                created_by = 'Webhook'
                sale_order_obj.update_shopify_order(self, created_by, instance)
            else:
                sale_order_obj.import_shopify_orders(self, instance)
            queue_id.write({'is_process_queue': False})

            if instance.is_shopify_create_schedule:
                queue_id.create_schedule_activity(queue_id)
