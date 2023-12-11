# -*- coding: utf-8 -*-
from odoo import models, fields


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
    active = fields.Boolean(string='Active', default=True, copy=False)
