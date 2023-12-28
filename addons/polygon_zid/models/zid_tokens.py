# -*- coding: utf-8 -*-
import datetime
import requests
from odoo import models, fields
import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class ZidTokens(models.Model):
    _name = 'zid.tokens'
    _description = 'Zid Tokens'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    access_token = fields.Char(string="Access Token", tracking=True)
    token_type = fields.Char(string="Token Type", tracking=True)
    expires_in = fields.Char(string="Expires In", tracking=True)
    authorization = fields.Char(string="Authorization", tracking=True)
    refresh_token = fields.Char(string="Refresh Token", tracking=True)
    zid_request_id = fields.Many2one('zid.request', string="Zid Request")
    zid_instance_id = fields.Many2one('zid.instance.ept', string="Zid Instance", tracking=True)
    token_expire_date = fields.Date('Expires On', default=lambda self: fields.Datetime.now()+relativedelta(months=5))
    active = fields.Boolean(string='Active', default=True, copy=False)

    def refresh_tokens(self):
        """
        Cron function to refresh expired tokens
        :return:
        """
        tokens_to_refersh = self.search([('token_expire_date','=', datetime.datetime.now())])
        for token in tokens_to_refersh:

            # Zid API endpoint for token generation
            token_endpoint = "https://oauth.zid.sa/oauth/token"

            zid_app = token.zid_request_id.app_id
            # Your client credentials
            client_id = zid_app.zid_client_id
            client_secret = zid_app.zid_client_secret
            refresh_token = token['refresh_token']
            # Request parameters
            data = {
                'grant_type': 'refresh_token',
                'client_id': client_id,
                'client_secret': client_secret,
                'refresh_token': refresh_token
            }

            # Make a POST request to the token endpoint
            try:
                response = requests.post(token_endpoint, data=data)

                # Check if the request was successful (status code 200)
                if response.status_code == 200:
                    # Parse the JSON response
                    old_access_token = token['access_token']
                    response_json = response.json()
                    # Access the refresh token
                    token.write({
                        'access_token': response_json['access_token'],
                        'token_type': response_json['token_type'],
                        'expires_in': response_json['expires_in'],
                        'authorization': response_json['authorization'],
                        'refresh_token': response_json['refresh_token'],
                        'token_expire_date': datetime.datetime.now()+relativedelta(months=5)
                    })
                    self.update_related_instance(old_access_token,response_json['access_token'])
            except Exception as e:
                print(f"Error: {response.status_code}, {response.text}")
                _logger.error(str(e))
                _logger.error(f"The attempt to refresh the token with the ID {refresh_token['id']} has failed.")


    def update_related_instance(self,old_access_token, new_access_token):
        """
        Helper function to update access token of the in instance
        """
        linked_instances = self.env['zid.instance.ept'].search([('access_token','=',old_access_token),('active','in',[True, False])])
        for linked_instance in linked_instances:
            linked_instance.write({'access_token': new_access_token})



