from odoo import fields, models
import datetime
import logging


class HelpdeskSLA(models.Model):
    """ Inherit helpdesk.sla """

    _inherit = 'helpdesk.sla'

    sla_reminder_email_template_id = fields.Many2one(
        'mail.template',
        string='SLA Reminder Email Templates',
        help='Email template used for SLA reminders',
        tracking=True,
    )
    sla_deadline = fields.Integer(
        string='SLA Deadline',
        help='SLA deadline',
        tracking=True,
    )

    def cron_sla_reminder(self):
        """Scheduled action to handle SLA Reminders.
        Checks tickets with SLA, calculates deadlines,
        and sends reminders if overdue."""
        _logger = logging.getLogger(__name__)
        Ticket = self.env['helpdesk.ticket']
        # Find all tickets with at least one SLA
        tickets = Ticket.search([
            ('sla_ids', '!=', False),
            ('user_id', '!=', False),
            ('create_date', '!=', False)
        ])
        now = fields.Datetime.now()
        for ticket in tickets:
            sla = ticket.sla_ids and ticket.sla_ids[0] or False
            if not sla:
                continue
            # Get deadline days from SLA
            sla_deadline = getattr(sla, 'sla_deadline', 0.0) or 0.0
            # Calculate deadline: create_date + 3 days - sla_deadline (in days)
            try:
                create_dt = fields.Datetime.from_string(ticket.create_date)
            except Exception as e:
                _logger.warning(
                    f"Invalid create_date for ticket {ticket.id}: {e}"
                )
                continue
            deadline = create_dt + datetime.timedelta(days=sla_deadline)
            if fields.Datetime.from_string(now) >= deadline:
                # Send reminder email using SLA's template
                template = getattr(
                    sla,
                    'sla_reminder_email_template_id',
                    False,
                )
                if template and ticket.user_id:
                    template.send_mail(ticket.id, force_send=True)
                    _logger.info(
                        f"SLA Reminder sent for ticket\
                            {ticket.id} to user {ticket.user_id.id}"
                    )
                else:
                    _logger.warning(
                        f"No email template or assigned user for ticket\
                            {ticket.id}"
                    )
        _logger.info('SLA Reminder cron executed.')
        return True
