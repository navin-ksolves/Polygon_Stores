# -*- coding: utf-8 -*-
from odoo import models, fields
import datetime

class ZidInstance(models.Model):
    _name = 'zid.instance.ept'
    _description = 'Zid Instance EPT'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    store_id = fields.Integer('Store Id')
    polygon_instance_id = fields.Many2one('polygon.instance', string='Polygon Instance', tracking=True)
    polygon_connector_id = fields.Many2one('polygon.connector.clients', string='Polygon Connector', tracking=True)
    polygon_client_id = fields.Many2one('polygon.client.company', string='Polygon Client', tracking=True)
    owner_id = fields.Many2one('res.partner', string="Owner", required=True, tracking=True)
    sales_team_id = fields.Many2one('crm.team', string='Sales Team', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, copy=False,
                                 default=lambda self: self.env.company.id, tracking=True, readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, copy=False,
                                   default=lambda self: self.env['stock.warehouse'].search(
                                       [('company_id', '=', self.env.company.id)], limit=1), tracking=True,
                                   readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', tracking=True)
    access_token = fields.Char(string="Access Token", tracking=True)
    last_customer_import = fields.Datetime(string='Last Customer Import', tracking=True)
    last_product_import = fields.Datetime(string='Last Product Import', tracking=True)
    last_order_import = fields.Datetime(string='Last Order Import', tracking=True)
    last_product_export = fields.Datetime(string='Last Product Export', tracking=True)
    import_orders_after_date = fields.Datetime(string='Date to begin order import', default=fields.Datetime.now,
                                               tracking=True)
    notify_customer = fields.Boolean(string='Notify Customer', tracking=True)
    default_user = fields.Many2one('res.users', string='Default User', tracking=True)
    sync_with_images = fields.Boolean(string='Sync with Images', default=True, copy=False, tracking=True)
    webhook_line = fields.One2many('zid.webhook.ept', 'zid_instance_id', string='Webhooks', copy=False, readonly=True,
                                   tracking=True)
    orders_today = fields.Integer(string='Orders Today', compute='order_count_for_day', store=True)
    orders_this_week = fields.Integer(string='Orders This Week', compute='order_count_for_week', store=True)
    orders_this_month = fields.Integer(string='Orders This Month', compute='order_count_for_month', store=True)
    orders_this_year = fields.Integer(string='Orders This Year', compute='order_count_for_year', store=True)
    orders_yesterday = fields.Integer(string='Orders Yesterday', compute='order_count_yesterday', store=True)
    orders_last_week = fields.Integer(string='Orders Last Week', compute='order_count_last_week', store=True)
    orders_last_month = fields.Integer(string='Orders Last Month', compute='order_count_last_month', store=True)
    orders_last_year = fields.Integer(string='Orders Last Year', compute='order_count_last_year', store=True)
    active = fields.Boolean(string='Active', default=True, copy=False)
    has_multi_inventory = fields.Boolean(string='Multi-Inventory', tracking=True, default=False)

    onboarding_stores = fields.Boolean('Onboarding Stores')
    onboarding_products = fields.Boolean('Onboarding Products')

    def order_count_for_day(self):
        """Order Count for the day"""
        datetime_now = datetime.datetime.now()

        # Make the time as 00:00:00:
        datetime_now = datetime_now.replace(hour=0, minute=0, second=0)

        # Make the datetime without any tz info:
        datetime_now = datetime_now.replace(tzinfo=None)

        return self.env['sale.order'].search_count([('instance_id', '=', self.polygon_instance_id.id),
                                                    ('date_order', '>=', datetime_now),
                                                    ('state', 'in', ['sale', 'done'])])

    def order_count_for_week(self):
        """Order Count for the week"""
        datetime_now = datetime.datetime.now()

        # Make the time as 00:00:00:
        datetime_now = datetime_now.replace(hour=0, minute=0, second=0)

        # Make the datetime without any tz info:
        datetime_now = datetime_now.replace(tzinfo=None)

        # Date 7 days ago:
        datetime_7_days = datetime_now - datetime.timedelta(days=7)

        return self.env['sale.order'].search_count([('instance_id', '=', self.polygon_instance_id.id),
                                                    ('date_order', '>=', datetime_7_days),
                                                    ('date_order', '<=',
                                                     datetime_now.replace(hour=23, minute=59, second=59)),
                                                    ('state', 'in', ['sale', 'done'])])

    def order_count_for_month(self):
        """Order Count for the month"""
        datetime_now = datetime.datetime.now()

        # Make the time as 00:00:00:
        datetime_now = datetime_now.replace(hour=0, minute=0, second=0)

        # Make the datetime without any tz info:
        datetime_now = datetime_now.replace(tzinfo=None)

        # Date 30 days ago:
        datetime_30_days = datetime_now - datetime.timedelta(days=30)

        return self.env['sale.order'].search_count([('instance_id', '=', self.polygon_instance_id.id),
                                                    ('date_order', '>=', datetime_30_days),
                                                    ('date_order', '<=',
                                                     datetime_now.replace(hour=23, minute=59, second=59)),
                                                    ('state', 'in', ['sale', 'done'])])

    def order_count_for_year(self):
        datetime_now = datetime.datetime.now()

        # Make the time as 00:00:00:
        datetime_now = datetime_now.replace(hour=0, minute=0, second=0)

        # Make the datetime without any tz info:
        datetime_now = datetime_now.replace(tzinfo=None)

        # Date 65 days ago:
        datetime_1_year = datetime_now - datetime.timedelta(days=365)

        return self.env['sale.order'].search_count([('instance_id', '=', self.polygon_instance_id.id),
                                                    ('date_order', '>=', datetime_1_year),
                                                    ('date_order', '<=', datetime_now.replace(hour=23, minute=59, second=59)),
                                                    ('state', 'in', ['sale', 'done'])])

    def order_count_yesterday(self):
        """Order Count for the yesterday"""
        datetime_now = datetime.datetime.now()

        # Make the time as 00:00:00:
        datetime_now = datetime_now.replace(hour=0, minute=0, second=0)

        # Make the datetime without any tz info:
        datetime_now = datetime_now.replace(tzinfo=None)

        # Date 1 day ago:
        datetime_now = datetime_now - datetime.timedelta(days=1)

        return self.env['sale.order'].search_count([('instance_id', '=', self.polygon_instance_id.id),
                                                    ('date_order', '>=', datetime_now),
                                                    ('date_order', '<=',
                                                     datetime_now.replace(hour=23, minute=59, second=59)),
                                                    ('state', 'in', ['sale', 'done'])])

    def order_count_last_week(self):
        """Order Count for the last week"""
        datetime_now = datetime.datetime.now()

        # Make the time as 00:00:00:
        datetime_now = datetime_now.replace(hour=0, minute=0, second=0)

        # Make the datetime without any tz info:
        datetime_now = datetime_now.replace(tzinfo=None)

        # Date 7 day ago:
        datetime_end = datetime_now - datetime.timedelta(days=8)

        # Date 14 day ago:
        datetime_start = datetime_now - datetime.timedelta(days=15)

        return self.env['sale.order'].search_count([('instance_id', '=', self.polygon_instance_id.id),
                                                    ('date_order', '>=', datetime_start),
                                                    ('date_order', '<=',
                                                     datetime_end.replace(hour=23, minute=59, second=59)),
                                                    ('state', 'in', ['sale', 'done'])])

    def order_count_last_month(self):
        """Order Count for the last month"""
        datetime_now = datetime.datetime.now()

        # Make the time as 00:00:00:
        datetime_now = datetime_now.replace(hour=0, minute=0, second=0)

        # Make the datetime without any tz info:
        datetime_now = datetime_now.replace(tzinfo=None)

        # Date 30 day ago:
        datetime_end = datetime_now - datetime.timedelta(days=31)

        # Date 60 day ago:
        datetime_start = datetime_now - datetime.timedelta(days=61)

        return self.env['sale.order'].search_count([('instance_id', '=', self.polygon_instance_id.id),
                                                    ('date_order', '>=', datetime_start),
                                                    ('date_order', '<=',
                                                     datetime_end.replace(hour=23, minute=59, second=59)),
                                                    ('state', 'in', ['sale', 'done'])])

    def order_count_last_year(self):
        """Order Count for the last year"""
        datetime_now = datetime.datetime.now()

        # Make the time as 00:00:00:
        datetime_now = datetime_now.replace(hour=0, minute=0, second=0)

        # Make the datetime without any tz info:
        datetime_now = datetime_now.replace(tzinfo=None)

        # Date 365 day ago:
        datetime_end = datetime_now - datetime.timedelta(days=366)

        # Date 730 day ago:
        datetime_start = datetime_now - datetime.timedelta(days=731)

        return self.env['sale.order'].search_count([('instance_id', '=', self.polygon_instance_id.id),
                                                    ('date_order', '>=', datetime_start),
                                                    ('date_order', '<=',
                                                     datetime_end.replace(hour=23, minute=59, second=59)),
                                                    ('state', 'in', ['sale', 'done'])])


class ZidWebhook(models.Model):
    _name = 'zid.webhook.ept'
    _description = 'Zid Webhook EPT'

    zid_instance_id = fields.Many2one('zid.instance.ept', string="Zid Instance", required=True, ondelete='cascade',
                                      index=True, copy=False)
