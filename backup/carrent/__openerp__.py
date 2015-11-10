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
    'depends': ['sale_stock','point_of_sale','carrent_report_layout'],

    # always loaded
    'data': [
        'views/rental_report.xml',
        'views/sequences.xml',
        'views/workflow.xml',
        'views/report_carrent_management.xml',
        'views/carrent.xml'
    ],
}
