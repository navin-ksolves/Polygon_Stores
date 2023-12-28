# -*- coding: utf-8 -*-
import datetime

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
        draft_schedulers_log = self.search([('status', '=', 'progress')])
        for scheduler_log in draft_schedulers_log:
            all_done = all(log_line.status == 'done' for log_line in scheduler_log.log_line_ids)
            if all_done:
                scheduler_log.write({'status': 'done'})

    def check_log_lines(self):
        """Check if any log lines are in progress or failed &
        update scheduler status"""
        draft_schedulers_log = self.search([('status', '!=', 'done')])
        for scheduler_log in draft_schedulers_log:
            any_failed = any(log_line.status == 'failed' for log_line in scheduler_log.log_line_ids)
            any_progress = any(log_line.status == 'progress' for log_line in scheduler_log.log_line_ids)
            if any_progress:
                scheduler_log.write({'status': 'progress'})
            elif any_failed:
                scheduler_log.write({'status': 'failed'})

    def run_queue(self, args={}):
        """
        Function to process tasks present in the log
        """
        record_limit = args.get('limit')
        scheduler_id = self.search([('date', '=', datetime.datetime.now())])
        scheduler_id = self.search([('id', '=', 147)]) #TODO: remove
        tasks = self.env['zid.scheduler.log.line'].search([('status', '=', 'draft'),
                                                           ('scheduler_log_id', '=', scheduler_id.id)], limit=record_limit)

        for task in tasks:
            is_task_failed = task.is_task_failed(task)
            if is_task_failed:
                continue

            task.status = 'progress'

            if task.scheduler_type == "sync_states":
                task.sync_states(task)

            # For processing currency
            elif task.scheduler_type == "currency":
                task.create_zid_currency(task)

            # code to update product quantity
            elif task.scheduler_type == "update_product_quant":
                task.update_product_qty(task)

            elif task.scheduler_type == "product_attributes":
                task.create_product_attributes(task)

            # For syncing delivery option country and states
            elif task.scheduler_type == 'sync_do_countries_states':
                is_successful = task.create_zid_country_master(task)
                task.status = 'done' if is_successful else 'draft'

            # For syncing store locations
            elif task.scheduler_type == 'store_locations':
                task.create_store_location_scheduler(task)

            elif task.scheduler_type == "product":
                task.sync_products(task)

            elif task.scheduler_type == "category":
                task.sync_product_category(task)

            elif task.scheduler_type == "order":
                task.sync_orders(task)

            elif task.scheduler_type == "webhook":
                task.manage_webhooks(task)
