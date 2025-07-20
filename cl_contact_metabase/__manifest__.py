{
    'name': 'CoLearn Contact Metabase Integration',
    'version': '1.0',
    'category': 'Contacts',
    'summary': 'Integrate Metabase data with Odoo contacts',
    'description': """
        This module integrates Metabase with Odoo contacts (res.partner).
        It allows for retrieving data from various predefined Metabase questions/cards
        and mapping them to Odoo contacts.
    """,
    'author': 'PortCities',
    'website': 'https://www.portcities.net',
    'depends': ['base', 'contacts', 'queue_job', 'cl_contact_base'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'data/email_notify_template.xml',
        'views/metabase_config_views.xml',
        'views/sync_log_views.xml',
        'wizards/response_metabase_views.xml',
        'views/res_partner_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

# attendance Paid Class Main
# attendance Paid Class Details

# Payment Slot Selection Succeeded
# Payment Received
# Payment Paid Access Paused
