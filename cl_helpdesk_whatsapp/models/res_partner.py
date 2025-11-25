from odoo import api, fields, models

import logging

_logger = logging.getLogger(__name__)


def _check_lead_owner_column_exists(cr):
    """Check if lead_owner_id column exists in res_partner table."""
    cr.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'res_partner'
        AND column_name = 'lead_owner_id'
    """)
    return cr.fetchone() is not None


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _setup_fields(self):
        """Override to conditionally add lead_owner_id field."""
        super()._setup_fields()
        # Field will be added after column is created via upgrade

    def _get_lead_owner_id(self):
        """Safely get lead_owner_id if the column exists."""
        self.ensure_one()
        if not _check_lead_owner_column_exists(self.env.cr):
            return False
        # Use raw SQL to avoid field not found error
        self.env.cr.execute(
            "SELECT lead_owner_id FROM res_partner WHERE id = %s",
            (self.id,)
        )
        result = self.env.cr.fetchone()
        if result and result[0]:
            return self.env['res.users'].browse(result[0])
        return False

    def _set_lead_owner_id(self, user):
        """Safely set lead_owner_id if the column exists."""
        self.ensure_one()
        if not _check_lead_owner_column_exists(self.env.cr):
            _logger.warning("[Lead Owner] Column lead_owner_id does not exist yet")
            return False
        user_id = user.id if user else None
        self.env.cr.execute(
            "UPDATE res_partner SET lead_owner_id = %s WHERE id = %s",
            (user_id, self.id)
        )
        return True

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

        # Skip if already has a lead owner
        existing_owner = self._get_lead_owner_id()
        if existing_owner:
            _logger.debug(
                f"[Lead Owner] Partner {self.name} already has lead owner: {existing_owner.name}"
            )
            return existing_owner

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
            self._set_lead_owner_id(assigned_user)
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

        Returns:
            res.users record or False
        """
        self.ensure_one()

        existing_owner = self._get_lead_owner_id()
        if existing_owner:
            return existing_owner

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
