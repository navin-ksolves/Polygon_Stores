# -*- coding: utf-8 -*-

from odoo import models, fields
from . import common_functions
import  requests, json

class ZidCurrency(models.Model):
    _name = 'zid.currency.master'
    _description = 'Zid Currencies'
    _rec_name = 'code'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    zid_id = fields.Integer('Zid Id')
    name = fields.Char('Name')
    code = fields.Char('Code')
    odoo_currency = fields.Many2one('res.currency', string='Odoo Currency')

    def create_currency_sync_log(self):
        """
        function to create sync log for currency in scheduler for each instance
        :return:
        """
        instances = self.env['zid.instance.ept'].search([])
        for instance in instances:
            common_functions.create_log_in_scheduler(self, instance, create_log_for=['currency'])
