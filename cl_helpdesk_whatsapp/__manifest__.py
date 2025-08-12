{
    'name': 'CoLearn Helpdesk - Ticket Auto Creation from WhatsApp',
    'version': '18.0.1.0.1',
    'summary': 'Module for ticket auto creation from WhatsApp',
    'description': """
        Add helpdesk customizations for ticket auto creation from WhatsApp
    """,
    'category': 'Helpdesk',
    'author': "Port Cities Ltd",
    'website': "http://www.portcities.net",
    'depends': [
        'helpdesk',
        'whatsapp',
        'cl_contact_base',
    ],
    'data': [
        'views/helpdesk_team_views.xml',
        'views/helpdesk_ticket_views.xml',
        'views/whatsapp_template_views.xml',
        'views/whatsapp_message_views.xml',
        'views/helpdesk_stage_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'AGPL-3',
    'support': 'modules@portcities.net',
}
