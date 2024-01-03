# -*- coding: utf-8 -*-

from odoo.http import Response
from urllib.parse import urlencode
import requests
from werkzeug.utils import redirect
from ..models import common_functions
from odoo import http
from odoo.exceptions import UserError
from odoo.http import request
from datetime import datetime
import logging

utc_time = datetime.utcnow()
_logger = logging.getLogger(__name__)
from ...delivery_partner_integration.controllers.controller import DeliveryCarrier


class InheritDeliveryCarrier(DeliveryCarrier):
    @http.route('/order/update/status', type="json", auth="public", methods=['POST'], cors="*")
    def order_update_status(self):
        post_data = request.get_json_data()
        _logger.info("POST DATA===>>>>>>>>>>>>>>>>>>>{}".format(post_data))
        _logger.info("SESSION===>>>>>>>>>>>>>>{}".format(request.session))
        if post_data.get('order_number'):
            if '#' in post_data.get('order_number'):
                order = (post_data.get('order_number').split('#'))[0]
            elif '.' in post_data.get('order_number'):
                order = (post_data.get('order_number').split('.'))[0]
            else:
                order = post_data.get('order_number')
            # user_id = request.env['res.users'].sudo().search([('id','=',2)])
            # _logger.info("COMPANY IDS++++====>>>>>>>>>>{}".format(user_id.company_ids.ids))
            sale_order = request.env['sale.order'].sudo().search([('name', '=ilike', order)])
            if sale_order:
                _logger.info("ORDER===>>>>>>>>>>>>>>>>{}".format(order))

                picking_id = request.env['stock.picking'].sudo().search(
                    [('sale_id', '=', sale_order.id), ('state', 'not in', ['done', 'cancel'])])
                _logger.info("PICKING ID====>>>>>>>>>>>>>>{}".format(picking_id))

        if post_data.get('status') in ['attempted', 'cancelled'] and picking_id.state not in ['done', 'cancel'] and picking_id.attempt >= 3:
            if picking_id.state not in ['done', 'cancel']:
                if picking_id.attempt >= 3:
                    common_functions.update_zid_order_status_based_on_picking(request,sale_order, picking_id,
                                                                              picking_cancelled=True)
                    return super(InheritDeliveryCarrier, self).order_update_status()
        # Updating order status in zid
        else:
            res = super(InheritDeliveryCarrier, self).order_update_status()
            common_functions.update_zid_order_status_based_on_picking(request,sale_order, picking_id, tracking_url= post_data.get('tracking_url'))
            return res


