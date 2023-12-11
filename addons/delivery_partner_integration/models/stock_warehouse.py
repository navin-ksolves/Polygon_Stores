import pytz

from odoo import fields, models, api

_tzs = [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]


def _tz_get(self):
    return _tzs


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    longitude = fields.Char(string="Longitude")
    latitude = fields.Char(string="Latitude")
    store_id_express = fields.Char(string="Store Code Express")
    store_id_planned = fields.Char(string="Store Code Planned")
    shift_slot_start = fields.Float(string="Shift Slot Start")
    shift_slot_end = fields.Float(string="Shift Slot End")
    tz = fields.Selection(_tz_get, string='Timezone', default=lambda self: self._context.get('tz'))