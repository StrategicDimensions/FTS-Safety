# -*- coding: utf-8 -*-
{
    'name' : 'PayU',
    'version' : '1.0',
    'depends' : ['payment','website_sale'],
    'author' : 'KTree computer solutions(p) Ltd',
    'category': 'payment',
    'summary':"PayU South Africa",
    'description': """
    PayU
    """,
    'website': 'http://www.odoo.com',
    'images': ['images/main-screenshot.png'],
    'data': [
	'views/payu_template.xml',
	'data/payu_data.xml',
	'views/payu.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    
}
