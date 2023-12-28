# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Zid Integration',
    'author': 'Polygon Stores Tech',
    'website': 'www.polygonstores.com',
    'maintainer': 'Polygon Stores Tech',
    'version': '16.0.1.0',
    'summary': 'Handle Zid Integration',
    'category': 'Sales',
    'description': "Handle the Polygon Zid Integration",
    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'data/zid_country_master_data.xml',
        'wizard/wizard_scheduler_log.xml',
        'views/zid_instance_ept.xml',
        'views/zid_customer_ept.xml',
        'views/zid_customer_locations.xml',
        'views/zid_product_category.xml',
        'views/zid_product_template.xml',
        'views/zid_product_attributes.xml',
        'views/zid_product_attributes_values.xml',
        'views/zid_product_variants_images.xml',
        'views/zid_order_ept.xml',
        'views/zid_order_lines_ept.xml',
        'views/zid_payment_gateway_view.xml',
        'views/zid_scheduler_order_view.xml',
        'views/zid_scheduler_order_line_view.xml',
        'views/zid_sale_workflow_config_view.xml',
        'views/zid_scheduler_log_line.xml',
        'views/zid_scheduler_log.xml',
        'views/zid_app.xml',
        'views/zid_request.xml',
        'views/zid_tokens.xml',
        'views/zid_user.xml',
        'views/zid_product_variants.xml',
        'views/zid_state_master_view.xml',
        'views/zid_country_master_view.xml',
        'views/zid_scheduler_state_view.xml',
        'views/zid_currency_view.xml',
        'views/zid_scheduler_currency_view.xml',
        'views/store_location_view.xml',
        'views/zid_store_location_scheduler.xml',
        'views/zid_product_attribute_value_scheduler.xml',
        'views/zid_product_attribute_scheduler_view.xml',
        'views/zid_scheduler_product_variant_view.xml',
        'views/zid_scheduler_products_view.xml',
        'views/zid_product_category_scheduler_view.xml',
        'views/zid_product_image.xml',
        # 'views/zid_delivery_options_view.xml',
        # 'views/zid_delivery_option_cities.xml',
        'menu/menu.xml',
    ],
    'depends': [
        'polygon_base',
        'polygon_client',
        'polygon_connector',
    ],
    'auto_install': False,
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}