from odoo import models, fields, api
from odoo.exceptions import ValidationError

import logging
import datetime

_logger = logging.getLogger("Polygon Client Contract Line")

class PolygonClientContractsLine(models.Model):
    _name = 'polygon.client.contracts.line'
    _description = 'Polygon Client Contracts Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Contract Line Name', required=True, copy=False, index=True)
    contract_id = fields.Many2one('polygon.client.contracts', string='Contract', readonly=True, copy=False)
    product_id = fields.Many2one('polygon.client.products', string='Product', readonly=True, copy=False)
    rate_type = fields.Selection([('fixed', 'Fixed'),
                                  ('variable', 'Variable')
                                 ], string='Rate Type', default='fixed')
    charge_basis = fields.Selection([('per_order', 'Per Order'),
                                     ('per_day', 'Per Day'),
                                     ('per_month', 'Per Month'),
                                     ('per_year', 'Per Year')
                                    ], string='Charge Basis', default='per_order')
    rate = fields.Float(string='Rate', required=True, copy=False)
    country_id = fields.Many2one('res.country', string='Country', readonly=True, copy=False, required=True, default=lambda self: self.env.company.country_id.id)
    state_id = fields.Many2one('res.country.state', string='State', readonly=True, copy=False, required=True, domain="[('country_id', '=', country_id)]")

    # Check if rate is greater than 0
    @api.constrains('rate')
    def _check_rate(self):
        for line in self:
            if line.rate <= 0:
                raise ValidationError("Rate must be greater than 0.")


    # Check if rate type and charge basis are compatible
    @api.constrains('rate_type', 'charge_basis')
    def _check_rate_type(self):
        for line in self:
            if line.rate_type == 'fixed' and line.charge_basis == 'per_order':
                raise ValidationError("Fixed rate cannot be per order.")
            elif line.rate_type == 'variable' and line.charge_basis == 'per_order':
                raise ValidationError("Variable rate cannot be per order.")
            elif line.rate_type == 'variable' and line.charge_basis == 'per_day':
                raise ValidationError("Variable rate cannot be per day.")
            elif line.rate_type == 'variable' and line.charge_basis == 'per_year':
                raise ValidationError("Variable rate cannot be per year.")
            
    @api.constrains('product_id')
    def _check_product_type(self):
        for line in self:
            if line.rate_type != 'fixed' and line.product_id.product_type == 'filfillment':
                raise ValidationError("filfillment products cannot have variable rates.")

    @api.model
    def create(self, vals):
        contract_line = super(PolygonClientContractsLine, self).create(vals)

        return contract_line