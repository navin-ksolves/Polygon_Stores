# -*- coding: utf-8 -*-
from odoo import http
from odoo.exceptions import UserError
from odoo.http import request
from datetime import datetime
import logging

utc_time = datetime.utcnow()
_logger = logging.getLogger(__name__)


class DeliveryCarrier(http.Controller):
    @http.route('/order/update/status', type="json", auth="public", methods=['POST'], cors="*")
    def order_update_status(self):
        post_data = request.get_json_data()
        _logger.info("POST DATA===>>>>>>>>>>>>>>>>>>>{}".format(post_data))
        _logger.info("SESSION===>>>>>>>>>>>>>>{}".format(request.session))
        if post_data.get('order_number'):
            if '#' in post_data.get('order_number'):
                order = (post_data.get('order_number').split('#'))[0]
            else:
                order = post_data.get('order_number')
            # user_id = request.env['res.users'].sudo().search([('id','=',2)])
            # _logger.info("COMPANY IDS++++====>>>>>>>>>>{}".format(user_id.company_ids.ids))
            sale_order = request.env['sale.order'].sudo().search([('name', '=', order)])
            _logger.info("SALE ORDER====>>>>>>>>>>>>{}".format(sale_order))
            if post_data.get('worker'):
                worker_dict = post_data.get('worker')
                _logger.info("WORKER DICT====>>>>>>>>>>>>>>{}".format(worker_dict))
                if worker_dict.get('name'):
                    vals = {
                        'name': worker_dict['name'],
                        'mobile': worker_dict['virtual_number'],
                        'phone': worker_dict['contact'],
                        'partner_latitude': worker_dict['lat'],
                        'partner_longitude': worker_dict['lng']
                    }
                    driver_id = request.env['res.partner'].sudo().create(vals)
                    if sale_order:
                        if driver_id:
                            sale_order.write({
                                'driver_id': driver_id.id
                            })


            if sale_order:
                _logger.info("ORDER===>>>>>>>>>>>>>>>>{}".format(order))
                
                picking_id = request.env['stock.picking'].sudo().search([('sale_id', '=', sale_order.id),('state','not in',['done','cancel'])])
                _logger.info("PICKING ID====>>>>>>>>>>>>>>{}".format(picking_id))
                if order:
                    sale_dict = {
                        'delivery_order_ref': order
                    }
                    sale_order.sudo().write(sale_dict)
                if post_data.get('tracking_url'):
                    # print("TRAKING URL===")
                    picking_dict = {
                        'carrier_tracking_ref': post_data.get('tracking_url'),
                        'carrier_tracking_url': post_data.get('tracking_url')
                    }
                    picking_id.sudo().write(picking_dict)
                if post_data.get('status') in ['pickup_completed', 'outfordelivery']:
                    if picking_id.move_ids_without_package:
                        for move_line_id in picking_id.move_ids_without_package:
                            if move_line_id.product_uom_qty == move_line_id.quantity_done:
                                quantity = True
                            else:
                                quantity = False
                                _logger.info('Demanded quantities and done quantities are not matching.')
                                break
                        if quantity:
                            picking_id.sudo().write({'state': 'in_transit'})
                elif post_data.get('status') == 'delivered':
                    picking_id.sudo().write({'state': 'done'})

                elif post_data.get('status') in ['attempted', 'cancelled']:
                    if picking_id.state not in ['done', 'cancel']:
                        if picking_id.attempt >= 3:
                            picking_id.sudo().write({'state': 'done'})
                            _logger.info("This is the 4th attempt of this order which is not allowed")
                            raise UserError("This is the 4th attempt of this order which is not allowed")

                        attempt_count = picking_id.attempt + 1
                        _logger.info("PICKING===>>>>>>>>>>>>>>{}".format(picking_id))
                        picking_id.sudo().write({'state': 'done'})
                        _logger.info("STATE===>>>>>>>>>>>>>>{}".format(picking_id.state))
                        picking_return_id = request.env['stock.return.picking'].sudo() \
                            .with_context({'active_id': picking_id.id, 'active_model': 'stock.picking'}).create({
                            'picking_id': picking_id.id
                        })
                        _logger.info('picking_return_id=======>>>>>>>>>>>{}'.format(picking_return_id))
                        picking_return_id.sudo()._onchange_picking_id()
                        new_picking_id, picking_type_id = picking_return_id.sudo()._create_returns()
                        _logger.info('new_picking_id=======>>>>>>>>>>>{}'.format(new_picking_id))
                        new_picking_id = request.env['stock.picking'].sudo().search([('id', '=', new_picking_id)])
                        if attempt_count == 1:
                            attempt_state = 'attempt_2'
                        elif attempt_count in [2, 3]:
                            attempt_state = 'attempt_3'

                        new_picking_id.sudo().write({
                            'attempt': attempt_count,
                            # 'attempted_state': attempt_state,
                            'carrier_tracking_ref': picking_id.carrier_tracking_ref,
                            'is_return': True,
                            'state': 'confirmed'
                        })

                elif post_data.get('status') in ['rto_delivered', 'reachedathub']:
                    picking_id.sudo().write({
                        'state': 'assigned'
                    })
