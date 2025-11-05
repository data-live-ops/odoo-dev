from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    @api.model
    def get_whatsapp_templates(self, category=None):
        """Get available WhatsApp templates for the current channel

        Args:
            category: Optional category filter

        Returns:
            list: Template data for frontend
        """
        return self.env['discuss.template'].get_templates_for_picker(category)

    @api.model
    def search_templates_by_command(self, command):
        """Search templates by slash command

        Args:
            command: Command string (e.g., 'halo', 'greeting')

        Returns:
            list: Matching templates with preview
        """
        if not command:
            # Return all active templates
            domain = [('active', '=', True)]
        else:
            # Search by shortcut or name
            command_lower = command.lower()
            domain = [
                ('active', '=', True),
                '|', '|',
                ('shortcut', 'ilike', '/' + command_lower),
                ('name', 'ilike', command_lower),
                ('description', 'ilike', command_lower),
            ]

        templates = self.env['discuss.template'].search(domain, limit=10, order='sequence, name')

        result = []
        for template in templates:
            result.append({
                'id': template.id,
                'name': template.name,
                'shortcut': template.shortcut,
                'description': template.description,
                'content': template.content[:100] + '...' if len(template.content) > 100 else template.content,
                'category': template.category,
            })

        return result

    def get_template_content_for_channel(self, template_id):
        """Get template content with placeholders replaced for current channel

        Args:
            template_id: ID of template

        Returns:
            dict: Template content with replacements applied
        """
        self.ensure_one()
        template = self.env['discuss.template'].browse(template_id)

        if not template.exists():
            return {'error': 'Template not found'}

        # Get partner from channel
        partner = None
        if self.channel_type == 'whatsapp' and self.whatsapp_number:
            partner = self._find_partner_by_phone(self.whatsapp_number)

        # Apply placeholders
        content = template.apply_placeholders(partner)

        # Increment usage counter
        template.action_use_template()

        return {
            'content': content,
            'template_name': template.name,
        }

    def action_insert_template(self, template_id, partner_id=None):
        """Insert a template into the message composer

        Args:
            template_id: ID of the template to insert
            partner_id: Optional partner ID for personalization

        Returns:
            dict: Template content with placeholders replaced
        """
        template = self.env['discuss.template'].browse(template_id)

        if not template.exists():
            return {'error': 'Template not found'}

        # Get partner from channel if not provided
        if not partner_id and self.channel_type == 'whatsapp':
            # Try to find partner by whatsapp_number
            partner = self._find_partner_by_phone(self.whatsapp_number)
            if partner:
                partner_id = partner.id

        # Get partner record if ID provided
        partner = self.env['res.partner'].browse(partner_id) if partner_id else None

        # Apply placeholders
        content = template.apply_placeholders(partner)

        # Increment usage counter
        template.action_use_template()

        return {
            'content': content,
            'template_id': template.id,
            'template_name': template.name,
        }

    def _find_partner_by_phone(self, phone):
        """Helper method to find partner by phone number

        Args:
            phone: Phone number to search

        Returns:
            res.partner: Partner record or False
        """
        if not phone:
            return False

        phone_clean = str(phone).replace('+', '').replace(' ', '').replace('-', '')
        last_10 = phone_clean[-10:] if len(phone_clean) >= 10 else phone_clean

        partner = self.env['res.partner'].search([
            '|', '|', '|',
            ('mobile', '=', phone_clean),
            ('mobile', '=', '0' + phone_clean),
            ('mobile', '=', '62' + phone_clean if not phone_clean.startswith('62') else phone_clean),
            ('mobile', 'like', '%' + last_10),
            ('active', '=', True)
        ], limit=1, order='write_date desc')

        return partner
