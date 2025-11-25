from odoo import models, api
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

    def _add_lead_owner_as_member(self, partner=None):
        """
        Add only the Lead Owner as member to the WhatsApp channel.
        This replaces the old method that added ALL internal users.

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

                # Check if already has lead owner as member
                if customer_partner.lead_owner_id:
                    lead_owner_partner = customer_partner.lead_owner_id.partner_id
                    existing_members = channel.channel_member_ids.mapped('partner_id')

                    if lead_owner_partner in existing_members:
                        _logger.debug(
                            f"[WhatsApp Channel Cron] Channel {channel.id}: "
                            f"Lead Owner {customer_partner.lead_owner_id.name} already member"
                        )
                        continue

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
