# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AccountBankStatement(models.Model):
  
    _inherit = 'account.bank.statement'

    shopify_payout_ref = fields.Char(string='Shopify Payout Reference')
