from odoo import models, fields, api
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger("Polygon Client Terms and Conditions")


class PolygonTermsAndConditions(models.Model):
    _name = 'polygon.client.terms'
    _description = 'Polygon Client Terms and Conditions'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Terms and Conditions Name', required=True, copy=False, index=True, tracking=True)
    terms = fields.Html(string='Terms and Conditions', required=True, copy=False)
    active = fields.Boolean(string='Active', default=True, copy=False, tracking=True)
    version = fields.Float(string='Version', required=True, copy=False, default=1.0, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True, copy=False, required=True,
                                 default=lambda self: self.env.company.id, tracking=True)

    @api.model
    def create(self, vals):
        if vals['active'] is True and self.env['polygon.client.terms'].search_count([
            ('active', '=', True),
            ('company_id', '=', self.env.company.id),  # Exclude the current record
        ]):
            _logger.warning("A T&C is already active for this company.")
            raise ValidationError("A T&C is already active for this company.")
        else:
            # Get the company id of the user trying to create the client
            company_id = self.env.user.company_id.id
            vals['company_id'] = company_id

            # Create terms
            terms = super(PolygonTermsAndConditions, self).create(vals)

            return terms
    #
    # @api.model
    # def write(self, vals):
    #     if vals['active'] is True and self.env['polygon.client.terms'].search_count([
    #         ('active', '=', True),
    #         ('company_id', '=', self.env.company.id),  # Exclude the current record
    #     ]):
    #         _logger.warning("A T&C is already active for this company.")
    #         raise ValidationError("A T&C is already active for this company.")
    #     else:
    #         # Get the company id of the user trying to create the client
    #         company_id = self.env.user.company_id.id
    #         vals['company_id'] = company_id
    #
    #         # Create terms
    #         terms = super().write('name':vals['name'],
    #         'terms':vals['terms'],
    #         'active':vals['active'],
    #         'version':vals['version'])
    #
    #
    #         return terms
