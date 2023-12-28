import re
import requests
import json
import logging
from datetime import datetime, timedelta

from odoo import api, fields, models
from . import common_functions
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        if self.picking_type_code == 'incoming':
            self.update_product_quantity_in_zid()

    def update_product_quantity_in_zid(self):
        instance_id = self.env['zid.instance.ept'].browse(29)
        product_id_list = []
        data_json = {'data':product_id_list}
        for move_id in self.move_ids:
            product_id_list.append(move_id.product_id.id)
        common_functions.create_log_in_scheduler(self,instance_id,['update_product_quant'], data_json)
