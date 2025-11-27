from odoo import _, api, fields, models


class HelpdeskTicket(models.Model):
    """ Inherit Helpdesk Ticket """

    _inherit = "helpdesk.ticket"

    user_id = fields.Many2one(
        tracking=True,
    )
    partner_id = fields.Many2one(
        tracking=True,
    )
    partner_phone = fields.Char(
        required=True,
        tracking=True,
    )
    email_cc = fields.Char()
    student_phase = fields.Selection(
        related='partner_id.metabase_student_phase',
        store=True,
    )
    initiated_by = fields.Selection(
        selection=[
            ('student', 'Student'),
            ('parent', 'Parent'),
        ],
    )
    channel = fields.Selection(
        selection=[
            ('whatsapp', 'WhatsApp'),
            ('inbound_call', 'Inbound Call'),
            ('req_callback', 'Req Callback'),
            ('internal', 'Internal'),
        ],
    )

    @api.model
    def create(self, vals):
        """Override to ensure notification when user_id is set"""
        ticket = super().create(vals)
        if ticket.user_id and ticket.user_id.partner_id and\
                ticket.channel == 'whatsapp':
            ticket.message_subscribe(
                partner_ids=[ticket.user_id.partner_id.id]
            )
            # Prepare values for the template, similar to Odoo base
            model_description = ticket.env['ir.model']._get(ticket._name)\
                .display_name
            company = ticket.company_id.sudo() if 'company_id' in ticket else\
                ticket.env.company
            values = {
                'access_link': ticket._notify_get_action_link('view'),
                'company': company,
                'model_description': model_description,
                'object': ticket,
            }
            # Use the same template as Odoo base for assignment
            assignation_msg = ticket.env['ir.qweb']._render(
                'mail.message_user_assigned',
                values,
                minimal_qcontext=True
            )
            assignation_msg = ticket.env['mail.render.mixin']\
                ._replace_local_links(assignation_msg)
            ticket.message_notify(
                subject=_('You have been assigned to %s', ticket.display_name),
                author_id=self.env.ref('base.user_root').id,
                body=assignation_msg,
                partner_ids=[ticket.user_id.partner_id.id],
                record_name=ticket.display_name,
                email_layout_xmlid='mail.mail_notification_layout',
                model_description=model_description,
            )
        return ticket

    def _get_whatsapp_channel_admin(self):
        """
        Get the admin assigned to customer's WhatsApp channel.
        This ensures helpdesk ticket is assigned to the same person handling WhatsApp.

        Returns:
            res.users record or False
        """
        import logging
        _logger = logging.getLogger(__name__)

        if not self.partner_id:
            return False

        # Find WhatsApp channel for this customer
        channel = self.env['discuss.channel'].sudo().search([
            ('channel_type', '=', 'whatsapp'),
            ('channel_member_ids.partner_id', '=', self.partner_id.id),
        ], limit=1, order='create_date desc')

        if not channel:
            _logger.debug(f"[Helpdesk Assignment] No WhatsApp channel found for partner {self.partner_id.name}")
            return False

        # Get admin from channel
        admin = channel._get_existing_admin_from_channel()
        if admin:
            _logger.info(
                f"[Helpdesk Assignment] Found WhatsApp admin {admin.name} "
                f"for partner {self.partner_id.name}"
            )
        return admin

    def assign_user_based_on_student_phase(self):
        """ Check student phase and assign agent based on it

        Assignment Priority:
        1. Use WhatsApp channel admin if exists (sync with WhatsApp)
        2. Use team assignment based on student phase (fallback)

        Team Rules:
        - Paid Student → Support team (or team with paid_student=True)
        - New Student or Non Paid Student → Onboarding team (or team with new_student/non_paid_student=True)
        """
        import logging
        _logger = logging.getLogger(__name__)

        if not self.partner_id:
            _logger.warning(f"[Helpdesk Assignment] Ticket {self.id} has no partner, skipping assignment")
            return

        student_phase = self.partner_id.metabase_student_phase
        _logger.info(f"[Helpdesk Assignment] Ticket {self.id} - Partner: {self.partner_id.name}, Student Phase: {student_phase}")

        # PRIORITY 1: Check if customer has WhatsApp channel with assigned admin
        whatsapp_admin = self._get_whatsapp_channel_admin()
        if whatsapp_admin:
            # Find team that this admin belongs to
            team = self.env['helpdesk.team'].sudo().search([
                ('member_ids', 'in', [whatsapp_admin.id]),
                ('is_whatsapp_team', '=', True),
            ], limit=1)

            if team:
                self.team_id = team
                self.user_id = whatsapp_admin
                _logger.info(
                    f"[Helpdesk Assignment] Synced with WhatsApp - Team: {team.name}, "
                    f"User: {whatsapp_admin.name}"
                )
                return

        # PRIORITY 2: Fallback to student phase based assignment
        if not student_phase:
            _logger.warning(f"[Helpdesk Assignment] Partner {self.partner_id.name} has no student phase, skipping assignment")
            return

        team_id = False

        # Find team based on student phase flags (same logic as WhatsApp assignment)
        if student_phase == 'paid':
            team_id = self.env['helpdesk.team'].search([
                ('is_whatsapp_team', '=', True),
                ('paid_student', '=', True),
            ], limit=1)
            if not team_id:
                # Fallback to name-based search
                team_id = self.env['helpdesk.team'].search([
                    ('name', 'ilike', 'Support')
                ], limit=1)
            _logger.info(f"[Helpdesk Assignment] Paid Student → Looking for team with paid_student=True")

        elif student_phase in ['new', 'non_paid']:
            # For new students
            if student_phase == 'new':
                team_id = self.env['helpdesk.team'].search([
                    ('is_whatsapp_team', '=', True),
                    ('new_student', '=', True),
                ], limit=1)
            # For non_paid students
            if not team_id:
                team_id = self.env['helpdesk.team'].search([
                    ('is_whatsapp_team', '=', True),
                    ('non_paid_student', '=', True),
                ], limit=1)
            if not team_id:
                # Fallback to name-based search
                team_id = self.env['helpdesk.team'].search([
                    ('name', 'ilike', 'Onboarding')
                ], limit=1)
            _logger.info(f"[Helpdesk Assignment] {student_phase} Student → Looking for matching team")

        if team_id:
            _logger.info(f"[Helpdesk Assignment] Found team: {team_id.name} (ID: {team_id.id})")
            self.team_id = team_id

            # Use same round-robin logic as WhatsApp assignment
            assigned_user = self.partner_id._get_or_assign_lead_owner()

            if assigned_user:
                self.user_id = assigned_user
                _logger.info(f"[Helpdesk Assignment] Assigned to user: {assigned_user.name}")
            else:
                _logger.warning(f"[Helpdesk Assignment] Could not determine user to assign")
        else:
            _logger.warning(f"[Helpdesk Assignment] No team found for student phase '{student_phase}'")
