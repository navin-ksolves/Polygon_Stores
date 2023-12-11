# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, _


class ShopifyQueueProcessEpt(models.TransientModel):
    _name = 'shopify.queue.process.ept'
    _description = 'Shopify Queue Process'

    def manual_queue_process(self):
        
        queue_process = self._context.get('queue_process')
        if queue_process == "process_product_queue_manually":
            self.sudo().process_product_queue_manually()
        if queue_process == "process_customer_queue_manually":
            self.sudo().process_customer_queue_manually()
        if queue_process == "process_order_queue_manually":
            self.sudo().process_order_queue_manually()
        if queue_process == "process_export_stock_queue_manually":
            self.sudo().process_export_stock_queue_manually()

    def process_product_queue_manually(self):
       
        model = self._context.get('active_model')
        shopify_product_queue_line_obj = self.env["shopify.product.data.queue.line.ept"]
        product_queue_ids = self._context.get('active_ids')
        if model == 'shopify.product.data.queue.line.ept':
            product_queue_ids = shopify_product_queue_line_obj.search(
                [('id', 'in', product_queue_ids)]).mapped("product_data_queue_id").ids
        for product_queue_id in product_queue_ids:
            product_queue_line_batch = shopify_product_queue_line_obj.search(
                [("product_data_queue_id", "=", product_queue_id),
                 ("state", "in", ('draft', 'failed'))])
            product_queue_line_batch.process_product_queue_line_data()
        return True

    def process_customer_queue_manually(self):
        
        model = self._context.get('active_model')
        customer_queue_line_obj = self.env["shopify.customer.data.queue.line.ept"]
        customer_queue_ids = self._context.get("active_ids")
        if model == "shopify.customer.data.queue.line.ept":
            customer_queue_ids = customer_queue_line_obj.search([('id', 'in', customer_queue_ids)]).mapped(
                "synced_customer_queue_id").ids
        for customer_queue_id in customer_queue_ids:
            synced_customer_queue_line_ids = customer_queue_line_obj.search(
                [("synced_customer_queue_id", "=", customer_queue_id),
                 ("state", "in", ["draft", "failed"])])
            if synced_customer_queue_line_ids:
                synced_customer_queue_line_ids.process_customer_queue_lines()

    def process_order_queue_manually(self):
      
        model = self._context.get('active_model')
        shopify_order_queue_line_obj = self.env["shopify.order.data.queue.line.ept"]
        order_queue_ids = self._context.get('active_ids')
        if model == "shopify.order.data.queue.line.ept":
            order_queue_ids = shopify_order_queue_line_obj.search([('id', 'in', order_queue_ids)]).mapped(
                "shopify_order_data_queue_id").ids
        self.env.cr.execute(
            """update shopify_order_data_queue_ept set is_process_queue = False where is_process_queue = True""")
        self._cr.commit()
        for order_queue_id in order_queue_ids:
            order_queue_line_batch = shopify_order_queue_line_obj.search(
                [("shopify_order_data_queue_id", "=", order_queue_id),
                 ("state", "in", ('draft', 'failed'))])
            order_queue_line_batch.process_import_order_queue_data()
        return True

    def process_export_stock_queue_manually(self, active_model=None, active_ids=None):
        if active_model:
            model = active_model
        else:
            model = self._context.get('active_model')
        shopify_export_stock_queue_line_obj = self.env["shopify.export.stock.queue.line.ept"]
        if active_ids:
            export_stock_queue_ids = active_ids
        else:
            export_stock_queue_ids = self._context.get('active_ids')
        if model == "shopify.export.stock.queue.line.ept":
            export_stock_queue_ids = shopify_export_stock_queue_line_obj.search(
                [('id', 'in', export_stock_queue_ids)]).mapped("export_stock_queue_id").ids
        self.env.cr.execute(
            """update shopify_export_stock_queue_ept set is_process_queue = False where is_process_queue = True""")
        self._cr.commit()
        for export_stock_queue_id in export_stock_queue_ids:
            export_stock_queue_line_obj = shopify_export_stock_queue_line_obj.search(
                [("export_stock_queue_id", "=", export_stock_queue_id),
                 ("state", "in", ('draft', 'failed'))])
            export_stock_queue_line_obj.process_export_stock_queue_data()
        return True

    def set_to_completed_queue(self):
       
        queue_process = self._context.get('queue_process')
        if queue_process == "set_to_completed_order_queue":
            self.set_to_completed_order_queue_manually()
        if queue_process == "set_to_completed_product_queue":
            self.set_to_completed_product_queue_manually()
        if queue_process == "set_to_completed_customer_queue":
            self.set_to_completed_customer_queue_manually()
        if queue_process == "set_to_completed_export_stock_queue":
            self.set_to_completed_export_stock_queue_manually()

    def set_to_completed_export_stock_queue_manually(self):
       

        export_stock_queue_ids = self._context.get('active_ids')
        export_stock_queue_ids = self.env['shopify.export.stock.queue.ept'].browse(export_stock_queue_ids)

        for export_stock_queue_id in export_stock_queue_ids:
            queue_lines = export_stock_queue_id.export_stock_queue_line_ids.filtered(
                lambda line: line.state in ['draft', 'failed'])
            queue_lines.write({'state': 'cancel'})

        return True

    def set_to_completed_order_queue_manually(self):
       
        order_queue_ids = self._context.get('active_ids')
        order_queue_ids = self.env['shopify.order.data.queue.ept'].browse(order_queue_ids)
        for order_queue_id in order_queue_ids:
            queue_lines = order_queue_id.order_data_queue_line_ids.filtered(
                lambda line: line.state in ['draft', 'failed'])
            queue_lines.write({'state': 'cancel'})
            order_queue_id.message_post(
                body=_("Manually set to cancel queue lines %s - ") % (queue_lines.mapped('shopify_order_id')))
        return True

    def set_to_completed_product_queue_manually(self):
       
        product_queue_ids = self._context.get('active_ids')
        product_queue_ids = self.env['shopify.product.data.queue.ept'].browse(product_queue_ids)
        for product_queue_id in product_queue_ids:
            queue_lines = product_queue_id.product_data_queue_lines.filtered(
                lambda line: line.state in ['draft', 'failed'])
            queue_lines.write({'state': 'cancel', 'shopify_image_import_state': 'done', "synced_product_data": False})
            product_queue_id.message_post(
                body=_("Manually set to cancel queue lines %s - ") % (queue_lines.mapped('product_data_id')))
        return True

    def set_to_completed_customer_queue_manually(self):
        
        customer_queue_ids = self._context.get('active_ids')
        customer_queue_ids = self.env['shopify.customer.data.queue.ept'].browse(customer_queue_ids)
        for customer_queue_id in customer_queue_ids:
            queue_lines = customer_queue_id.synced_customer_queue_line_ids.filtered(
                lambda line: line.state in ['draft', 'failed'])
            queue_lines.write({'state': 'cancel'})
        return True

    def instance_active_archive(self):
       
        instances = self.env['shopify.instance.ept'].browse(self._context.get('active_ids'))
        for instance in instances:
            instance.shopify_action_archive_unarchive()
        return True
