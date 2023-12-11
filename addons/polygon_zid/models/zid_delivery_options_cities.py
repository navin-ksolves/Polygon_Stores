# -*- coding: utf-8 -*-
from odoo import models, fields


class ZidDeliveryOptionsCities(models.Model):
    _name = 'zid.delivery.options.cities'
    _description = 'Contains zid delivery options cities'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    # _rec_name =

    zid_instance_id = fields.Many2one('zid.instance.ept', string="Instance", tracking=True, required=True, index=True)
    zid_country_master = fields.Many2one('zid.country.master',string="Zid Country Master")
    zid_state_master = fields.Many2one('zid.state.master',string="Zid State Master")
    odoo_country = fields.Many2one('res.country', string="Odoo Country", related = 'zid_country_master.odoo_country')
    odoo_state = fields.Many2one('res.country.state', string="Odoo State", related = 'zid_state_master.odoo_state')
    zid_delivery_option_id = fields.Many2one('zid.delivery.options', string="Zid Delivery Option")
    zid_country_id = fields.Integer('Zid Country Id')
    zid_country_name = fields.Char('Zid Country Name')
    zid_state_id = fields.Integer('Zid State Id')
    zid_state_name = fields.Char('Zid State Name')


