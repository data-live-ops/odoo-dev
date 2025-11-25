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
        and ensure correct partner is linked to discuss channel
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
                sender_mobile = message.get('from')
                if not sender_mobile:
                    continue

                # Fix discuss channel partner if there are duplicates
                self._fix_channel_partner(sender_mobile)

                # Auto-add internal users as members to the channel
                self._ensure_channel_has_all_members(sender_mobile)

                # If message is a button, extract payload as message_body
                if message.get('type') == 'button' and message.get(
                    'button',
                    {},
                ).get('payload'):
                    message_body = message['button']['payload']
                else:
                    message_body = message.get('text', {}).get('body') or\
                        message.get('body')

                self.auto_create_ticket_from_whatsapp(
                    message_body,
                    sender_mobile
                )

        # Now handle autoreplies
        self._process_autoreplies(value)

        return result

    def _ensure_channel_has_all_members(self, sender_mobile):
        """
        UPDATED: Now assigns Lead Owner (1 user = 1 admin) instead of all internal users.

        This is called after a message is received to assign/add Lead Owner to channel.

        :param sender_mobile: str, the sender's phone number
        """
        try:
            # Find the channel for this phone number
            channel = self._find_active_channel(sender_mobile)
            if not channel:
                _logger.debug(f"[Lead Owner] No active channel found for {sender_mobile}")
                return

            # Find the best partner for this phone number
            partner = self._find_best_partner_by_phone(sender_mobile)

            # Call the method to add Lead Owner as member (1 user = 1 admin)
            channel._add_lead_owner_as_member(partner=partner)

        except Exception as e:
            _logger.warning(f"[Lead Owner] Failed to assign lead owner for {sender_mobile}: {e}")

    def _fix_channel_partner(self, sender_mobile):
        """
        Fix discuss channel partner when there are duplicate contacts.
        Ensures the channel uses the best partner match.

        :param sender_mobile: str, the sender's phone number
        """
        try:
            # Find the channel for this phone number
            channel = self._find_active_channel(sender_mobile)
            if not channel:
                _logger.debug(f"[Channel Fix] No active channel found for {sender_mobile}")
                return

            # Find best partner match
            best_partner = self._find_best_partner_by_phone(sender_mobile)
            if not best_partner:
                _logger.debug(f"[Channel Fix] No partner found for {sender_mobile}")
                return

            # Get current channel partner
            current_partners = channel.channel_partner_ids

            # If channel already has the correct partner, skip
            if best_partner in current_partners:
                _logger.debug(f"[Channel Fix] Channel already has correct partner: {best_partner.name}")
                return

            # Update channel to use best partner
            # Remove other partners with same phone and add the best one
            partners_to_remove = current_partners.filtered(
                lambda p: p.mobile == best_partner.mobile or p.phone == best_partner.phone
            )

            if partners_to_remove:
                channel.write({
                    'channel_partner_ids': [
                        (3, p.id) for p in partners_to_remove  # Remove duplicates
                    ] + [(4, best_partner.id)]  # Add best partner
                })
                _logger.info(
                    f"[Channel Fix] Updated channel {channel.id} to use partner: {best_partner.name} "
                    f"(removed {len(partners_to_remove)} duplicate(s))"
                )
            else:
                # No duplicates to remove, just add the best partner
                channel.write({
                    'channel_partner_ids': [(4, best_partner.id)]
                })
                _logger.info(f"[Channel Fix] Added partner {best_partner.name} to channel {channel.id}")

        except Exception as e:
            _logger.warning(f"[Channel Fix] Failed to fix channel partner for {sender_mobile}: {e}")

    def _normalize_phone_number(self, phone):
        """
        Normalize phone number to standard formats for matching
        Removes +, spaces, dashes and handles Indonesian format

        Returns list of possible formats:
        - 628xxx (WhatsApp format)
        - 08xxx (local format)
        - +628xxx (international format)
        - 8xxx (without leading 0)
        """
        if not phone:
            return []

        # Clean phone number
        cleaned = str(phone).replace('+', '').replace(' ', '').replace('-', '')

        formats = [cleaned]  # Original cleaned format

        # If starts with 628, add 08 and 8 variants
        if cleaned.startswith('628'):
            formats.append('0' + cleaned[2:])  # 08xxx
            formats.append(cleaned[2:])        # 8xxx
            formats.append('+' + cleaned)      # +628xxx
        # If starts with 08, add 628 and 8 variants
        elif cleaned.startswith('08'):
            formats.append('628' + cleaned[1:])  # 628xxx
            formats.append(cleaned[1:])          # 8xxx
            formats.append('+628' + cleaned[1:]) # +628xxx
        # If starts with 8 (no leading 0), add 08 and 628 variants
        elif cleaned.startswith('8') and not cleaned.startswith('08'):
            formats.append('0' + cleaned)      # 08xxx
            formats.append('628' + cleaned)    # 628xxx
            formats.append('+628' + cleaned)   # +628xxx

        _logger.info(f"[Phone Normalize] Input: {phone} → Formats: {formats}")
        return formats

    def _find_best_partner_by_phone(self, sender_mobile):
        """
        Find the best partner match when there are duplicates with same phone.
        Priority:
        1. Partner with metabase_student_id (most complete data)
        2. Partner that is a student (more likely to chat)
        3. Most recently updated partner

        :param sender_mobile: str, the sender's phone number
        :return: res.partner record or False
        """
        # Normalize phone number to multiple formats for matching
        phone_formats = self._normalize_phone_number(sender_mobile)

        _logger.info(f"[Partner Search] Searching partner with phone formats: {phone_formats}")

        # Search for ALL partners matching the phone (not just first one)
        all_partners = self.env['res.partner']
        for phone_format in phone_formats:
            partners = self.env['res.partner'].search([
                '|',
                ('mobile', '=', phone_format),
                ('phone', '=', phone_format),
            ])
            if partners:
                all_partners |= partners
                _logger.info(f"[Partner Search] Found {len(partners)} partner(s) with format: {phone_format}")

        if not all_partners:
            return False

        # If only one partner, return it
        if len(all_partners) == 1:
            _logger.info(f"[Partner Search] Single partner found: {all_partners.name}")
            return all_partners

        # Multiple partners found - select the best one
        _logger.warning(f"[Partner Search] Multiple partners found ({len(all_partners)}) for phone {sender_mobile}, selecting best match")

        # Priority 1: Partner with metabase_student_id (most complete)
        partners_with_student_id = all_partners.filtered(lambda p: p.metabase_student_id)
        if partners_with_student_id:
            best = partners_with_student_id.sorted(lambda p: p.write_date, reverse=True)[0]
            _logger.info(f"[Partner Search] Selected partner with student_id: {best.name} (ID: {best.id})")
            return best

        # Priority 2: Partner that is a student
        student_partners = all_partners.filtered(lambda p: p.contact_type == 'student' or p.is_student)
        if student_partners:
            best = student_partners.sorted(lambda p: p.write_date, reverse=True)[0]
            _logger.info(f"[Partner Search] Selected student partner: {best.name} (ID: {best.id})")
            return best

        # Priority 3: Most recently updated
        best = all_partners.sorted(lambda p: p.write_date, reverse=True)[0]
        _logger.info(f"[Partner Search] Selected most recent partner: {best.name} (ID: {best.id})")
        return best

    def auto_create_ticket_from_whatsapp(self, message_body, sender_mobile):
        """
        Auto-create a helpdesk ticket when receiving specific keyword.
        :param message_body: str, the WhatsApp message body
        :param sender_mobile: str, the sender's phone number (format: 628xxx from WhatsApp)
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

        # Use smart partner search to handle duplicates
        partner = self._find_best_partner_by_phone(sender_mobile)
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
                "[Ticket Creation] Skipping - open ticket already exists for %s",
                partner and partner.name or sender_mobile
            )
            return None  # Skip ticket creation

        ticket_vals = {
            'name': 'WhatsApp Ticket',
            'description': 'Ticket created from WhatsApp message.',
            'channel': 'whatsapp',
        }

        if partner:
            student_phase = partner.metabase_student_phase or 'Not Set'
            _logger.info(
                "[Ticket Creation] Partner found: %s (ID: %s, mobile: %s, phone: %s, student_phase: %s)",
                partner.name, partner.id, partner.mobile, partner.phone, student_phase
            )
            ticket_vals['partner_id'] = partner.id
            ticket_vals['partner_phone'] = partner.phone or partner.mobile

            # If partner has no student_phase, set it to non_paid
            if not partner.metabase_student_phase:
                _logger.warning(
                    "[Ticket Creation] Partner %s has no student_phase, setting to 'non_paid'",
                    partner.name
                )
                partner.write({'metabase_student_phase': 'non_paid'})
        else:
            _logger.warning("[Ticket Creation] Partner not found for phone: %s, will default to non_paid", sender_mobile)
            # Create partner with non_paid student_phase as default
            partner = self.env['res.partner'].create({
                'name': f'WhatsApp User {sender_mobile[-4:]}',
                'mobile': sender_mobile,
                'metabase_student_phase': 'non_paid',
                'contact_type': 'student',
                'is_student': True,
            })
            _logger.info(
                "[Ticket Creation] Created new partner: %s (ID: %s) with student_phase: non_paid",
                partner.name, partner.id
            )
            ticket_vals['partner_id'] = partner.id
            ticket_vals['partner_phone'] = sender_mobile

        ticket_vals['description'] += f"\nPhone: {sender_mobile}"

        _logger.info("[Ticket Creation] Creating ticket with values: %s", ticket_vals)
        ticket = self.env['helpdesk.ticket'].create(ticket_vals)
        _logger.info("[Ticket Creation] Ticket created: ID=%s, Name=%s, Student Phase=%s",
                    ticket.id, ticket.name, ticket.student_phase or 'Not Set')

        # Auto-assign based on student phase
        ticket.assign_user_based_on_student_phase()

        _logger.info("[Ticket Creation] Final assignment - Team: %s, User: %s",
                    ticket.team_id.name if ticket.team_id else 'Not Assigned',
                    ticket.user_id.name if ticket.user_id else 'Not Assigned')
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
