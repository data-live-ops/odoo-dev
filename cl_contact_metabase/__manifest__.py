{
    'name': 'Colearn Contact Metabase Integration',
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
    'depends': ['base', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'views/metabase_config_views.xml',
        'views/res_partner_views.xml',
        'views/menu_views.xml',
        'wizards/import_metabase_contacts_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
