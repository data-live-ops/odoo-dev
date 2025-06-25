from datetime import timedelta
from odoo import fields, models
import logging

_logger = logging.getLogger(__name__)


class WhatsAppAccount(models.Model):
    """Extend WhatsApp Account to add autoreply functionality"""
    _inherit = "whatsapp.account"

    def _process_messages(self, value):
        """
        Override to add autoreply functionality for incoming messages
        """
        # Call the original method to process the message
        result = super(WhatsAppAccount, self)._process_messages(value)

        # Auto-create helpdesk ticket for each incoming WhatsApp message
        messages = value.get('messages')
        if not messages and value.get('whatsapp_business_api_data', {})\
                .get('messages'):
            messages = value['whatsapp_business_api_data']['messages']
        if messages:
            for message in messages:
                # If message is a button, extract payload as message_body
                if message.get('type') == 'button' and message.get(
                    'button',
                    {},
                ).get('payload'):
                    message_body = message['button']['payload']
                else:
                    message_body = message.get('text', {}).get('body') or\
                        message.get('body')
                sender_mobile = message.get('from')
                self.auto_create_ticket_from_whatsapp(
                    message_body,
                    sender_mobile
                )

        # Now handle autoreplies
        self._process_autoreplies(value)

        return result

    def auto_create_ticket_from_whatsapp(self, message_body, sender_mobile):
        """
        Auto-create a helpdesk ticket when receiving specific keyword.
        :param message_body: str, the WhatsApp message body
        :param sender_mobile: str, the sender's phone number
        :return: helpdesk.ticket record or None
        """
        template_id = self.env['whatsapp.template'].search([
            ('is_autoreply', '=', True),
        ], limit=1)

        if not template_id:
            return None
        else:
            trigger_message = template_id.button_create_ticket_id.name

        if trigger_message:
            if not message_body or\
                    message_body.strip() != trigger_message:
                return None  # Only trigger on exact message

        phone_number = '+' + sender_mobile
        # Search for partner by phone or mobile
        partner = self.env['res.partner'].search([
            ('mobile', '=', phone_number)
        ], limit=1)

        # Check for existing open ticket for this partner or phone
        open_ticket_domain = [('stage_id.is_closed_stage', '=', False)]
        if partner:
            open_ticket_domain += [('partner_id', '=', partner.id)]
        else:
            open_ticket_domain += [('partner_phone', '=', sender_mobile)]
        open_ticket = self.env['helpdesk.ticket'].search(
            open_ticket_domain,
            limit=1,
        )
        if open_ticket:
            _logger.info(
                "Skipping ticket creation: open ticket already exists for %s",
                partner and partner.name or sender_mobile
            )
            return None  # Skip ticket creation

        ticket_vals = {
            'name': 'WhatsApp Ticket',
            'description': 'Ticket created from WhatsApp message.',
            'channel': 'whatsapp',
        }
        if partner:
            ticket_vals['partner_id'] = partner.id
            ticket_vals['partner_phone'] = partner.mobile
        else:
            # Save phone in description if no partner found
            ticket_vals['partner_phone'] = sender_mobile
        ticket_vals['description'] += f"\nPhone: {sender_mobile}"

        ticket = self.env['helpdesk.ticket'].create(ticket_vals)
        return ticket

    def _process_autoreplies(self, value):
        """
        Send automatic replies based on configured templates in helpdesk teams
        """
        if 'messages' not in value and value.get(
            'whatsapp_business_api_data', {}
        ).get('messages'):
            value = value['whatsapp_business_api_data']

        for message in value.get('messages', []):
            # Skip processing for some message types
            if message.get('type') not in [
                'text',
                'button',
                'image',
                'document',
                'audio'
            ]:
                continue

            # Find sender's phone number
            sender_mobile = message.get('from')
            if not sender_mobile:
                continue

            # Check if this is from a contact we've already interacted with
            channel = self._find_active_channel(sender_mobile)
            if not channel:
                continue

            template_id = self.env['whatsapp.template'].search([
                ('is_autoreply', '=', True),
            ], limit=1)

            if not template_id or not template_id.wa_template_uid:
                continue

            timed_delay = template_id.timed_delay*60

            # Check if we've already sent an autoreply to this channel recently
            recent_autoreply = self.env['whatsapp.message'].sudo().search([
                ('mail_message_id.model', '=', 'discuss.channel'),
                ('mail_message_id.res_id', '=', channel.id),
                ('mobile_number', '=', sender_mobile),
                ('message_type', '=', 'outbound'),
                ('is_autoreply', '=', True),
            ], limit=1)

            if recent_autoreply:
                next_autoreply_time = recent_autoreply.create_date\
                    + timedelta(minutes=timed_delay)
                if fields.Datetime.now() < next_autoreply_time:
                    _logger.info(
                        "Skipping autoreply for %s - already"
                        " sent one recently",
                        sender_mobile
                    )
                    continue
            try:
                # Use the template directly since we're using whatsapp.template
                template = template_id

                # Send template message
                model_name = template.model_id.model
                composer_vals = {
                    'res_model': model_name,
                    'res_ids': str(channel.id),
                    'phone': sender_mobile,
                    'wa_template_id': template.id,
                    'batch_mode': False,
                }
                composer = self.env['whatsapp.composer']\
                    .with_context(active_model=model_name)\
                    .create(composer_vals)
                message = composer._create_whatsapp_messages(force_create=True)
                message._send()

                # Mark this message as an autoreply
                message.write({'is_autoreply': True})

                _logger.info(
                    "Sent autoreply template %s to %s",
                    template.name,
                    sender_mobile
                )

            except Exception as e:
                _logger.error(
                    "Failed to send autoreply to %s: %s",
                    sender_mobile, str(e)
                )
