# -*- coding: utf-8 -*-
from odoo import models, fields


class ZidUser(models.Model):
    _name = 'zid.user'
    _description = 'Zid User'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", tracking=True)
    zid_user_id = fields.Integer(string="User Id", tracking=True)
    uuid = fields.Char(string="UUId", tracking=True)
    username = fields.Char(string="User Name", tracking=True)
    email = fields.Char(string="Email", tracking=True)
    mobile = fields.Char(string="Mobile", tracking=True)
