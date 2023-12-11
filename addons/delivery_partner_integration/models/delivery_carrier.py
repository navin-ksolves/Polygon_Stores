from odoo import api, fields, models
from odoo.exceptions import UserError

class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    shipping_method = fields.Selection([('express', 'Instant 1 Hour'), ('same_day', 'Same Day'), ('next_day', 'Next Day'), ('vendor_del', 'Vendor Delivery')], default="express", string='Shipping Method', required=True)
