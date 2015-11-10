# -*- coding: utf-8 -*-
{
    'name': "CSmart Car Rental Management",

    'summary': """
        Aplikasi Manajemen Sewa Mobil""",

    'description': """
        Aplikasi untuk me-manage persewaan mobil
    """,

    'author': "DTBS",
    'website': "http://www.dtbsindo.web.id",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Rental',
    'version': '0.1',

    # any module necessary for this one to work correctly
    # 'depends': ['csmart_base','sale_stock','point_of_sale','product_uom_prices','customer_auto_email'],
    'depends': ['csmart_base','sale','product_uom_prices','customer_auto_email'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/carrent.xml'
    ],
}
