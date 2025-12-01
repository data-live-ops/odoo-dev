from odoo import models, api, Command, tools, _
from markupsafe import Markup
import logging

_logger = logging.getLogger(__name__)


class DiscussChannel(models.Model):
    """Extend Discuss Channel to auto-add members for WhatsApp channels"""
    _inherit = 'discuss.channel'

    def _get_customer_partner_from_channel(self):
        """
        Get the customer (non-internal user) partner from a WhatsApp channel.

        Returns:
            res.partner record or False
        """
        self.ensure_one()

        # Get all partners in this channel
        channel_partners = self.channel_partner_ids

        # Find the customer (non-internal user partner)
        for partner in channel_partners:
            # Check if this partner is NOT linked to an internal user
            user = self.env['res.users'].search([
                ('partner_id', '=', partner.id),
                ('share', '=', False),  # Internal user
                ('active', '=', True),
            ], limit=1)

            if not user:
                # This partner is not an internal user, so it's the customer
                return partner

        return False

    def _get_existing_admin_from_channel(self):
        """
        Get the existing admin (internal user) from this channel if any.

        Returns:
            res.users record or False
        """
        self.ensure_one()

        for member in self.channel_member_ids:
            partner = member.partner_id
            # Check if this partner is an internal user
            user = self.env['res.users'].sudo().search([
                ('partner_id', '=', partner.id),
                ('share', '=', False),  # Internal user
                ('active', '=', True),
            ], limit=1)

            if user:
                return user

        return False

    def _add_lead_owner_as_member(self, partner=None):
        """
        Add only the Lead Owner as member to the WhatsApp channel.
        This replaces the old method that added ALL internal users.

        IMPORTANT: If channel already has an admin, DO NOT add another one.
        1 User = 1 Admin (Lead Owner)

        Args:
            partner: res.partner record of the customer (optional, will auto-detect)

        Returns:
            res.users record of the Lead Owner or False
        """
        for channel in self:
            if channel.channel_type != 'whatsapp':
                continue

            try:
                # IMPORTANT: Check if channel already has an admin
                existing_admin = channel._get_existing_admin_from_channel()
                if existing_admin:
                    _logger.debug(
                        f"[WhatsApp Channel] Channel {channel.id} already has admin "
                        f"{existing_admin.name}, skipping new assignment"
                    )
                    return existing_admin

                # Get customer partner from channel if not provided
                customer_partner = partner or channel._get_customer_partner_from_channel()

                if not customer_partner:
                    _logger.warning(
                        f"[WhatsApp Channel] No customer partner found for channel {channel.id}"
                    )
                    continue

                # Get or assign Lead Owner for this customer
                lead_owner = customer_partner._get_or_assign_lead_owner()

                if not lead_owner:
                    _logger.warning(
                        f"[WhatsApp Channel] Could not get/assign lead owner for "
                        f"partner {customer_partner.name} (channel {channel.id})"
                    )
                    continue

                # Check if Lead Owner is already a member
                existing_member_partners = channel.sudo().channel_member_ids.mapped('partner_id')
                existing_partner_ids = set(existing_member_partners.ids)

                lead_owner_partner = lead_owner.partner_id

                if lead_owner_partner.id in existing_partner_ids:
                    _logger.debug(
                        f"[WhatsApp Channel] Lead Owner {lead_owner.name} is already "
                        f"a member of channel {channel.id}"
                    )
                    return lead_owner

                # Add Lead Owner as member
                try:
                    channel.sudo().add_members(partner_ids=[lead_owner_partner.id])
                    _logger.info(
                        f"[WhatsApp Channel] Added Lead Owner {lead_owner.name} "
                        f"to channel {channel.id} for customer {customer_partner.name}"
                    )
                    return lead_owner
                except Exception as e:
                    _logger.error(
                        f"[WhatsApp Channel] Failed to add Lead Owner to channel {channel.id}: {e}",
                        exc_info=True
                    )
                    return False

            except Exception as e:
                _logger.error(
                    f"[WhatsApp Channel] Unexpected error in _add_lead_owner_as_member "
                    f"for channel {channel.id}: {e}",
                    exc_info=True
                )

        return False

    def _auto_add_internal_users_as_members(self):
        """
        DEPRECATED: This method now calls _add_lead_owner_as_member instead.

        Previously added ALL internal users to the channel (caused spam).
        Now only adds the Lead Owner (1 user = 1 admin).
        """
        _logger.info(
            "[WhatsApp Channel] _auto_add_internal_users_as_members called, "
            "redirecting to _add_lead_owner_as_member"
        )
        return self._add_lead_owner_as_member()

    def write(self, vals):
        """
        Override write to handle member updates if needed in the future.
        Currently just calls super.
        """
        return super().write(vals)

    def _cron_add_internal_users_to_whatsapp_channels(self):
        """
        Scheduled action to assign Lead Owners to WhatsApp channels.

        UPDATED: Now assigns Lead Owner (1 user = 1 admin) instead of all internal users.

        This is useful for bulk updating existing channels that don't have Lead Owners.
        Can be run manually via Settings → Technical → Automation → Scheduled Actions
        """
        _logger.info("[WhatsApp Channel Cron] Starting Lead Owner assignment to WhatsApp channels")

        # Get all WhatsApp channels
        channels = self.search([('channel_type', '=', 'whatsapp')])
        _logger.info(f"[WhatsApp Channel Cron] Found {len(channels)} WhatsApp channels")

        if not channels:
            _logger.info("[WhatsApp Channel Cron] No WhatsApp channels found")
            return

        # Process each channel
        channels_updated = 0
        lead_owners_assigned = 0

        for channel in channels:
            try:
                # Get customer partner from channel
                customer_partner = channel._get_customer_partner_from_channel()

                if not customer_partner:
                    _logger.debug(
                        f"[WhatsApp Channel Cron] Channel {channel.id}: No customer partner found"
                    )
                    continue

                # Skip check for existing lead owner since field doesn't exist yet
                # Just proceed to add lead owner as member

                # Add Lead Owner as member
                lead_owner = channel._add_lead_owner_as_member(partner=customer_partner)

                if lead_owner:
                    channels_updated += 1
                    lead_owners_assigned += 1
                    _logger.info(
                        f"[WhatsApp Channel Cron] Channel {channel.id} ({channel.name}): "
                        f"Assigned Lead Owner {lead_owner.name}"
                    )

            except Exception as e:
                _logger.error(
                    f"[WhatsApp Channel Cron] Failed to process channel {channel.id}: {e}",
                    exc_info=True
                )
                continue

        _logger.info(
            f"[WhatsApp Channel Cron] Completed! "
            f"Updated {channels_updated} channels, "
            f"assigned {lead_owners_assigned} Lead Owners"
        )

    @api.returns('self')
    def _get_whatsapp_channel(self, whatsapp_number, wa_account_id, sender_name=False, create_if_not_found=False, related_message=False):
        """
        OVERRIDE: Replace notify_user_ids with WhatsApp Team member assignment.

        Instead of using wa_account_id.notify_user_ids (Default Users in WhatsApp Account),
        we use our custom WhatsApp Team assignment based on student phase.
        """
        from odoo.addons.whatsapp.tools import phone_validation as wa_phone_validation

        # Normalize phone number (same as original)
        base_number = whatsapp_number if whatsapp_number.startswith('+') else f'+{whatsapp_number}'
        wa_number = base_number.lstrip('+')
        wa_formatted = wa_phone_validation.wa_phone_format(
            self.env.company,
            number=base_number,
            force_format="WHATSAPP",
            raise_exception=False,
        ) or wa_number

        related_record = False
        responsible_partners = self.env['res.partner']
        channel_domain = [
            ('whatsapp_number', '=', wa_formatted),
            ('wa_account_id', '=', wa_account_id.id)
        ]
        if related_message:
            related_record = self.env[related_message.model].browse(related_message.res_id)
            responsible_partners = related_record._whatsapp_get_responsible(
                related_message=related_message,
                related_record=related_record,
                whatsapp_account=wa_account_id,
            ).partner_id

        channel = self.sudo().search(channel_domain, order='create_date desc', limit=1)
        if responsible_partners:
            channel = channel.filtered(lambda c: all(r in c.channel_member_ids.partner_id for r in responsible_partners))

        partners_to_notify = responsible_partners
        record_name = related_message.record_name if related_message else False
        if related_message and not record_name and related_message.res_id:
            record_name = self.env[related_message.model].browse(related_message.res_id).display_name

        if not channel and create_if_not_found:
            # Find or create partner for this WhatsApp number
            whatsapp_partner = self.env['res.partner']._find_or_create_from_number(wa_formatted, sender_name)

            channel = self.sudo().with_context(tools.clean_context(self.env.context)).create({
                'name': f"{wa_formatted} ({record_name})" if record_name else wa_formatted,
                'channel_type': 'whatsapp',
                'whatsapp_number': wa_formatted,
                'whatsapp_partner_id': whatsapp_partner.id,
                'wa_account_id': wa_account_id.id,
            })
            partners_to_notify |= whatsapp_partner

            if related_message:
                # Add message in channel about the related document
                info = _("Related %(model_name)s: ", model_name=self.env['ir.model']._get(related_message.model).display_name)
                url = Markup('{base_url}/odoo/{model}/{res_id}').format(
                    base_url=self.get_base_url(), model=related_message.model, res_id=related_message.res_id)
                related_record_name = related_message.record_name
                if not related_record_name:
                    related_record_name = self.env[related_message.model].browse(related_message.res_id).display_name
                channel.message_post(
                    body=Markup('<p>{info}<a target="_blank" href="{url}">{related_record_name}</a></p>').format(
                        info=info, url=url, related_record_name=related_record_name),
                    message_type='comment',
                    author_id=self.env.ref('base.partner_root').id,
                    subtype_xmlid='mail.mt_note',
                )
                if hasattr(related_record, 'message_post'):
                    # Add notification in document about the new message and related channel
                    info = _("A new WhatsApp channel is created for this document")
                    url = Markup('{base_url}/odoo/discuss.channel/{channel_id}').format(
                        base_url=self.get_base_url(), channel_id=channel.id)
                    related_record.message_post(
                        author_id=self.env.ref('base.partner_root').id,
                        body=Markup('<p>{info} <a target="_blank" class="o_whatsapp_channel_redirect"'
                                    'data-oe-id="{channel_id}" href="{url}">{channel_name}</a></p>').format(
                                        info=info, url=url, channel_id=channel.id, channel_name=channel.display_name),
                        message_type='comment',
                        subtype_xmlid='mail.mt_note',
                    )

            # ============================================================
            # CUSTOM: Use WhatsApp Team assignment instead of notify_user_ids
            # ============================================================
            # Get Lead Owner from WhatsApp Team based on student phase
            lead_owner = whatsapp_partner._get_or_assign_lead_owner()

            if lead_owner:
                # Add Lead Owner's partner to notification list
                partners_to_notify |= lead_owner.partner_id
                _logger.info(
                    f"[WhatsApp Channel] New channel {channel.id}: "
                    f"Assigned Lead Owner {lead_owner.name} from WhatsApp Team "
                    f"(student phase: {whatsapp_partner.metabase_student_phase or 'not set'})"
                )
            else:
                # Fallback to notify_user_ids only if no WhatsApp Team configured
                _logger.warning(
                    f"[WhatsApp Channel] New channel {channel.id}: "
                    f"No WhatsApp Team found, falling back to notify_user_ids"
                )
                if partners_to_notify == channel.whatsapp_partner_id and wa_account_id.notify_user_ids.partner_id:
                    partners_to_notify |= wa_account_id.notify_user_ids.partner_id

            # Set channel members
            channel.channel_member_ids = [Command.clear()] + [Command.create({'partner_id': partner.id}) for partner in partners_to_notify]
            channel._broadcast(partners_to_notify.ids)

        return channel
