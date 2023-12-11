# -*- coding: utf-8 -*-
from odoo import models, fields
from . import common_functions

class ZidRequest(models.Model):
    _name = 'zid.request'
    _description = 'Zid Request'
    _rec_name = 'store_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    app_id = fields.Many2one('zid.app', string="Zid App")
    store_id = fields.Char(string="Store Id", tracking=True)
    store_url = fields.Char(string="Store Url", tracking=True)
    event = fields.Char(string="Event", tracking=True)
    merchant_email = fields.Char(string="Merchant Email", tracking=True)
    merchant_phone = fields.Char(string="Merchant Phone", tracking=True)
    is_processed = fields.Boolean(string="Processed", default=True, tracking=True)
    note = fields.Text(string="Note")
    has_multi_product_inventory = fields.Boolean('Multi-Inventory')
    
    def continue_process(self):
        polygon_client_user = self.env['polygon.client.users'].search([('email', '=', self.merchant_email)])
        zid_token = self.env['zid.tokens'].search([('zid_request_id','=', self.id)])
        if polygon_client_user:
            self.write({'is_processed': True})
            # create instance for the processed self
            created_instance = self.create_zid_instance(polygon_client_user, zid_token)
            zid_token.write({'zid_instance_id': created_instance.id})

    def create_zid_instance(self, polygon_client_user, zid_token):
        """
        Function to create zid instance
        :param polygon_client_user: polygon client user present in Odoo
        :return:
        """
        polygon_client = polygon_client_user.client_id.id
        polygon_connector = self.env['polygon.connector.clients'].sudo().search(
            [('client_id', '=', polygon_client_user.client_id.id)])
        polygon_instance = self.env['polygon.instance'].sudo().search([('connector_id', '=', polygon_connector.id)])
        warehouse_id = self.env['stock.warehouse'].sudo().search([('company_id', '=', self.env.company.id)], limit=1)
        company_id = self.env.company.id
        data_for_instance = {
            'name': polygon_client_user['name'],
            'polygon_instance_id': polygon_instance.id if polygon_instance else False,
            'polygon_connector_id': polygon_connector.id if polygon_connector else False,
            'polygon_client_id': polygon_client if polygon_client else False,
            'owner_id': polygon_client_user['user_id']['partner_id'].id,
            'company_id': company_id,
            'warehouse_id': warehouse_id.id,
            'access_token': zid_token['access_token'],
            'store_id': self.store_id,
            'has_multi_inventory' : self.has_multi_product_inventory
        }

        data_for_instance['owner_id'] = polygon_instance.connector_id.client_id.partner_id.id
        primary_user = self.env['polygon.client.users'].sudo().search(
            [('client_id', '=', polygon_instance.connector_id.client_id.id), ('is_primary', '=', True)]).user_id

        data_for_instance['default_user'] = primary_user.id
        data_for_instance['sales_team_id'] = primary_user.partner_id.team_id.id
        # Create the product price list:
        pricelist_id = self.env['product.pricelist'].sudo().create({'name': data_for_instance['name'] + ' Pricelist',
                                                             'company_id': data_for_instance['company_id'],
                                                             'currency_id': self.env.company.currency_id.id,
                                                             'polygon_instance_id': polygon_instance.id,
                                                             'client_id': data_for_instance['polygon_client_id'],
                                                             'sales_team_id': data_for_instance['sales_team_id']
                                                             })

        data_for_instance['pricelist_id'] = pricelist_id.id
        # instace creation
        new_instance = self.env['zid.instance.ept'].sudo().create(data_for_instance)
        # logs creation
        common_functions.create_log_in_scheduler(self, new_instance,
                                     create_log_for = ['store_locations', 'product_attributes','category','product'])
        return new_instance
