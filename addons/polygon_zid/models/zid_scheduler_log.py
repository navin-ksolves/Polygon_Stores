# -*- coding: utf-8 -*-
from odoo import models, fields
import requests
import json
import logging
from . import common_functions
import ast

_logger = logging.getLogger(__name__)


class ZidSchedulerLog(models.Model):
    _name = 'zid.scheduler.log'
    _description = 'Zid Scheduler Log'
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    date = fields.Date('Date', default=lambda self: fields.Datetime.now())
    log_line_ids = fields.One2many('zid.scheduler.log.line', 'scheduler_log_id', 'Log')
    status = fields.Selection([('draft', 'Draft'), ('progress', 'In Progess'), ('done', 'Done'), ('failed', 'Failed')],
                              string="Status", tracking=True, default='draft', readonly=True)

    def check_log_lines_done(self):
        """Check if all log lines are done and update scheduler status to done."""
        draft_schedulers_log = self.search([('status','=','progress')])
        for scheduler_log in draft_schedulers_log:
            all_done = all(log_line.status == 'done' for log_line in scheduler_log.log_line_ids)
            if all_done:
                scheduler_log.write({'status': 'done'})

    def check_log_lines(self):
        """Check if any log lines are in progress or failed &
        update scheduler status"""
        draft_schedulers_log = self.search([('status','!=','done')])
        for scheduler_log in draft_schedulers_log:
            any_failed = any(log_line.status == 'failed' for log_line in scheduler_log.log_line_ids)
            any_progress = any(log_line.status == 'progress' for log_line in scheduler_log.log_line_ids)
            if any_progress:
                scheduler_log.write({'status': 'progress'})
            elif any_failed:
                scheduler_log.write({'status': 'failed'})

