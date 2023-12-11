import re
import requests
import json
import logging
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        sale_order_id = self.env['sale.order'].search([('name','=',self.origin)])
        res = super(StockPicking, self).button_validate()

        _logger.info("CONTEXT===>>>>>>>>>>>>>>>>>>>>{}".format(self._context))
        if  sale_order_id:
            if self.state == 'ready_to_dispatch':
                
                if self.attempt > 0:
                    if self.picking_type_id.code == 'outgoing':
                        self.sale_id.with_context({"attempt": self.attempt}).action_shipsy_add_order()
                if sale_order_id:
                    if self.picking_type_id.code == 'outgoing':
                        if sale_order_id.flag == False:
                            sale_order_id.action_shipsy_add_order()
                            sale_order_id.write({
                                'flag': True
                            })
                        elif sale_order_id.flag == True:
                            sale_order_id.action_shipsy_update_order()
        if self.is_return and self.attempt < 3:
            self.write({'state': 'done'})
            picking_return_id = self.env['stock.return.picking'].sudo() \
                .with_context({'active_id': self.id, 'active_model': 'stock.picking'}).create({
                'picking_id': self.id
            })
            _logger.info('picking_return_id=======>>>>>>>>>>>{}'.format(picking_return_id))
            picking_return_id.sudo()._onchange_picking_id()
            new_picking_id, picking_type_id = picking_return_id.sudo()._create_returns()
            _logger.info('new_picking_id=======>>>>>>>>>>>{}'.format(new_picking_id))
            new_picking_id = self.env['stock.picking'].sudo().search([('id', '=', new_picking_id)])
            new_picking_id.sudo().write({
                'carrier_tracking_ref': self.carrier_tracking_ref,
                'is_return': False
            })
        return res