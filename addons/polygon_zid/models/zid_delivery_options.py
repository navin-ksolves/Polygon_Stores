# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ZidDeliveryOptions(models.Model):
    _name = 'zid.delivery.options'
    _description = 'Contains delivery options'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    zid_instance_id = fields.Many2one('zid.instance.ept', string="Instance", tracking=True, required=True, index=True)
    zid_delivery_option_id = fields.Integer(string="Zid Delivery Option Id")
    name = fields.Char(string="Name")
    city_ids = fields.One2many('zid.delivery.options.cities', 'zid_delivery_option_id', string="Cities")
    active = fields.Boolean(string="Active", default=False)

    def write(self, values):
        res = super(ZidDeliveryOptions, self).write(values)
        for delivery_option in self:
            if values.get('active') == True:
                create_log_for = ['sync_do_countries_states']
                for log in create_log_for:
                    data_for_log = {
                        'scheduler_type': log,
                        'instance_id': self.zid_instance_id.id,
                        'status': 'draft',
                        'json': {"delivery_option_id": delivery_option.id},
                        'attempts': 0
                    }
                    delivery_option.env['zid.scheduler.log.line'].sudo().create(data_for_log)
        # here you can do accordingly
        return res
