import requests
import json

from odoo import api, fields, models
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = 'res.company'

    shipsy_api_key = fields.Char(
        'Shipsy API Key', help='API Key used to connect the shipsy delivery partner apis.')
