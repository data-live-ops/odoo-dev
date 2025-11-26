from odoo import api, fields, models

import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # NOTE: lead_owner_id field will be added after column is created in database
    # For now, we use helper methods to safely access the column if it exists

    def _get_whatsapp_team(self):
        """
        Get the WhatsApp team for channel assignment.
        This is the PRIMARY method for WhatsApp channel admin assignment.

        Returns:
            helpdesk.team record or False
        """
        team = self.env['helpdesk.team'].search([
            ('is_whatsapp_team', '=', True)
        ], limit=1)

        if team:
            _logger.info(f"[Lead Owner] Found WhatsApp team: '{team.name}'")
        else:
            _logger.warning("[Lead Owner] No WhatsApp team configured (is_whatsapp_team=True)")

        return team

    def _get_team_by_student_phase(self):
        """
        Get the helpdesk team based on student phase configuration.
        FALLBACK method - only used if no WhatsApp team is configured.

        Returns:
            helpdesk.team record or False
        """
        self.ensure_one()
        student_phase = self.metabase_student_phase or 'non_paid'

        domain = []
        if student_phase == 'non_paid':
            domain = [('non_paid_student', '=', True)]
        elif student_phase == 'new':
            domain = [('new_student', '=', True)]
        elif student_phase == 'paid':
            domain = [('paid_student', '=', True)]
        else:
            # Default to non_paid team if unknown phase
            domain = [('non_paid_student', '=', True)]

        team = self.env['helpdesk.team'].search(domain, limit=1)

        if team:
            _logger.info(
                f"[Lead Owner] Found team '{team.name}' for student_phase '{student_phase}'"
            )
        else:
            _logger.warning(
                f"[Lead Owner] No team found for student_phase '{student_phase}'"
            )

        return team

    def _assign_lead_owner(self):
        """
        Assign a Lead Owner to this partner.

        Priority:
        1. WhatsApp Team (is_whatsapp_team=True) - RECOMMENDED
        2. Student Phase Team (fallback)

        Uses round-robin assignment from the team members.

        Returns:
            res.users record or False
        """
        self.ensure_one()

        # Priority 1: Get WhatsApp team
        team = self._get_whatsapp_team()

        # Priority 2: Fallback to student phase team
        if not team:
            _logger.info("[Lead Owner] No WhatsApp team, falling back to student phase team")
            team = self._get_team_by_student_phase()

        if not team:
            _logger.warning(
                f"[Lead Owner] Cannot assign lead owner for {self.name}: no team found. "
                "Please configure a WhatsApp team (Helpdesk > Configuration > Teams > check 'WhatsApp Team')"
            )
            return False

        if not team.member_ids:
            _logger.warning(
                f"[Lead Owner] Team '{team.name}' has no members. "
                "Please add team members to enable WhatsApp assignment."
            )
            return False

        # Use Odoo's built-in assignment method (respects round-robin/balanced settings)
        user_dict = team._determine_user_to_assign()
        assigned_user_id = user_dict.get(team.id)

        if assigned_user_id:
            assigned_user = self.env['res.users'].browse(assigned_user_id)
            _logger.info(
                f"[Lead Owner] Assigned {assigned_user.name} as lead owner for {self.name} "
                f"(team: {team.name})"
            )
            return assigned_user
        else:
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
