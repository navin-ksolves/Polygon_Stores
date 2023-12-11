# -*- coding: utf-8 -*-
from odoo import models, fields


class ZidStateMaster(models.Model):
    _name = 'zid.state.master'
    _description = 'Zid State Master'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    zid_state_id = fields.Char('Zid State Id')
    name= fields.Char('Name')
    odoo_state = fields.Many2one('res.country.state', string='Odoo State')
    zid_country_id = fields.Many2one('zid.country.master', string='Zid Country')
    odoo_country = fields.Many2one('res.country', string='Odoo Country', related = 'zid_country_id.odoo_country')