from odoo import api, fields, models, tools
import logging

_logger = logging.getLogger(__name__)


class WhatsAppChannelMonitor(models.Model):
    """
    SQL View model to monitor WhatsApp channels and their assigned admins.
    Provides visibility into which customer is handled by which admin.
    """
    _name = 'whatsapp.channel.monitor'
    _description = 'WhatsApp Channel Monitor'
    _auto = False
    _order = 'last_message_date desc'

    channel_id = fields.Many2one('discuss.channel', string='Channel', readonly=True)
    channel_name = fields.Char(string='Channel Name', readonly=True)
    customer_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    customer_phone = fields.Char(string='Customer Phone', readonly=True)
    student_phase = fields.Char(string='Student Phase', readonly=True)
    admin_id = fields.Many2one('res.partner', string='Assigned Admin', readonly=True)
    admin_user_id = fields.Many2one('res.users', string='Admin User', readonly=True)
    admin_count = fields.Integer(string='Total Admins', readonly=True)
    member_count = fields.Integer(string='Total Members', readonly=True)
    create_date = fields.Datetime(string='Channel Created', readonly=True)
    last_message_date = fields.Datetime(string='Last Message', readonly=True)

    def init(self):
        """Create the SQL view for WhatsApp channel monitoring."""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH channel_customers AS (
                    -- Get customer (non-internal user) for each channel
                    SELECT
                        dc.id as channel_id,
                        dc.name as channel_name,
                        dc.create_date,
                        rp.id as customer_id,
                        COALESCE(rp.phone, rp.mobile) as customer_phone,
                        rp.metabase_student_phase as student_phase
                    FROM discuss_channel dc
                    JOIN discuss_channel_member dcm ON dcm.channel_id = dc.id
                    JOIN res_partner rp ON rp.id = dcm.partner_id
                    LEFT JOIN res_users ru ON ru.partner_id = rp.id AND ru.active = true AND ru.share = false
                    WHERE dc.channel_type = 'whatsapp'
                    AND ru.id IS NULL  -- Customer = partner without internal user
                ),
                channel_admins AS (
                    -- Get first admin (internal user) for each channel
                    SELECT DISTINCT ON (dc.id)
                        dc.id as channel_id,
                        rp.id as admin_id,
                        ru.id as admin_user_id
                    FROM discuss_channel dc
                    JOIN discuss_channel_member dcm ON dcm.channel_id = dc.id
                    JOIN res_partner rp ON rp.id = dcm.partner_id
                    JOIN res_users ru ON ru.partner_id = rp.id AND ru.active = true AND ru.share = false
                    WHERE dc.channel_type = 'whatsapp'
                    ORDER BY dc.id, dcm.create_date ASC
                ),
                channel_stats AS (
                    -- Count admins and total members per channel
                    SELECT
                        dc.id as channel_id,
                        COUNT(CASE WHEN ru.id IS NOT NULL THEN 1 END) as admin_count,
                        COUNT(dcm.id) as member_count
                    FROM discuss_channel dc
                    JOIN discuss_channel_member dcm ON dcm.channel_id = dc.id
                    JOIN res_partner rp ON rp.id = dcm.partner_id
                    LEFT JOIN res_users ru ON ru.partner_id = rp.id AND ru.active = true AND ru.share = false
                    WHERE dc.channel_type = 'whatsapp'
                    GROUP BY dc.id
                ),
                channel_last_message AS (
                    -- Get last message date per channel
                    SELECT
                        mm.res_id as channel_id,
                        MAX(mm.date) as last_message_date
                    FROM mail_message mm
                    WHERE mm.model = 'discuss.channel'
                    AND mm.message_type IN ('comment', 'whatsapp_message')
                    GROUP BY mm.res_id
                )
                SELECT
                    cc.channel_id as id,
                    cc.channel_id,
                    cc.channel_name,
                    cc.customer_id,
                    cc.customer_phone,
                    cc.student_phase,
                    ca.admin_id,
                    ca.admin_user_id,
                    COALESCE(cs.admin_count, 0) as admin_count,
                    COALESCE(cs.member_count, 0) as member_count,
                    cc.create_date,
                    clm.last_message_date
                FROM channel_customers cc
                LEFT JOIN channel_admins ca ON ca.channel_id = cc.channel_id
                LEFT JOIN channel_stats cs ON cs.channel_id = cc.channel_id
                LEFT JOIN channel_last_message clm ON clm.channel_id = cc.channel_id
            )
        """ % self._table)

    def action_open_channel(self):
        """Open the discuss channel."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'discuss.channel',
            'res_id': self.channel_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_customer(self):
        """Open the customer partner form."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': self.customer_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_reset_and_reassign(self):
        """
        Reset channel members: remove all admins and reassign only 1 admin.
        Can be called on single or multiple records.
        """
        channels_reset = 0
        channels_failed = 0

        for record in self:
            try:
                channel = record.channel_id
                customer = record.customer_id

                if not channel or not customer:
                    _logger.warning(f"[Reset] Skipping record {record.id}: missing channel or customer")
                    channels_failed += 1
                    continue

                # Get all admin members (internal users) in this channel
                admin_members = channel.sudo().channel_member_ids.filtered(
                    lambda m: m.partner_id.user_ids and
                              any(u.active and not u.share for u in m.partner_id.user_ids)
                )

                if admin_members:
                    _logger.info(
                        f"[Reset] Channel {channel.id}: Removing {len(admin_members)} admin(s)"
                    )
                    # Remove admin members
                    admin_members.sudo().unlink()

                # Reassign new lead owner
                lead_owner = customer._get_or_assign_lead_owner()

                if lead_owner:
                    # Add new lead owner as member
                    channel.sudo().add_members(partner_ids=[lead_owner.partner_id.id])
                    _logger.info(
                        f"[Reset] Channel {channel.id}: Assigned {lead_owner.name} as new admin"
                    )
                    channels_reset += 1
                else:
                    _logger.warning(
                        f"[Reset] Channel {channel.id}: Could not assign new lead owner"
                    )
                    channels_failed += 1

            except Exception as e:
                _logger.error(f"[Reset] Error processing channel {record.id}: {e}")
                channels_failed += 1

        # Return notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Reset Complete',
                'message': f'Reset {channels_reset} channel(s). Failed: {channels_failed}',
                'type': 'success' if channels_failed == 0 else 'warning',
                'sticky': False,
            }
        }

    def action_reset_all_channels(self):
        """
        Reset ALL WhatsApp channels - remove all admins and reassign based on new logic.
        This is a bulk operation for cleaning up existing channels.
        """
        # Get all monitor records
        all_records = self.search([])
        _logger.info(f"[Reset All] Starting reset for {len(all_records)} channels")
        return all_records.action_reset_and_reassign()
