# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models, tools, Command
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = "stock.picking"

    updated_in_shopify = fields.Boolean(default=False)
    is_shopify_delivery_order = fields.Boolean("Shopify Delivery Order", default=False)
    shopify_instance_id = fields.Many2one("shopify.instance.ept", "Shopify Instance")
    shopify_location_id = fields.Many2one("shopify.location.ept", "Shopify Location")
    is_cancelled_in_shopify = fields.Boolean("Is Cancelled In Shopify ?", default=False, copy=False,
                                             help="Use this field to identify shipped in Odoo but cancelled in Shopify")
    is_manually_action_shopify_fulfillment = fields.Boolean("Is Manually Action Required ?", default=False, copy=False,
                                                            help="Those orders which we may fail update fulfillment "
                                                                 "status, we force set True and use will manually take "
                                                                 "necessary actions")
    shopify_fulfillment_id = fields.Char(string='Shopify Fulfillment Id')
    attempt = fields.Integer('Attempt')
    is_return = fields.Boolean('Is Return')
    # attempted_state = fields.Selection([('attempted', 'Attempted'),
    #                                     ('attempt_2', '2nd Attempt'),
    #                                     ('attempt_3', '3rd Attempt')], default='attempted')
    state = fields.Selection(
        selection_add=[
            ('ready_to_dispatch', 'Ready To Dispatch'),
            ('in_transit', 'In Transit'),
            ('done', 'Done'),
            ('cancel', 'Cancelled'),
        ])

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        sale_order_id = self.env['sale.order'].search([('name', '=', self.origin)])
        delivery_type = sale_order_id.delivery_carrier_id.shipping_method
        if self.picking_type_code == 'incoming' and not self.is_return:
            instance = self.env['shopify.instance.ept'].search([('shopify_contact_id','=',self.owner_id.id)])
            if instance:
                product_queue_vals = {
                    "shopify_instance_id": instance and instance.id or False
                }
                stock_queue_id = self.env['shopify.export.stock.queue.ept'].create(product_queue_vals)
                for move_id in self.move_ids:
                    shopify_product_id = self.env['shopify.product.product.ept'].search([('product_id','=',move_id.product_id.id)])
                    vals={
                        'name': shopify_product_id.default_code,
                        'shopify_product_id': shopify_product_id.id,
                        'inventory_item_id': shopify_product_id.inventory_item_id,
                        'quantity': move_id.quantity_done,
                        'state': 'draft',
                        'export_stock_queue_id': stock_queue_id.id,
                        'location_id': self.shopify_location_id.shopify_location_id
                    }
                    self.env['shopify.export.stock.queue.line.ept'].create(vals)

                    wizard_id = self.env['shopify.queue.process.ept']
                    wizard_id.process_export_stock_queue_manually('shopify.export.stock.queue.line.ept', stock_queue_id.export_stock_queue_line_ids.ids)
        
        if self.picking_type_id.code == 'outgoing':
                    if not self.env.context.get('skip_backorder'):
                        pickings_to_backorder = self._check_backorder()
                        if pickings_to_backorder:
                            return res
                        else:
                            if delivery_type == 'vendor_del':
                                self.write({
                                    'state': 'done'
                                })
                            else:
                                self.write({
                                    'state': 'ready_to_dispatch'
                                })
                    else:
                        self.write({
                                'state': 'ready_to_dispatch'
                            })
        return res
    
    def manually_update_shipment(self):
        
        picking = self
        self.env['sale.order'].update_order_status_in_shopify(self.shopify_instance_id, picking_ids=picking)
        return True
        
        
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        for picking in self:
            instance_id = self.env["shopify.instance.ept"].search([("shopify_contact_id","=",picking.partner_id.id)])
            picking.write({'shopify_instance_id': instance_id.id})
            picking.write({'owner_id': picking.partner_id.id})
            picking.write({'shopify_location_id': instance_id.shopify_location_id.id})
            picking_id = isinstance(picking.id, int) and picking.id or getattr(picking, '_origin', False) and picking._origin.id
            if picking_id:
                moves = self.env['stock.move'].search([('picking_id', '=', picking_id)])
                for move in moves:
                    move.write({'partner_id': picking.partner_id.id})


class StockPickingReturn(models.TransientModel):
    _inherit = 'stock.return.picking'

    @api.onchange('picking_id')
    def _onchange_picking_id(self):
        move_dest_exists = False
        product_return_moves = [(5,)]
        print("self.picking_id.state====",self.picking_id.state)
        if self.picking_id and self.picking_id.state != 'done':
            raise UserError(_("You may only return Done pickings."))
        # In case we want to set specific default values (e.g. 'to_refund'), we must fetch the
        # default values for creation.
        line_fields = [f for f in self.env['stock.return.picking.line']._fields.keys()]
        product_return_moves_data_tmpl = self.env['stock.return.picking.line'].default_get(line_fields)
        for move in self.picking_id.move_ids:
            if move.state == 'cancel':
                continue
            if move.scrapped:
                continue
            if move.move_dest_ids:
                move_dest_exists = True
            product_return_moves_data = dict(product_return_moves_data_tmpl)
            product_return_moves_data.update(self._prepare_stock_return_picking_line_vals_from_move(move))
            product_return_moves.append((0, 0, product_return_moves_data))
        if self.picking_id and not product_return_moves:
            raise UserError(
                _("No products to return (only lines in Done state and not fully returned yet can be returned)."))
        if self.picking_id:
            self.product_return_moves = product_return_moves
            self.move_dest_exists = move_dest_exists
            self.parent_location_id = self.picking_id.picking_type_id.warehouse_id and self.picking_id.picking_type_id.warehouse_id.view_location_id.id or self.picking_id.location_id.location_id.id
            self.original_location_id = self.picking_id.location_id.id
            location_id = self.picking_id.location_id.id
            if self.picking_id.picking_type_id.return_picking_type_id.default_location_dest_id.return_location:
                location_id = self.picking_id.picking_type_id.return_picking_type_id.default_location_dest_id.id
            self.location_id = location_id

        
        
   
