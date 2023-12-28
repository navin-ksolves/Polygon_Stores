import base64
import certifi
import urllib3
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    """Inherit the model to add fields and function"""
    _inherit = 'product.product'

    image_url = fields.Char(string='Image URL', help='Image URL or Path')
    image_added = fields.Binary("Image (1920x1920)",
                                compute='_compute_image_added', store=True)

    @api.depends('image_url')
    def _compute_image_added(self):
        """ Function to load an image from URL or local file path """
        for product in self:
            image = False
            if product.image_url:
                if product.image_url.startswith(('http://', 'https://')):
                    # Load image from URL
                    try:
                        http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED',
                                                   ca_certs=certifi.where())
                        image_response = http.request('GET', product.image_url)
                        image = base64.b64encode(image_response.data)
                    except Exception as e:
                        # Handle URL loading errors
                        raise UserError(
                            _(f"Error loading image from URL: {str(e)}"))
                else:
                    # Load image from local file path
                    try:
                        with open(product.image_url, 'rb') as image_file:
                            image = base64.b64encode(image_file.read())
                    except Exception as e:
                        # Handle local file loading errors
                        raise UserError(
                            _(f"Error loading image from local path: {str(e)}"))
            image_added = image
            if image_added:
                product.image_1920 = image_added

