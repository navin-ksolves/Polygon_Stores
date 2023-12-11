# -*- coding: utf-8 -*-
from odoo import models, fields
import json
import ast
from . import common_functions
import logging

_logger = logging.getLogger(__name__)

class ZidSchedulerState(models.Model):
    _name = 'zid.scheduler.currency'
    _description = 'Zid Scheduler Currency'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    status = fields.Selection([('draft', 'Draft'), ('progress', 'In Progess'), ('done', 'Done'), ('failed', 'Failed')],
                              string="Status", tracking=True, default='draft', readonly=True)
    data = fields.Text(string="Json Data", readonly=True)
    currency_master_id = fields.Many2one('zid.currency.master', string='Currency Master', readonly=True)
    scheduler_log_id = fields.Many2one('zid.scheduler.log.line', string="Scheduler Log", readonly=True)

    def create_currency_master_records(self):
        """
       Function to create record in zid currency master if state not present
       :return:
       """
        _logger.info("Creating Currency Records In Master Data")
        draft_states = self.search([('status', '=', 'draft')])
        currency_objs = self.env['zid.currency.master']

        for currency in draft_states:
            try:
                currency.status = 'progress'
                input_string = currency['data']
                curr = ast.literal_eval(input_string)

                currency_master = currency_objs.search([('zid_id', '=', curr['id'])])

                if not currency_master:
                    data_for_currency_master = {
                        'zid_id': curr['id'],
                        'name': curr['name'],
                        'code': curr['code']
                    }
                    currency_master = currency_objs.create(data_for_currency_master)

                if currency_master:
                    currency.currency_master_id = currency_master.id
                    currency.status = 'done'
                    currency.scheduler_log_id.completed_lines += 1
                    _logger.info(f"Currency creation for currency with Zid Id {curr['id']} successfull!!")
                else:
                    currency.status = 'failed'
            except Exception as e:
                _logger.error(str(e))
                _logger.error(f"Currency creation for currency with Zid Id {curr['id']} failed!!")
            common_functions.update_scheduler_log_state(currency.scheduler_log_id)