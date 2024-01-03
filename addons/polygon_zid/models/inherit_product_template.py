import itertools
import logging

import base64
import certifi
import urllib3
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class InheritProductTemplate(models.Model):
    _inherit = "product.template"

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


    def _create_variant_ids(self):
        """
        Overided this function to preserve variant when new attribute is added
        to the template
        :return:
        """
        if not self:
            return

        self.env.flush_all()
        Product = self.env["product.product"]

        variants_to_create = []
        variants_to_activate = Product
        variants_to_unlink = Product

        for tmpl_id in self:
            lines_without_no_variants = tmpl_id.valid_product_template_attribute_line_ids._without_no_variant_attributes()

            all_variants = tmpl_id.with_context(active_test=False).product_variant_ids.sorted(lambda p: (p.active, -p.id))

            current_variants_to_create = []
            current_variants_to_activate = Product

            # adding an attribute with only one value should not recreate product
            # write this attribute on every product to make sure we don't lose them
            # single_value_lines = lines_without_no_variants.filtered(
            #     lambda ptal: len(ptal.product_template_value_ids._only_active()) == 1)
            # if single_value_lines:
            #     for variant in all_variants:
            #         combination = variant.product_template_attribute_value_ids | single_value_lines.product_template_value_ids._only_active()
            #         # Do not add single value if the resulting combination would
            #         # be invalid anyway.
            #         if (
            #                 len(combination) == len(lines_without_no_variants) and
            #                 combination.attribute_line_id == lines_without_no_variants
            #         ):
            #             variant.product_template_attribute_value_ids = combination

            # Set containing existing `product.template.attribute.value` combination
            existing_variants = {
                variant.product_template_attribute_value_ids: variant for variant in all_variants
            }

            # Determine which product variants need to be created based on the attribute
            # configuration. If any attribute is set to generate variants dynamically, skip the
            # process.
            # Technical note: if there is no attribute, a variant is still created because
            # 'not any([])' and 'set([]) not in set([])' are True.
            if not tmpl_id.has_dynamic_attributes():
                # Iterator containing all possible `product.template.attribute.value` combination
                # The iterator is used to avoid MemoryError in case of a huge number of combination.
                all_combinations = itertools.product(*[
                    ptal.product_template_value_ids._only_active() for ptal in lines_without_no_variants
                ])
                # For each possible variant, create if it doesn't exist yet.
                for combination_tuple in all_combinations:
                    combination = self.env['product.template.attribute.value'].concat(*combination_tuple)
                    is_combination_possible = tmpl_id._is_combination_possible_by_config(combination,
                                                                                         ignore_no_variant=True)
                    if not is_combination_possible:
                        continue
                    if combination in existing_variants:
                        current_variants_to_activate += existing_variants[combination]
                    else:
                        current_variants_to_create.append(tmpl_id._prepare_variant_values(combination))
                        if len(current_variants_to_create) > 1000:
                            raise UserError(_(
                                'The number of variants to generate is too high. '
                                'You should either not generate variants for each combination or generate them on demand from the sales order. '
                                'To do so, open the form view of attributes and change the mode of *Create Variants*.'))
                variants_to_create += current_variants_to_create
                variants_to_activate += current_variants_to_activate

            else:
                for variant in existing_variants.values():
                    is_combination_possible = self._is_combination_possible_by_config(
                        combination=variant.product_template_attribute_value_ids,
                        ignore_no_variant=True,
                    )
                    if is_combination_possible:
                        current_variants_to_activate += variant
                variants_to_activate += current_variants_to_activate

            variants_to_unlink += all_variants - current_variants_to_activate

        if variants_to_activate:
            variants_to_activate.write({'active': True})
        if variants_to_create:
            Product.create(variants_to_create)
        # if variants_to_unlink:
        #     variants_to_unlink._unlink_or_archive()
            # prevent change if exclusion deleted template by deleting last variant
            if self.exists() != self:
                raise UserError(
                    _("This configuration of product attributes, values, and exclusions would lead to no possible variant. Please archive or delete your product directly if intended."))

        # prefetched o2m have to be reloaded (because of active_test)
        # (eg. product.template: product_variant_ids)
        # We can't rely on existing invalidate because of the savepoint
        # in _unlink_or_archive.
        self.env.flush_all()
        self.env.invalidate_all()
        return True
