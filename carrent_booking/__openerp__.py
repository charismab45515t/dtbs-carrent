# -*- coding: utf-8 -*-
{
    'name': "CSmart Car Rental Booking Management",

    'summary': """
        Aplikasi Manajemen Booking Rental""",

    'description': """
        Aplikasi untuk me-manage booking mobil
    """,

    'author': "DTBS",
    'website': "http://www.dtbsindo.web.id",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Rental',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['csmart_base','carrent','attachment_preview'],

    # always loaded
    'data': [
        'views/configuration.xml',
        'views/configuration_data.xml',
        'views/unit_summ_view.xml',
        'wizard/booking_return_wizard.xml',
        'views/booking.xml',
        'views/workflow.xml',
        'views/sequences.xml',
        'views/booking_data.xml',
        'views/booking_email.xml',
        'views/booking_cron.xml'
    ],
    'js': ["static/src/js/carrent_unit_summary.js", ],
    'qweb': ['static/src/xml/carrent_unit_summary.xml'],
    'css': ["static/src/css/unit_summary.css"],
}
