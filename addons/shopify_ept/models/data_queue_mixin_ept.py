# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models


class DataQueueMixinEpt(models.AbstractModel):
    _inherit = "data.queue.mixin.ept"

    def delete_data_queue_ept(self, queue_data=False, is_delete_queue=False):
        
        if not queue_data:
            queue_data = []
        queue_data += ["shopify_product_data_queue_ept", "shopify_order_data_queue_ept",
                       "shopify_customer_data_queue_ept"]
        return super(DataQueueMixinEpt, self).delete_data_queue_ept(queue_data, is_delete_queue)
