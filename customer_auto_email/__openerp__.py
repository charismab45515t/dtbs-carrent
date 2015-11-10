# -*- coding: utf-8 -*-
{
    "name" : "Automatical email to customer",
    "version" : "1.0",
    "author" : "DTBS",
    "description": """
        Sends automatic when customer created
    """,
    "website" : "http://dtbsindo.web.id",
    "category" : "",
    # 'depends': ['base','csmart_base','sale_stock'],
    'depends': ['base','csmart_base','sale'],
    "data" : [
        'views/email_template_customer_auto.xml',
        'views/configuration.xml',
        'views/configuration_data.xml',
        'views/menu.xml'
    ],
    'js': [], 
    'css': [],
    'qweb': [],
    "active": False,
    "installable": True,
}