class Main(http.Controller):

    @http.route(['/zid/product', '/zid/order', '/zid/activation'], type='json', auth='none', methods=['POST'], csrf=False)
    def zid_webhook(self, **kwargs):
        """
        Function to create log for webhook in scheduler_log_line using the data from webhook
        """
        webhook_event = request.httprequest.environ.get('HTTP_WEBHOOK_EVENT')
        data = request.dispatcher.jsonrequest
        store_id = data.get("store_id")
        zid_store_id = request.env['zid.instance.ept'].search([('store_id', '=', store_id)], limit=1)
        data_for_log = {
            'scheduler_type': 'webhook',
            'instance_id': zid_store_id.id,
            'status': 'draft',
            'attempts': 0,
            'json': {'data': [data]},
            'webhook_type': webhook_event
        }
        request.env['zid.scheduler.log.line'].sudo().create(data_for_log)

    @http.route('/zid/redirect', type='http', auth='none', csrf=False)
    def redirect(self, **kwargs):
        """
        :Use: Redirect from zid when user start activation process
        :Param: client id
        :Return: URL for Authorize
        """
        # Get the client id from the url
        # client_id = http.request.params.get('id')
        client_id = kwargs['client_id']
        client_id_odoo = request.env['zid.app'].search([('zid_client_id', '=', client_id)])
        if not client_id_odoo:
            return redirect('https://www.polygonstores.com/')

        # Check for existing client
        # zid_credentials = request.env['zid.app'].sudo().search([('zid_client_id', '=', client_id)], limit=1)

        params = {
            'client_id': client_id,
            'response_type': 'code'
        }
        query_string = urlencode(params)
        # url = zid_credentials.zid_oauth_endpoint + '/oauth/authorize?' + query_string
        url = 'https://oauth.zid.sa/oauth/authorize'

        return redirect(f'{url}?{query_string}')

    @http.route('/zid/callback', type='http', auth='none')
    def callback(self, **kwargs):
        """
        :Use: Callback from zid when user click on installing application
        :Param: code
        :Return:
        """
        # Get the id from the url
        # client_id = http.request.params.get('id')
        client_id = kwargs['client_id']
        client_secret = request.env['zid.app'].search([('zid_client_id', '=', client_id)])['zid_client_secret']
        app_id = request.env['zid.app'].search([('zid_client_id', '=', client_id)]).id

        # Get the client secret from the database
        # zid_credentials = request.env['zid.app'].sudo().search([('zid_client_id', '=', client_id)], limit=1)

        # Get the authentication token from zid
        # token_url = zid_credentials.zid_oauth_endpoint + '/oauth/token'
        token_url = "https://oauth.zid.sa/oauth/token"

        payload = {
            'grant_type': 'authorization_code',
            'client_id': client_id,
            'client_secret': client_secret,
            'code': kwargs.get('code', '')
        }

        response = requests.post(token_url, data=payload)
        response_json = response.json()
        # Create Zid Token
        zid_token = self.create_zid_token(response_json)
        # Get Manager Profile and Store in Odoo
        self.create_manager_profile(response_json, zid_token, app_id)
        return redirect('https://web.zid.sa/account/settings/shipping-options')

    def create_zid_token(self, response_data):
        """
        :Use: Create new record of zid token
        :Param response_data: dict
        :Return: new created token
        """
        return request.env['zid.tokens'].create({
            'access_token': response_data['access_token'],
            'token_type': response_data['token_type'],
            'expires_in': response_data['expires_in'],
            'authorization': response_data['authorization'],
            'refresh_token': response_data['refresh_token'],
        })

    def create_manager_profile(self, response_data, zid_token, app_id):
        """
        :Use: Get X-Manager Profile from zid
        :Param response_data: dict, zid_token: Browsable record, app_id: id of the app which made request
        :Return: True
        """

        url = "https://api.zid.sa/v1/managers/account/profile"

        headers = {
            "Accept-Language": "",
            "Authorization": 'Bearer ' + response_data['authorization'],
            "X-Manager-Token": response_data['access_token'],
            "User-Agent": "",
            "Accept": "application/json"
        }

        manager_data = requests.get(url, headers=headers)
        store_details = manager_data.json()['user']['store']
        new_zid_request = request.env['zid.request'].create({
            'app_id': app_id,
            'store_id': store_details['id'],
            'store_url': store_details['url'],
            'merchant_email': store_details['email'],
            'merchant_phone': store_details['phone'],
            'has_multi_product_inventory': store_details['has_multi_product_inventory']
        })
        zid_token.write({'zid_request_id': new_zid_request.id})
        user_details = manager_data.json()['user']
        new_zid_user = request.env['zid.user'].create({
            'name': user_details['name'],
            'zid_user_id': user_details['id'],
            'email': user_details['email'],
            'mobile': user_details['mobile'],
            'username': user_details['username'],
            'uuid': user_details['uuid']
        })
        self.process_request(new_zid_user['email'], new_zid_request, zid_token, store_details['id'])

    def process_request(self, zid_user_email, new_zid_request, zid_token, store_id):
        """
        To decide whether to process the request further based on email
        :param zid_user_email: email of the user
        :param new_zid_request: request created in Odoo
        """
        polygon_client_user = request.env['polygon.client.users'].sudo().search([('email', '=', zid_user_email)])
        if polygon_client_user:
            new_zid_request.write({'is_processed': True})
            # create instance for the processed request
            # created_instance = new_zid_request.create_zid_instance(polygon_client_user, zid_token)
            created_instance = self.create_zid_instance(polygon_client_user, zid_token, store_id)
            zid_token.write({'zid_instance_id':created_instance.id})
        else:
            new_zid_request.write({'is_processed': False})

    def create_zid_instance(self, polygon_client_user, zid_token, store_id):
        """
        Function to create zid instance
        :param polygon_client_user: polygon client user present in Odoo
        :return:
        """
        polygon_client = polygon_client_user.client_id.id
        polygon_connector = request.env['polygon.connector.clients'].sudo().search(
            [('client_id', '=', polygon_client_user.client_id.id)])
        polygon_instance = request.env['polygon.instance'].sudo().search([('connector_id', '=', polygon_connector.id)])
        has_multi_product_inventory = zid_token.zid_request_id.has_multi_product_inventory
        # warehouse_id = request.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        data_for_instance = {
            'name': polygon_client_user['name'],
            'polygon_instance_id': polygon_instance.id if polygon_instance else False,
            'polygon_connector_id': polygon_connector.id if polygon_connector else False,
            'polygon_client_id': polygon_client if polygon_client else False,
            'owner_id': polygon_client_user['user_id']['partner_id'].id,
            'company_id': 1,
            'warehouse_id': 1,
            'access_token': zid_token['access_token'],
            'has_multi_inventory':has_multi_product_inventory,
            'store_id': store_id
        }

        data_for_instance['owner_id'] = polygon_instance.connector_id.client_id.partner_id.id
        primary_user = request.env['polygon.client.users'].sudo().search(
            [('client_id', '=', polygon_instance.connector_id.client_id.id), ('is_primary', '=', True)]).user_id

        data_for_instance['default_user'] = primary_user.id
        data_for_instance['sales_team_id'] = primary_user.partner_id.team_id.id
        # Create the product price list:
        # pricelist_id = request.env['product.pricelist'].create({'name': data_for_instance['name'] + ' Pricelist',
        #                                                      'company_id': data_for_instance['company_id'],
        #                                                      'currency_id': self.env.company.currency_id.id,
        #                                                      'polygon_instance_id': polygon_instance.id,
        #                                                      'client_id': data_for_instance['polygon_client_id'],
        #                                                      'sales_team_id': data_for_instance['sales_team_id']
        #                                                      })
        #
        # data_for_instance['pricelist_id'] = pricelist_id.id
        #instace creation
        new_instance = request.env['zid.instance.ept'].sudo().create(data_for_instance)
        create_log_for = ['product', 'category','store_locations','product_attributes']
        common_functions.create_log_in_scheduler(request, new_instance, create_log_for= create_log_for)
        return new_instance
    #
    # def create_log_in_scheduler(self, zid_instance):
    #     """
    #     Function to create log in zid_scheduler
    #     :param zid_instance: zid instance
    #     :return:
    #     """
    #     create_log_for = ['delivery_option', 'currency', 'vat', 'product', 'category','store_locations','product_attributes']
    #     for log in create_log_for:
    #         data_for_log = {
    #             'scheduler_type': log,
    #             'instance_id': zid_instance.id,
    #             'status': 'draft',
    #             'attempts': 0
    #         }
    #         request.env['zid.scheduler.log.line'].sudo().create(data_for_log)
    #     return True
