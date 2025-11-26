from odoo import api, fields, models

import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # NOTE: lead_owner_id field will be added after column is created in database
    # For now, we use helper methods to safely access the column if it exists

    def _get_team_by_student_phase(self):
        """
        Get the helpdesk team based on student phase configuration.

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
        Assign a Lead Owner to this partner based on student phase.
        Uses round-robin assignment from the appropriate helpdesk team members.

        Returns:
            res.users record or False
        """
        self.ensure_one()

        # Get team based on student phase
        team = self._get_team_by_student_phase()

        if not team:
            _logger.warning(
                f"[Lead Owner] Cannot assign lead owner for {self.name}: no team found"
            )
            return False

        if not team.member_ids:
            _logger.warning(
                f"[Lead Owner] Team '{team.name}' has no members"
            )
            return False

        # Use Odoo's built-in assignment method (respects round-robin/balanced settings)
        user_dict = team._determine_user_to_assign()
        assigned_user_id = user_dict.get(team.id)

        if assigned_user_id:
            assigned_user = self.env['res.users'].browse(assigned_user_id)
            _logger.info(
                f"[Lead Owner] Assigned {assigned_user.name} as lead owner for {self.name} "
                f"(team: {team.name}, student_phase: {self.metabase_student_phase})"
            )
            return assigned_user
        else:
            _logger.warning(
                f"[Lead Owner] Team '{team.name}' could not determine user to assign"
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
