# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Conversion Engine Integration',
    'author': 'Polygon Stores Tech',
    'website': 'www.polygonstores.com',
    'maintainer': 'Polygon Stores Tech',
    'version': '1.0',
    'summary': 'Handle Conversion Engine Integration',
    'category': 'Sales',
    'description': "Handle the Polygon Conversion Engine Integration",
    'data': [
        'security/ir.model.access.csv',
        'views/polygon_cengine_view.xml',
        'data/ir_cron_data.xml'
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
