# -*- coding: utf-8 -*-
{
    'name': 'Delivery Partner Integration',
    'version': '1.0.0',
    'category': '',
    'author': 'Polygon Stores Tech',
    'website': "www.polygonstores.com",
    'summary': 'Integration with the delivery partner for the order updates.',
    'description': '''Integration of odoo with the delivery partner for the order updates.''',
    'depends': ['base', 'sale', 'shopify_ept'],
    'data': [
        'views/res_company_views.xml',
        'views/sale_order_view.xml',
        'views/stock_warehouse_view.xml',
        'views/product_template_view.xml'
    ],
    # 'images': ['images/odoo-mautic.png'],
    'license': 'OPL-1',
    'price': '',
    'currency': '',
    'installable': True,
    'auto_install': False,
}
