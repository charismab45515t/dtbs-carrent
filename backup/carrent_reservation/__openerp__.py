# -*- coding: utf-8 -*-
{
    'name': "CSmart Car Rental Reservation",

    'summary': """
        Sistem Reservasi Manajemen Sewa Mobil""",

    'description': """
        Aplikasi untuk me-manage reservasi persewaan mobil
    """,

    'author': "DTBS",
    'website': "http://www.dtbsindo.web.id",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Rental',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['carrent','stock','mail','email_template','carrent_report_layout'],

    # always loaded
    'data': [
        'views/sequences.xml',
        "wizard/reservation_wizard.xml",
        'views/reservation_workflow.xml',
        'views/unit_summ_view.xml',
        'views/scheduler.xml',
        'views/reservation.xml'
    ],
    'js': ["static/src/js/carrent_unit_summary.js", ],
    'qweb': ['static/src/xml/carrent_unit_summary.xml'],
    'css': ["static/src/css/unit_summary.css"],
    'installable': True,
    'auto_install': False,
}
