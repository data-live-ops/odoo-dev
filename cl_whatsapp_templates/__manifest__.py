{
    'name': 'WhatsApp Templates',
    'version': '1.0',
    'category': 'Discuss',
    'summary': 'Template messages for WhatsApp conversations',
    'description': """
        WhatsApp Template Messages
        ==========================
        This module adds template message functionality for WhatsApp conversations in Odoo Discuss.

        Features:
        ---------
        * Create and manage message templates
        * Quick insert templates in WhatsApp conversations
        * Support for dynamic placeholders
        * Category and search functionality
    """,
    'author': 'PortCities',
    'website': 'https://www.portcities.net',
    'depends': ['base', 'mail', 'whatsapp'],
    'data': [
        'security/ir.model.access.csv',
        'views/whatsapp_template_views.xml',
        'views/discuss_channel_views.xml',
        'data/whatsapp_template_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cl_whatsapp_templates/static/src/slash_commands/template_slash_commands.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
