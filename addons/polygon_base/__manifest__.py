# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Polygon Custom Module',
    'version': '1.0',
    'summary': 'Handle Polygon Base logics',
    'category': 'Sales',
    'description': "Handle the Polygon Base logics",
    'website': 'https://www.odoo.com/app/point-of-sale-shop',
    'data': [
        'security/polygon_users.xml',
        'security/ir.model.access.csv',
        'security/sale_order.xml',
        'security/product_template.xml',
        'security/product_product.xml',
        'views/product_owners.xml',
        'views/polygon_base.xml',
    ],
    'depends': [
        'crm',
        'sale_management',
        'stock',
        'account',
    ],
    'auto_install': False,
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
