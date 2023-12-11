# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from datetime import datetime
from odoo.exceptions import UserError
from odoo import models, fields, api, _


class ProductProduct(models.Model):
    _inherit = "product.product"

    ept_image_ids = fields.One2many('common.product.image.ept', 'product_id', string='Product Images')
    is_drop_ship_product = fields.Boolean(store=False, compute="_compute_is_drop_ship_product")

    @api.depends('route_ids')
    def _compute_is_drop_ship_product(self):
      
        customer_locations = self.env['stock.location'].search([('usage', '=', 'customer')])
        route_ids = self.route_ids | self.categ_id.route_ids
        stock_rule = self.env['stock.rule'].search([('company_id', '=', self.env.company.id), ('action', '=', 'buy'),
                                                    ('location_id', 'in', customer_locations.ids),
                                                    ('route_id', 'in', route_ids.ids)])
        if stock_rule:
            self.is_drop_ship_product = True
        else:
            self.is_drop_ship_product = False

    def prepare_common_image_vals(self, vals):
       
        image_vals = {"sequence": 0,
                      "image": vals.get("image_1920", False),
                      "name": self.name,
                      "product_id": self.id,
                      "template_id": self.product_tmpl_id.id}
        return image_vals

    @api.model
    def create(self, vals):
       
        res = super(ProductProduct, self).create(vals)
        if vals.get("image_1920", False) and res:
            image_vals = res.prepare_common_image_vals(vals)
            self.env["common.product.image.ept"].create(image_vals)
        return res

    def write(self, vals):
      
        res = super(ProductProduct, self).write(vals)
        if vals.get("image_1920", False) and self:
            common_product_image_obj = self.env["common.product.image.ept"]
            for record in self:
                if vals.get("image_1920"):
                    image_vals = record.prepare_common_image_vals(vals)
                    common_product_image_obj.create(image_vals)

        return res

    def get_products_based_on_movement_date_ept(self, from_datetime, company):
        
        if not from_datetime or not company:
            raise UserError(_('You must provide the From Date and Company'))
        result = []
        mrp_module = self.search_installed_module_ept('mrp')
        date = str(datetime.strftime(from_datetime, '%Y-%m-%d %H:%M:%S'))

        if mrp_module:
            result = self.get_product_movement_of_bom_product(date, company)

        # qry = ("""select product_id from stock_move where date >= '%s' and company_id = %d and
        #          state in ('partially_available','assigned','done')""" % (date, company.id))

        # Updated the query with the condition with is_update_shopify_qty to avoid the duplicate queue creation.
        qry = ("""select sm.product_id from stock_move sm join product_product pp on pp.id=sm.product_id 
                where sm.date >= '%s' and sm.company_id = %d and sm.state in ('partially_available','assigned','done') 
                and pp.is_update_shopify_qty=True;""" % (date, company.id))
        self._cr.execute(qry)
        result += self._cr.dictfetchall()
        product_ids = [product_id.get('product_id') for product_id in result]

        return list(set(product_ids))

    def search_installed_module_ept(self, module_name):
       
        module_obj = self.env['ir.module.module']
        module = module_obj.sudo().search([('name', '=', module_name), ('state', '=', 'installed')])
        return module

    def get_product_movement_of_bom_product(self, date, company):
       
        mrp_qry = ("""select p.id as product_id from product_product as p
                    inner join mrp_bom as mb on mb.product_tmpl_id=p.product_tmpl_id
                    inner join mrp_bom_line as ml on ml.bom_id=mb.id
                    inner join stock_move as sm on sm.product_id=ml.product_id
                    where sm.date >= '%s' and sm.company_id = %d and sm.state in 
                    ('partially_available','assigned','done')""" % (date, company.id))
        self._cr.execute(mrp_qry)
        result = self._cr.dictfetchall()
        return result

    def prepare_location_and_product_ids(self, warehouse, product_list):
        
        locations = self.env['stock.location'].search([('location_id', 'child_of', warehouse.lot_stock_id.ids)])
        location_ids = ','.join(str(e) for e in locations.ids)
        product_ids = ','.join(str(e) for e in product_list)
        return location_ids, product_ids

    def check_for_bom_products(self, product_ids):
        
        bom_product_ids = []
        mrp_module = self.search_installed_module_ept('mrp')
        if mrp_module:
            qry = ("""select p.id as product_id from product_product as p
                        inner join mrp_bom as mb on mb.product_tmpl_id=p.product_tmpl_id
                        and p.id in (%s)""" % product_ids)
            self._cr.execute(qry)
            bom_product_ids = self._cr.dictfetchall()
            bom_product_ids = [product_id.get('product_id') for product_id in bom_product_ids]

        return bom_product_ids

    def prepare_free_qty_query(self, location_ids, simple_product_list_ids):
        
        query = """select pp.id as product_id,
                COALESCE(sum(sq.quantity)-sum(sq.reserved_quantity),0) as stock
                from product_product pp
                left join stock_quant sq on pp.id = sq.product_id and sq.location_id in (%s)
                where pp.id in (%s) group by pp.id;""" % (location_ids, simple_product_list_ids)
        return query

    def prepare_forecasted_qty_query(self, location_ids, simple_product_list_ids):
        
        query = ("""select product_id,sum(stock) as stock from (select pp.id as product_id,
                COALESCE(sum(sq.quantity)-sum(sq.reserved_quantity),0) as stock
                from product_product pp
                left join stock_quant sq on pp.id = sq.product_id and sq.location_id in (%s)
                where pp.id in (%s) group by pp.id
                union all
                select product_id as product_id, sum(product_qty) as stock from stock_move
                where state in ('assigned') and product_id in (%s) and location_dest_id in (%s)
                group by product_id) as test group by test.product_id""" % (location_ids, simple_product_list_ids,
                                                                            simple_product_list_ids, location_ids))
        return query

    def get_free_qty_ept(self, warehouse, product_list):
        
        qty_on_hand = {}
        location_ids, product_ids = self.prepare_location_and_product_ids(warehouse, product_list)

        bom_product_ids = self.check_for_bom_products(product_ids)
        if bom_product_ids:
            bom_products = self.with_context(warehouse=warehouse.ids).browse(bom_product_ids)
            for product in bom_products:
                actual_stock = getattr(product, 'free_qty')
                qty_on_hand.update({product.id: actual_stock})

        simple_product_list = list(set(product_list) - set(bom_product_ids))
        simple_product_list_ids = ','.join(str(e) for e in simple_product_list)
        if simple_product_list_ids:
            qry = self.prepare_free_qty_query(location_ids, simple_product_list_ids)
            self._cr.execute(qry)
            result = self._cr.dictfetchall()
            for i in result:
                qty_on_hand.update({i.get('product_id'): i.get('stock')})
        return qty_on_hand

    def get_forecasted_qty_ept(self, warehouse, product_list):
        
        forcasted_qty = {}
        location_ids, product_ids = self.prepare_location_and_product_ids(warehouse, product_list)

        bom_product_ids = self.check_for_bom_products(product_ids)
        if bom_product_ids:
            bom_products = self.with_context(warehouse=warehouse.ids).browse(bom_product_ids)
            for product in bom_products:
                actual_stock = getattr(product, 'free_qty') + getattr(product, 'incoming_qty')
                forcasted_qty.update({product.id: actual_stock})

        simple_product_list = list(set(product_list) - set(bom_product_ids))
        simple_product_list_ids = ','.join(str(e) for e in simple_product_list)
        if simple_product_list_ids:
            qry = self.prepare_forecasted_qty_query(location_ids, simple_product_list_ids)
            self._cr.execute(qry)
            result = self._cr.dictfetchall()
            for i in result:
                forcasted_qty.update({i.get('product_id'): i.get('stock')})
        return forcasted_qty
