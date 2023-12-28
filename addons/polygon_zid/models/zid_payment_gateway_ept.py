# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import json
import time

from datetime import datetime, timedelta
from odoo import models, fields
from odoo.exceptions import UserError
#
# from .. import shopify
# from ..shopify.pyactiveresource.connection import ClientError


class ZidPaymentGateway(models.Model):
    _name = 'zid.payment.gateway.ept'
    _description = "Zid Payment Gateway"

    name = fields.Char(help="Payment method name")
    code = fields.Char(help="Payment method code given by zid")
    zid_instance_id = fields.Many2one('zid.instance.ept', 'Zid Instance')
    active = fields.Boolean(default=True)

    # def import_payment_gateway(self, instance):
    #
    #     to_date = datetime.now()
    #     from_date = to_date - timedelta(7)
    #
    #     try:
    #         results = shopify.Order().find(status="any", updated_at_min=from_date,
    #                                        updated_at_max=to_date, fields=['gateway'], limit=250)
    #     except ClientError as error:
    #         if hasattr(error, "response"):
    #             if error.response.code == 429 and error.response.msg == "Too Many Requests":
    #                 time.sleep(int(float(error.response.headers.get('Retry-After', 5))))
    #                 results = shopify.Order().find(status="any", updated_at_min=from_date,
    #                                                updated_at_max=to_date, fields=['gateway'], limit=250)
    #             else:
    #                 message = str(error.code) + "\n" + json.loads(error.response.body.decode()).get("errors")
    #                 raise UserError(message)
    #     except Exception as error:
    #         raise UserError(error)
    #
    #     for result in results:
    #         result = result.to_dict()
    #         gateway = result.get('gateway') or "no_payment_gateway"
    #         self.search_or_create_payment_gateway(instance, gateway)
    #
    #     return True
    #
    # def search_or_create_payment_gateway(self, instance, gateway_name):
    #
    #     shopify_payment_gateway = self.search([('code', '=', gateway_name),
    #                                            ('shopify_instance_id', '=', instance.id)], limit=1)
    #     if not shopify_payment_gateway:
    #         shopify_payment_gateway = self.create({'name': gateway_name,
    #                                                'code': gateway_name,
    #                                                'shopify_instance_id': instance.id})
    #     return shopify_payment_gateway
    #
    # def shopify_search_create_gateway_workflow(self, instance, order_data_queue_line, order_response,
    #                                            gateway):
    #
    #     common_log_line_obj = self.env["common.log.lines.ept"]
    #     auto_workflow_id = False
    #
    #     shopify_payment_gateway = self.search_or_create_payment_gateway(instance, gateway)
    #
    #     workflow_config = self.env['sale.auto.workflow.configuration.ept'].search(
    #         [('shopify_instance_id', '=', instance.id),
    #          ('payment_gateway_id', '=', shopify_payment_gateway.id),
    #          ('financial_status', '=', order_response.get('financial_status'))])
    #     if not workflow_config:
    #
    #         message = "- Automatic order process workflow configuration not found for this order " \
    #                   "%s. \n - System tries to find the workflow based on combination of Payment " \
    #                   "Gateway(such as Manual,Credit Card, Paypal etc.) and Financial Status(such as Paid," \
    #                   "Pending,Authorised etc.).\n - In this order Payment Gateway is %s and Financial Status is %s." \
    #                   " \n - You can configure the Automatic order process workflow " \
    #                   "under the menu Shopify > Configuration > Financial Status." % (order_response.get('name'),
    #                                                                                   gateway,
    #                                                                                   order_response.get(
    #                                                                                       'financial_status'))
    #         common_log_line_obj.create_common_log_line_ept(shopify_instance_id=instance.id, message=message,
    #                                                        model_name='sale.order',
    #                                                        order_ref=order_response.get('name'),
    #                                                        shopify_order_data_queue_line_id=order_data_queue_line.id
    #                                                        if order_data_queue_line else False)
    #         if order_data_queue_line:
    #             order_data_queue_line.write({'state': 'failed', 'processed_at': datetime.now()})
    #         return shopify_payment_gateway, auto_workflow_id, False
    #
    #     auto_workflow_id = workflow_config.auto_workflow_id if workflow_config else False
    #     payment_term = workflow_config.payment_term_id if workflow_config else False
    #     if auto_workflow_id and not auto_workflow_id.picking_policy:
    #         message = "- Picking policy decides how the products will be delivered, " \
    #                   "'Deliver all at once' or 'Deliver each when available'.\n- System found %s Auto Workflow, " \
    #                   "but coudn't find configuration about picking policy under it." \
    #                   "\n- Please review the Auto workflow configuration here : " \
    #                   "Shopify > Configuration > Sale Auto " \
    #                   "Workflow" % auto_workflow_id.name
    #         common_log_line_obj.create_common_log_line_ept(shopify_instance_id=instance.id, message=message,
    #                                                        model_name='sale.order',
    #                                                        order_ref=order_response.get('name'),
    #                                                        shopify_order_data_queue_line_id=order_data_queue_line.id
    #                                                        if order_data_queue_line else False)
    #         if order_data_queue_line:
    #             order_data_queue_line.write({'state': 'failed', 'processed_at': datetime.now()})
    #         auto_workflow_id = False
    #
    #     return shopify_payment_gateway, auto_workflow_id, payment_term