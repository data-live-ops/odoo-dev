from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class DiscussChannel(models.Model):
    """Extend Discuss Channel to auto-add members for WhatsApp channels"""
    _inherit = 'discuss.channel'

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to automatically add all internal users as members
        when a WhatsApp channel is created.

        This ensures all team members can see WhatsApp conversations
        without manual invitation.
        """
        channels = super().create(vals_list)

        # Process each created channel
        for channel in channels:
            if channel.channel_type == 'whatsapp':
                self._auto_add_internal_users_as_members(channel)

        return channels

    def _auto_add_internal_users_as_members(self, channel):
        """
        Automatically add all internal users (non-portal users) as members
        of the WhatsApp channel.

        This allows all CS/support staff to see and respond to
        WhatsApp conversations.

        :param channel: discuss.channel record (WhatsApp channel)
        """
        try:
            # Find all internal users (non-portal, active users)
            internal_users = self.env['res.users'].search([
                ('share', '=', False),  # Internal users only (not portal/external)
                ('active', '=', True),
            ])

            if not internal_users:
                _logger.warning(
                    "[WhatsApp Channel] No internal users found to add as members"
                )
                return

            # Get existing channel member partner IDs
            existing_partner_ids = channel.channel_member_ids.mapped('partner_id').ids

            # Filter users whose partners are not already members
            partners_to_add = internal_users.mapped('partner_id').filtered(
                lambda p: p.id not in existing_partner_ids
            )

            if partners_to_add:
                # Add partners as channel members using Odoo 18 API
                partner_ids = partners_to_add.ids
                try:
                    channel.add_members(partner_ids=partner_ids)
                    _logger.info(
                        f"[WhatsApp Channel] Auto-added {len(partners_to_add)} internal users "
                        f"as members to channel {channel.id} (phone: {channel.whatsapp_number})"
                    )
                except Exception as e:
                    _logger.error(
                        f"[WhatsApp Channel] Failed to add members to channel {channel.id}: {e}",
                        exc_info=True
                    )
            else:
                _logger.debug(
                    f"[WhatsApp Channel] All internal users are already members "
                    f"of channel {channel.id}"
                )
        except Exception as e:
            # Catch any unexpected errors during the whole process
            _logger.error(
                f"[WhatsApp Channel] Unexpected error in auto-add members: {e}",
                exc_info=True
            )

    def write(self, vals):
        """
        Override write to handle member updates if needed in the future.
        Currently just calls super.
        """
        return super().write(vals)

    def _cron_add_internal_users_to_whatsapp_channels(self):
        """
        Scheduled action to add all internal users as members
        to existing WhatsApp channels.

        This is useful for bulk updating existing channels.
        Can be run manually via Settings → Technical → Automation → Scheduled Actions
        """
        _logger.info("[WhatsApp Channel Cron] Starting bulk member addition to WhatsApp channels")

        # Get all WhatsApp channels
        channels = self.search([('channel_type', '=', 'whatsapp')])
        _logger.info(f"[WhatsApp Channel Cron] Found {len(channels)} WhatsApp channels")

        if not channels:
            _logger.info("[WhatsApp Channel Cron] No WhatsApp channels found")
            return

        # Get all internal users
        internal_users = self.env['res.users'].search([
            ('share', '=', False),
            ('active', '=', True),
        ])
        _logger.info(f"[WhatsApp Channel Cron] Found {len(internal_users)} internal users")

        if not internal_users:
            _logger.warning("[WhatsApp Channel Cron] No internal users found")
            return

        # Process each channel
        channels_updated = 0
        members_added_total = 0

        for channel in channels:
            try:
                # Get existing members
                existing_partners = channel.channel_member_ids.mapped('partner_id')

                # Find partners to add
                partners_to_add = internal_users.mapped('partner_id').filtered(
                    lambda p: p not in existing_partners
                )

                if partners_to_add:
                    # Add members
                    channel.add_members(partner_ids=partners_to_add.ids)
                    channels_updated += 1
                    members_added_total += len(partners_to_add)

                    _logger.info(
                        f"[WhatsApp Channel Cron] Channel {channel.id} ({channel.name}): "
                        f"Added {len(partners_to_add)} members"
                    )
                else:
                    _logger.debug(
                        f"[WhatsApp Channel Cron] Channel {channel.id} ({channel.name}): "
                        f"Already has all members"
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
            f"added {members_added_total} members total"
        )
