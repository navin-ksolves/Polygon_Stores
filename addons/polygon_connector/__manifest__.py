# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Polygon Connector Module',
    'author': 'Polygon Stores Tech',
    'website': 'www.polygonstores.com',
    'maintainer': 'Polygon Stores Tech',
    'version': '1.0',
    'summary': 'Handle Polygon Connector',
    'category': 'Sales',
    'description': "Handle the Polygon Base logics",
    'data': [
        'security/ir.model.access.csv',
        'views/polygon_connector_view.xml',
        'views/stock_warehouse.xml',
        'views/product_pricelist.xml'
    ],
    'depends': [
        'polygon_base',
        'polygon_client',
        'delivery_partner_integration'
    ],
    'auto_install': False,
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
