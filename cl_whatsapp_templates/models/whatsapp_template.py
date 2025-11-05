from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class WhatsAppTemplate(models.Model):
    _name = 'discuss.template'
    _description = 'Discuss Message Template'
    _order = 'sequence, name'

    name = fields.Char(
        string='Template Name',
        required=True,
        help='Short name to identify the template'
    )

    content = fields.Text(
        string='Message Content',
        required=True,
        help='The message content. Use {partner_name}, {company_name}, etc. for placeholders'
    )

    category = fields.Selection([
        ('greeting', 'Greeting'),
        ('info', 'Information'),
        ('support', 'Support'),
        ('closing', 'Closing'),
        ('other', 'Other'),
    ], string='Category', default='other', required=True)

    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Lower number appears first in the list'
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        help='Inactive templates are hidden from selection'
    )

    description = fields.Char(
        string='Description',
        help='Short description of when to use this template'
    )

    usage_count = fields.Integer(
        string='Usage Count',
        default=0,
        readonly=True,
        help='Number of times this template has been used'
    )

    shortcut = fields.Char(
        string='Shortcut',
        help='Quick access shortcut (e.g., /greeting)'
    )

    @api.model
    def get_templates_for_picker(self, category=None):
        """Return templates formatted for the template picker widget"""
        domain = [('active', '=', True)]
        if category:
            domain.append(('category', '=', category))

        templates = self.search(domain)
        return templates.read(['id', 'name', 'content', 'category', 'description', 'shortcut'])

    def action_use_template(self):
        """Increment usage counter when template is used"""
        self.ensure_one()
        self.usage_count += 1
        return True

    def apply_placeholders(self, partner_id=None):
        """Replace placeholders with actual values

        Args:
            partner_id: res.partner record for personalization

        Returns:
            str: Message content with placeholders replaced
        """
        self.ensure_one()
        content = self.content

        # Always replace company placeholders
        content = content.replace('{company_name}', self.env.company.name or '')

        # Replace partner placeholders if partner is provided
        if partner_id:
            replacements = {
                '{partner_name}': partner_id.name or '',
                '{partner_phone}': partner_id.mobile or partner_id.phone or '',
                '{partner_email}': partner_id.email or '',
            }

            for placeholder, value in replacements.items():
                content = content.replace(placeholder, value)

        return content
