{
    'name': 'Colearn - Helpdesk SLA Timer',
    'version': '18.0.1.0.0',
    'category': 'Settings',
    'summary': 'SLA Timer',
    'description': """
        -SLA Timer
    """,
    'website': 'https://www.portcities.net',
    'author': 'Portcities Ltd.',
    'depends': [
        'helpdesk'
    ],
    'data': [
        'views/sla_policies_views.xml',
        'data/ir_cron_sla_reminder.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'AGPL-3',
}
