from odoo import models, api
import re
import logging

_logger = logging.getLogger(__name__)


class MailChannel(models.Model):
    _inherit = 'mail.channel'

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set proper name for WhatsApp channels at creation time

        This ensures new WhatsApp channels immediately show contact names
        instead of phone numbers in the Discuss sidebar.
        """
        for vals in vals_list:
            if vals.get('channel_type') == 'whatsapp' and vals.get('whatsapp_number'):
                phone = vals['whatsapp_number']

                # Find partner by phone number with flexible matching
                partner = self._find_partner_by_phone(phone)

                if partner:
                    vals['name'] = partner.name
                    _logger.info(f"WhatsApp channel created with name: {partner.name} (phone: {phone})")
                else:
                    _logger.warning(f"WhatsApp channel created but no partner found for phone: {phone}")

        return super().create(vals_list)

    def name_get(self):
        """Override name_get to display partner name for WhatsApp channels

        This fixes existing WhatsApp channels that show phone numbers
        by dynamically resolving to contact names on display.
        """
        result = []

        for channel in self:
            name = channel.name

            # Only process WhatsApp channels with phone number as name
            if channel.channel_type == 'whatsapp' and channel.whatsapp_number:
                if re.match(r'^[\+]?[0-9]{8,15}$', str(name)):
                    # Try to find partner by phone
                    partner = self._find_partner_by_phone(channel.whatsapp_number)

                    if partner:
                        name = partner.name

            result.append((channel.id, name))

        return result

    @api.model
    def _find_partner_by_phone(self, phone):
        """Helper method to find partner by phone number with flexible matching

        Supports multiple Indonesian phone formats:
        - 628788147054 (country code without +)
        - +628788147054 (country code with +)
        - 08788147054 (local format with 0)
        - 8788147054 (local format without 0)

        Args:
            phone (str): Phone number to search

        Returns:
            res.partner: Matching partner record or False
        """
        if not phone:
            return False

        # Clean phone number (remove special characters)
        phone_clean = str(phone).replace('+', '').replace(' ', '').replace('-', '')

        # Get last 10 digits for partial matching
        last_10 = phone_clean[-10:] if len(phone_clean) >= 10 else phone_clean

        # Search with multiple format variations
        partner = self.env['res.partner'].search([
            '|', '|', '|',
            ('mobile', '=', phone_clean),                                                      # Exact match
            ('mobile', '=', f'0{phone_clean}'),                                                # With 0 prefix
            ('mobile', '=', f'62{phone_clean}' if not phone_clean.startswith('62') else phone_clean),  # With 62 country code
            ('mobile', 'like', f'%{last_10}'),                                                # Last 10 digits match
            ('active', '=', True)
        ], limit=1, order='write_date desc')

        return partner
