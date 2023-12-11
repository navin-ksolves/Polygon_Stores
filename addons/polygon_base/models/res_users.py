from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    polygon_user_type = fields.Selection([
                                    ('client_user', 'Client User'),
                                    ('polygon_sales', 'Polygon Sales'),
                                    ('polygon_ops_manager', 'Polygon Ops Manager'),
                                    ('polygon_ops_executive', 'Polygon Ops Executive'),
                                    ('polygon_warehouse_manager', 'Polygon Warehouse Manager'),
                                    ('polygon_warehouse_executive', 'Polygon Warehouse Executive'),
                                    ('polygon_warehouse_picker', 'Polygon Warehouse Picker'),
                                    ('polygon_finance', 'Polygon Finance'),
                                    ('polygon_tech', 'Polygon Tech'),
                                    ('polygon_management', 'Polygon Management'),
                                    ('polygon_superadmin', 'Polygon Super Admin'),
                                ], string='User Type', default='client_user', copy=False)