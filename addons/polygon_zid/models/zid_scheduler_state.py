# -*- coding: utf-8 -*-
from odoo import models, fields
import ast
from . import common_functions
import logging

_logger = logging.getLogger(__name__)

class ZidSchedulerState(models.Model):
    _name = 'zid.scheduler.state'
    _description = 'Zid Scheduler State'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    status = fields.Selection([('draft', 'Draft'), ('progress', 'In Progess'), ('done', 'Done'), ('failed', 'Failed')],
                              string="Status", tracking=True, default='draft', readonly=True)
    data = fields.Text(string="Json Data", readonly=True)
    state_master_id = fields.Many2one('zid.state.master', string='State Master', readonly=True)
    scheduler_log_id = fields.Many2one('zid.scheduler.log.line', string="Scheduler Log", readonly=True)
    attempts = fields.Integer("Scheduler Attempts")


    def create_record_in_zid_state_master(self, args = {}):
        """
        Function to create record in zid state master if state not present
        :return:
        """
        record_limit = args.get('limit')
        draft_states = self.search(['|', '&', ('status','=','failed'),('attempts','<', 3),('status', '=', 'draft')], limit = record_limit)
        state_objs = self.env['zid.state.master']

        for state in draft_states:
            try:
                _logger.info("Creating Zid State Record")
                state.status = 'progress'
                state.attempts += 1
                input_string = state['data']
                city = ast.literal_eval(input_string)

                zid_country_id = self.env['zid.country.master'].search([('zid_country_id', '=', city['country_id'])])
                state_master = state_objs.search([('zid_state_id', '=', city['id'])])

                if not state_master:
                    data_for_state_master = {
                        'zid_state_id': city['id'],
                        'name': city['en_name'],
                        'zid_country_id': zid_country_id.id
                    }
                    state_master = state_objs.create(data_for_state_master)

                if state_master:
                    state.state_master_id = state_master.id
                    state.status = 'done'
                    state.scheduler_log_id.completed_lines += 1
                    common_functions.update_scheduler_log_state(state.scheduler_log_id)
                    common_functions.update_log_line_attempts(self, 'zid.scheduler.state', state.scheduler_log_id, 'scheduler_log_id')
            except Exception as e:
                state.status = 'failed'
                common_functions.update_log_line_attempts(self, 'zid.scheduler.state', state.scheduler_log_id,
                                                          'scheduler_log_id')
                _logger.error(str(e))

