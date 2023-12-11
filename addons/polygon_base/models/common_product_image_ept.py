from odoo import models, api, _


class ProductImageEpt(models.Model):
    _inherit = "common.product.image.ept"

    # Add a change detection on url to call the existing get_image_ept() method:
    @api.onchange('url')
    def _onchange_url(self):
        if self.url:
            self.get_image_ept()