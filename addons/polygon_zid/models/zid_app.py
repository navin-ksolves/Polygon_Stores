# -*- coding: utf-8 -*-
from odoo import models, fields, api

import requests
import time

class ZidApp(models.Model):
    _name = 'zid.app'
    _description = 'Zid App'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _rec_name = 'app_name'

    app_name = fields.Char(string="App Name", required=True, copy=False, readonly=False)
    zid_client_id = fields.Char(string="Client ID Zid Portal", required=False, copy=False, readonly=False, index=True, unique=True)
    zid_client_secret = fields.Char(string="Client Secret Zid Portal", required=False, copy=False, readonly=False, index=True, unique=True)
    zid_oauth_endpoint = fields.Char(string="OAuth Endpoint", required=True, copy=False, readonly=False)
    access_token = fields.Char(string="Access Token", required=False, copy=False, readonly=True)
    token_type = fields.Char(string="Token Type", required=False, copy=False, readonly=True)
    expires_in = fields.Integer(string="Expires In", required=False, copy=False, readonly=True)
    authorization = fields.Char(string="Authorization", required=False, copy=False, readonly=True)
    refresh_token = fields.Char(string="Refresh Token", required=False, copy=False, readonly=True)
    base_api_url = fields.Char(string="Base API URL", copy=False, readonly=False)
    redirect_url = fields.Char(string='Redirect URL', required=True, copy=False, index=True, tracking=True)
    callback_url = fields.Char(string='Callback URL', required=True, copy=False, index=True, tracking=True)
    active = fields.Boolean(string='Active', default=True, copy=False, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company)

    _sql_constraints = [('unique_zid_id', 'unique(zid_client_id)',
                         "Client ID already exists. This must be unique!"),
                         ('unique_zid_secret', 'unique(zid_client_secret)',
                         "Zid Secret already exists. This must be unique!")]
    country_ids = fields.Many2many('zid.country.master', string='Zid Countries')

    @api.model
    def refresh_token(self, vals_list):
        for val in vals_list:

            # datetime now in unix:
            now = time.time()

            # datetime expires_in in unix:
            expires_in = float(val.expires_in)
            
            if now > expires_in:

                token_url = val.zid_oauth_endpoint + '/oauth/token'
                payload = {
                    'grant_type': 'authorization_code',
                    'client_id': val.zid_client_id,
                    'client_secret': val.zid_client_secret,
                    'redirect_uri': self.env['ir.config_parameter'].sudo().get_param('web.base.url') + '/zid/uae/callback',
                    'code': self.args.get('code')
                }

                response = requests.post(token_url, data=payload)
                response_json = response.json()

                val.write({
                    'access_token': response_json['access_token'],
                    'token_type': response_json['token_type'],
                    'expires_in': response_json['expires_in'],
                    'authorization': response_json['authorization'],
                    'refresh_token': response_json['refresh_token']
                })
