{
    'name': 'CoLearn Contact - Base',
    'version': '18.0.1.0.0',
    'summary': 'Module for contact base',
    'description': """
        Add contact customizations for base
    """,
    'category': 'Contacts',
    'author': "Port Cities Ltd",
    'website': "http://www.portcities.net",
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'wizard/contact_merge_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'AGPL-3',
    'support': 'modules@portcities.net',
}
