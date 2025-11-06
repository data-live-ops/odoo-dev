from odoo import models, api
import re
import logging

_logger = logging.getLogger(__name__)


class MailCannedResponse(models.Model):
    _inherit = 'mail.canned.response'

    def render_substitution(self, channel_id=None):
        """Render substitution with placeholders replaced

        Supported placeholders:
        [NAME] - Partner/Contact name
        [COMPANY] - Company name
        [PHONE] - Partner phone
        [EMAIL] - Partner email
        [USER] - Current user name

        Args:
            channel_id: discuss.channel ID for context

        Returns:
            str: Rendered substitution text
        """
        self.ensure_one()
        substitution = self.substitution or ''

        _logger.info(f"[Canned Response] render_substitution called for canned_response {self.id}, channel_id: {channel_id}")
        _logger.info(f"[Canned Response] Original substitution: {substitution}")

        # Check if there are any placeholders
        if '[' not in substitution:
            return substitution

        # Get replacement values
        replacements = {}

        # Company name (always available)
        replacements['[COMPANY]'] = self.env.company.name or ''
        _logger.info(f"[Canned Response] [COMPANY] = {replacements['[COMPANY]']}")

        # Current user (the logged in user, NOT the customer)
        replacements['[USER]'] = self.env.user.name or ''
        _logger.info(f"[Canned Response] [USER] = {replacements['[USER]']} (user ID: {self.env.user.id})")

        # Partner info from channel (this is the CUSTOMER)
        if channel_id:
            channel = self.env['discuss.channel'].browse(channel_id)
            if channel.exists():
                partner = self._find_partner_from_channel(channel)

                if partner:
                    replacements['[NAME]'] = partner.name or ''
                    replacements['[PHONE]'] = partner.mobile or partner.phone or ''
                    replacements['[EMAIL]'] = partner.email or ''
                    _logger.info(f"[Canned Response] [NAME] = {replacements['[NAME]']} (partner ID: {partner.id})")
                    _logger.info(f"[Canned Response] [PHONE] = {replacements['[PHONE]']}")
                    _logger.info(f"[Canned Response] [EMAIL] = {replacements['[EMAIL]']}")
                else:
                    _logger.warning(f"[Canned Response] No partner found for channel {channel_id}")
        else:
            _logger.warning(f"[Canned Response] No channel_id provided, skipping [NAME], [PHONE], [EMAIL]")

        # Replace all placeholders
        for placeholder, value in replacements.items():
            substitution = substitution.replace(placeholder, value)

        _logger.info(f"[Canned Response] Final rendered: {substitution}")

        return substitution

    @api.model
    def _get_substitution_with_variables(self, canned_response_id, channel_id=None):
        """Get substitution text with variables replaced

        Variables format: {{1}}, {{2}}, {{3}}, etc.
        Maps to: partner_name, company_name, partner_phone, etc.

        Args:
            canned_response_id: ID of canned response
            channel_id: discuss.channel ID for context

        Returns:
            str: Substitution text with variables replaced
        """
        canned_response = self.browse(canned_response_id)
        if not canned_response.exists():
            return ''

        substitution = canned_response.substitution or ''

        # Find all {{N}} patterns
        variable_pattern = re.findall(r'{{(\d+)}}', substitution)
        if not variable_pattern:
            # No variables, return as is
            return substitution

        # Get replacement values
        replacements = self._get_variable_values(channel_id)

        # Replace each {{N}} with corresponding value
        for var_num in variable_pattern:
            var_index = int(var_num)
            if var_index in replacements:
                substitution = substitution.replace(f'{{{{{var_num}}}}}', replacements[var_index])
            else:
                _logger.warning(f"Variable {{{{var_num}}}} has no mapping, keeping as is")

        return substitution

    def _get_variable_values(self, channel_id=None):
        """Get variable replacement values from channel context

        Variable mapping:
        {{1}} -> partner_name
        {{2}} -> company_name
        {{3}} -> partner_phone
        {{4}} -> partner_email
        {{5}} -> user_name

        Args:
            channel_id: discuss.channel ID

        Returns:
            dict: {1: 'value', 2: 'value', ...}
        """
        replacements = {}

        # Get company name (always available)
        replacements[2] = self.env.company.name or ''

        # Get current user name
        replacements[5] = self.env.user.name or ''

        # Get partner info from channel if available
        if channel_id:
            channel = self.env['discuss.channel'].browse(channel_id)
            if channel.exists():
                partner = self._find_partner_from_channel(channel)

                if partner:
                    replacements[1] = partner.name or ''
                    replacements[3] = partner.mobile or partner.phone or ''
                    replacements[4] = partner.email or ''
                    _logger.info(f"[Canned Response Variables] Found partner: {partner.name}")
                else:
                    _logger.info(f"[Canned Response Variables] No partner found for channel {channel.id}")

        return replacements

    def _find_partner_from_channel(self, channel):
        """Find partner from channel

        Args:
            channel: discuss.channel record

        Returns:
            res.partner or False
        """
        _logger.info(f"[Canned Response] Finding partner for channel {channel.id} (type: {channel.channel_type})")

        # For WhatsApp channels
        if channel.channel_type == 'whatsapp':
            whatsapp_number = channel.whatsapp_number
            _logger.info(f"[Canned Response] WhatsApp number: {whatsapp_number}")

            if whatsapp_number:
                partner = channel._find_partner_by_phone(whatsapp_number)
                if partner:
                    _logger.info(f"[Canned Response] Found partner via phone: {partner.name} (ID: {partner.id})")
                    return partner
                else:
                    _logger.warning(f"[Canned Response] No partner found for WhatsApp number: {whatsapp_number}")
            else:
                _logger.warning(f"[Canned Response] WhatsApp channel has no whatsapp_number field")

        # For direct message channels
        if channel.channel_type == 'chat':
            # Get the other member (not current user)
            other_members = channel.channel_member_ids.filtered(
                lambda m: m.partner_id.id != self.env.user.partner_id.id
            )
            if other_members:
                partner = other_members[0].partner_id
                _logger.info(f"[Canned Response] Found partner from chat: {partner.name} (ID: {partner.id})")
                return partner

        # For group channels, try to get from channel_partner_ids
        if channel.channel_partner_ids:
            # Return first partner that's not current user
            partners = channel.channel_partner_ids.filtered(
                lambda p: p.id != self.env.user.partner_id.id
            )
            if partners:
                partner = partners[0]
                _logger.info(f"[Canned Response] Found partner from group: {partner.name} (ID: {partner.id})")
                return partner

        _logger.warning(f"[Canned Response] No partner found for channel {channel.id}")
        return False
