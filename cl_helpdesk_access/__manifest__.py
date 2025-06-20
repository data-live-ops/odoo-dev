{
    'name': 'Colearn - Helpdesk Access Rights',
    'version': '18.0.1.0.0',
    'category': 'Helpdesk',
    'summary': 'Helpdesk access rights customizations',
    'description': """
        Add customizations to helpdesk access rights for CoLearn
    """,
    'website': 'https://www.portcities.net',
    'author': 'Portcities Ltd.',
    'depends': ['helpdesk'],
    'data': [
        'data/res_groups_data.xml',
        'data/ir_rule_data.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'AGPL-3',
}
