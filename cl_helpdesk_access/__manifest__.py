{
    'name': 'CoLearn Helpdesk - Access Rights',
    'version': '18.0.1.0.0',
    'summary': 'Module for helpdesk access rights',
    'description': """
        Add helpdesk customizations for access rights
    """,
    'category': 'Helpdesk',
    'author': "Port Cities Ltd",
    'website': "http://www.portcities.net",
    'depends': ['helpdesk'],
    'data': [
        'data/res_groups_data.xml',
        'data/ir_rule_data.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'AGPL-3',
    'support': 'modules@portcities.net',
}
