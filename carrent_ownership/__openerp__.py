# -*- coding: utf-8 -*-
{
    'name': "CSmart Car Ownership Management",

    'summary': """
        Aplikasi Manajemen BPKB Mobil Rental""",

    'description': """
        Aplikasi untuk me-manage BPKB mobil
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
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/ownership.xml',
        'views/workflow.xml',
        'views/ownership_data.xml',
        'views/sequences.xml'
    ],
}
