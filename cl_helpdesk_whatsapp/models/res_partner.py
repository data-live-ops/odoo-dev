from odoo import api, fields, models

import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # NOTE: lead_owner_id field will be added after column is created in database
    # For now, we use helper methods to safely access the column if it exists

    def _get_whatsapp_team_by_phase(self):
        """
        Get the WhatsApp team based on student phase.
        Finds a team that has BOTH:
        - is_whatsapp_team = True
        - matching student phase (non_paid/new/paid)

        Returns:
            helpdesk.team record or False
        """
        self.ensure_one()
        student_phase = self.metabase_student_phase or 'non_paid'

        # Build domain: WhatsApp team + student phase
        domain = [('is_whatsapp_team', '=', True)]

        if student_phase == 'non_paid':
            domain.append(('non_paid_student', '=', True))
        elif student_phase == 'new':
            domain.append(('new_student', '=', True))
        elif student_phase == 'paid':
            domain.append(('paid_student', '=', True))
        else:
            # Default to non_paid
            domain.append(('non_paid_student', '=', True))

        team = self.env['helpdesk.team'].search(domain, limit=1)

        if team:
            _logger.info(
                f"[Lead Owner] Found WhatsApp team '{team.name}' "
                f"for student_phase '{student_phase}'"
            )
        else:
            _logger.debug(
                f"[Lead Owner] No WhatsApp team found for student_phase '{student_phase}'"
            )

        return team

    def _get_any_whatsapp_team(self):
        """
        Get any WhatsApp team (fallback if no phase-specific team found).

        Returns:
            helpdesk.team record or False
        """
        team = self.env['helpdesk.team'].search([
            ('is_whatsapp_team', '=', True)
        ], limit=1)

        if team:
            _logger.info(f"[Lead Owner] Found WhatsApp team (fallback): '{team.name}'")

        return team

    def _assign_lead_owner(self):
        """
        Assign a Lead Owner to this partner.

        Priority:
        1. WhatsApp Team matching student phase (is_whatsapp_team + phase)
        2. Any WhatsApp Team (fallback)

        Uses round-robin assignment from the team members.

        Returns:
            res.users record or False
        """
        self.ensure_one()

        # Priority 1: Get WhatsApp team matching student phase
        team = self._get_whatsapp_team_by_phase()

        # Priority 2: Fallback to any WhatsApp team
        if not team:
            _logger.info(
                f"[Lead Owner] No phase-specific WhatsApp team for '{self.metabase_student_phase}', "
                "trying any WhatsApp team"
            )
            team = self._get_any_whatsapp_team()

        if not team:
            _logger.warning(
                f"[Lead Owner] Cannot assign lead owner for {self.name}: no WhatsApp team found. "
                "Please configure WhatsApp teams (Helpdesk > Configuration > Teams > check 'WhatsApp Team')"
            )
            return False

        if not team.member_ids:
            _logger.warning(
                f"[Lead Owner] Team '{team.name}' has no members. "
                "Please add team members to enable WhatsApp assignment."
            )
            return False

        # Try Odoo's built-in assignment method first
        try:
            user_dict = team._determine_user_to_assign()
            assigned_user_id = user_dict.get(team.id)

            if assigned_user_id:
                assigned_user = self.env['res.users'].browse(assigned_user_id)
                _logger.info(
                    f"[Lead Owner] Assigned {assigned_user.name} as lead owner for {self.name} "
                    f"(team: {team.name}, phase: {self.metabase_student_phase})"
                )
                return assigned_user
        except Exception as e:
            _logger.warning(
                f"[Lead Owner] _determine_user_to_assign failed: {e}. Using fallback."
            )

        # Fallback: Custom round-robin from team members
        # Count WhatsApp channels assigned to each member and pick the one with least
        members = team.member_ids
        if members:
            member_channel_counts = []

            for member in members:
                # Count how many WhatsApp channels this member is assigned to
                channel_count = self.env['discuss.channel.member'].sudo().search_count([
                    ('partner_id', '=', member.partner_id.id),
                    ('channel_id.channel_type', '=', 'whatsapp'),
                ])
                member_channel_counts.append((member, channel_count))
                _logger.debug(
                    f"[Lead Owner] Member {member.name} has {channel_count} WhatsApp channels"
                )

            # Sort by channel count (ascending) and pick the one with least channels
            member_channel_counts.sort(key=lambda x: x[1])
            assigned_user = member_channel_counts[0][0]

            _logger.info(
                f"[Lead Owner] Round-robin assigned {assigned_user.name} as lead owner for {self.name} "
                f"(team: {team.name}, phase: {self.metabase_student_phase}, "
                f"current channels: {member_channel_counts[0][1]})"
            )
            return assigned_user

        _logger.warning(
            f"[Lead Owner] Team '{team.name}' could not determine user to assign. "
            "Check team assignment settings."
        )
        return False

    def _get_or_assign_lead_owner(self):
        """
        Get existing Lead Owner or assign a new one.
        Note: Currently always assigns new (no persistence without lead_owner_id field)

        Returns:
            res.users record or False
        """
        self.ensure_one()
        return self._assign_lead_owner()

    @api.onchange('phone', 'country_id', 'company_id')
    def _onchange_phone_validation(self):
        """ Replace, disable method because disturb phone number in partner """
        return

    @api.onchange('mobile', 'country_id', 'company_id')
    def _onchange_mobile_validation(self):
        """ Replace, disable method because disturb phone number in partner """
        return
    
    def _find_or_create_from_number(self, number, name=False):
        """ Super, assign phone number from mobile if phone is empty """
        res = super(ResPartner, self)._find_or_create_from_number(number, name)
        if res and not res.phone:
            res.phone = res.mobile
        return res
