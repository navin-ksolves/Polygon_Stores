# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Polygon Client Module',
    'author': 'Polygon Stores Tech',
    'website': 'www.polygonstores.com',
    'maintainer': 'Polygon Stores Tech',
    'version': '1.0',
    'summary': 'Handle Polygon Clients for the Polygon Sales Team',
    'category': 'Sales',
    'description': "Handle the Polygon Base logics",
    'data': [
        'security/ir.model.access.csv',
        'views/menu_items.xml',
        'views/polygon_client_company.xml',
        'views/polygon_client_users.xml',
    ],
    'depends': [
        'polygon_base',
    ],
    'auto_install': False,
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
