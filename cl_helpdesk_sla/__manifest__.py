{
    'name': 'CoLearn Helpdesk - SLA Timer',
    'version': '18.0.1.0.0',
    'summary': 'Module for helpdesk SLA timer',
    'description': """
        Add helpdesk customizations for SLA timer
    """,
    'category': 'Helpdesk',
    'author': "Port Cities Ltd",
    'website': "http://www.portcities.net",
    'depends': ['helpdesk'],
    'data': [
        'data/ir_cron_data.xml',
        'views/helpdesk_sla_views.xml',
        'views/helpdesk_ticket_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'AGPL-3',
    'support': 'modules@portcities.net',
    'post_init_hook': 'update_helpdesk_sla_company_rule_domain',
    'uninstall_hook': 'restore_helpdesk_sla_company_rule',
}
