from odoo import models, fields, api
from odoo.exceptions import ValidationError

import logging
import datetime

_logger = logging.getLogger("Polygon Client Contracts")

class PolygonClientContracts(models.Model):
    _name = 'polygon.client.contracts'
    _description = 'Polygon Client Contracts'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    @api.model
    def _find_tc_id(self):
        tc = self.env['polygon.client.terms'].search([('company_id', '=', self.env.user.company_id.id), ('active', '=', True)], limit=1)

        return tc.id if tc else False

    name = fields.Char(string='Contract Name', required=True, copy=False, index=True)
    client_id = fields.Many2one('polygon.client.company', string='Client', readonly=True, copy=False)
    contract_start = fields.Date(string='Contract Start Date', required=True, copy=False, default=fields.Date.today)
    contract_end = fields.Date(string='Contract End Date', required=True, copy=False)
    tc_id = fields.Many2one('polygon.client.terms', string='Terms and Conditions', readonly=True, default=_find_tc_id, copy=False, required=True)
    tc_agreed = fields.Boolean(string='Terms and Conditions Agreed', default=False, copy=False)
    active = fields.Boolean(string='Active', default=True, copy=False)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, copy=False, required=True, 
                                  default=lambda self: self.env.company.currency_id.id)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', readonly=True, copy=False, required=False, 
                                   default=lambda self: self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], limit=1).id)
    attachments = fields.Many2many('ir.attachment', string='Contract Copy', copy=False, required=False)

    def _compute_attached_docs_count(self):
        attachment = self.env['ir.attachment']
        self.doc_count = attachment.search_count(
        [('res_model', '=', 'polygon.client.contracts'), ('res_id', '=', self.id)])

    doc_count = fields.Integer(compute=_compute_attached_docs_count, string="Number of documents attached")

    # Check if an active client contract exists for the client
    @api.constrains('client_id')
    def _check_client_contract(self):
        for contract in self:
            if contract.client_id.contract_id and contract.client_id.contract_id.active:
                _logger.info("An active contract already exists for this client.")
                raise ValidationError("An active contract already exists for this client.")
            
    @api.onchange('active')
    def _onchange_active(self):
        for record in self:
            if not record.active:
                record.client_id.active = False
    
    @api.model
    def create(self, vals):
        contract = super(PolygonClientContracts, self).create(vals)

        return contract
    
    # Create a cron job to check if the contract has expired
    @api.model
    def check_contract_expiry(self):
        for contract in self:
            if contract.contract_end < datetime.date.today():
                contract.active = False
            else:
                contract.active = True

    @api.model
    def check_contract_start(self):
        for contract in self:
            if contract.contract_start > datetime.date.today():
                contract.active = False
            else:
                contract.active = True

    @api.model
    def check_tc_agreed(self):
        for contract in self:
            if contract.tc_agreed == False:
                contract.active = False

    @api.onchange('active')
    def on_change(self):
        for contract in self:
            if not contract.active:
                contract.client_id.contract_id = None
                contract.client_id.active = False
            elif contract.active:
                contract.client_id.active = True
                contract.client_id.contract_id = contract.id

    # At end of month, calculate number of days in the month and calculate the charges for the month
    @api.model
    def calculate_charges(self):
        for contract in self:

            if contract.active:
                if contract.contract_end > datetime.date.today():
                    if contract.contract_start < datetime.date.today():
                        # Calculate the number of days in the month
                        today = datetime.date.today()
                        first_day = today.replace(day=1)
                        last_day = first_day.replace(month=first_day.month+1) - datetime.timedelta(days=1)
                        number_of_days = last_day.day

                        # Create a sale order for the client
                        so = self.evn['sale.order'].create({'partner_id': contract.client_id.partner_id.id, 'company_id': contract.client_id.company_id.id, 
                                                            'currency_id': contract.currency_id.id, 'owner_id': contract.client_id.company_id.id, 'state': 'draft',
                                                            'user_id': contract.client_id.polygon_sales_id.id, 'origin': 'Automation', 'client_order_ref': contract.name})
                                                            

                        for line in contract.contract_line_ids:
                            if line.rate_type == 'fixed':
                                if line.charge_basis == 'per_day':
                                    # Create a sale order line
                                    so_line = self.env['sale.order.line'].create({'order_id': so.id, 'product_id': line.product_id.odoo_product_id.id, 
                                                                                'product_uom_qty': number_of_days, 'price_unit': line.rate})
                                elif line.charge_basis == 'per_month':
                                    line.charge = (line.rate/30)
                                    # Create a sale order line
                                    so_line = self.env['sale.order.line'].create({'order_id': so.id, 'product_id': line.product_id.odoo_product_id.id,
                                                                                'product_uom_qty': number_of_days, 'price_unit': line.charge})
                                    
                                elif line.charge_basis == 'per_year':
                                    line.charge = (line.rate/365)
                                    # Create a sale order line
                                    so_line = self.env['sale.order.line'].create({'order_id': so.id, 'product_id': line.product_id.odoo_product_id.id,
                                                                                'product_uom_qty': number_of_days, 'price_unit': line.charge})

                            elif line.rate_type == 'variable':
                                if line.charge_basis == 'per_order':
                                    # Get the number of orders for the month
                                    sales_orders = self.env['sale.order'].search([('date_order', '>=', contract.contract_start), ('date_order', '<=', last_day), 
                                                                                  ('state', '=', 'done'), ('billed_id', '=', None), ('owner_id', '=', contract.client_id.id)])
                                    
                                    for sale in sales_orders:
                                        orders_count = 0
                                        if sale.state_id == line.state_id:
                                            orders_count += 1

                                        # Create a sale order line
                                        so_line = self.env['sale.order.line'].create({'order_id': so.id, 'product_id': line.product_id.odoo_product_id.id,
                                                                                    'product_uom_qty': orders_count, 'price_unit': line.rate})
                                        # Update the billed_id in the sale order
                                        sale.billed_id = so.id

                        # If SO lines exist, confirm the SO
                        if so.order_line:
                            so.action_confirm()                                        

    @api.constrains('contract_start', 'contract_end')
    def _check_contract_dates(self):
        for contract in self:
            if contract.contract_start > contract.contract_end:
                raise ValidationError("Contract start date cannot be greater than contract end date.")

    def attachment_tree_view(self):
        domain = ['&', ('res_model', '=', 'polygon.client.contracts'), ('res_id', 'in', self.ids)]
        res_id = self.ids and self.ids[0] or False

        return {
            'name': _('attachments'),
            'domain': domain,
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'kanban,tree,form',
            'view_type': 'form',
            'limit': 5,
            'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, res_id)
        }