""" Import Library """
from odoo import api, fields, models


class HelpdeskTicket(models.Model):
    """ Inherit helpdesk.ticket """

    _inherit = 'helpdesk.ticket'

    is_get_reminder = fields.Boolean(string='Is Get Reminder', default=False)

    @api.model
    def cron_sla_reminder(self):
        """Scheduled action to handle SLA Reminders.
        Checks tickets with SLA, calculates deadlines,
        and sends reminders if overdue."""
        print("cron_sla_reminder")
        # Improved query: for each ticket, get the SLA status
        # with the minimum deadline, its sla_id,
        # and check if now > (deadline - sla_deadline)
        self.env.cr.execute("""
            SELECT
                t.id as ticket_id,
                s.sla_reminder_email_template_id as template_id
            FROM helpdesk_ticket t
            JOIN (
                SELECT ss.ticket_id, ss.sla_id, ss.deadline
                FROM helpdesk_sla_status ss
                JOIN (
                    SELECT ticket_id, MIN(deadline) AS min_deadline
                    FROM helpdesk_sla_status
                    WHERE deadline IS NOT NULL
                    GROUP BY ticket_id
                ) min_ss ON ss.ticket_id = min_ss.ticket_id
                    AND ss.deadline = min_ss.min_deadline
            ) ss_min ON t.id = ss_min.ticket_id
            JOIN helpdesk_sla s ON ss_min.sla_id = s.id
            WHERE t.team_id IS NOT NULL
            AND ss_min.deadline IS NOT NULL
            AND t.is_get_reminder = False
            AND (ss_min.deadline - (INTERVAL '1 hour' * s.sla_deadline))
                <= (NOW() AT TIME ZONE 'UTC')
        """)
        rows = self.env.cr.fetchall()
        for row in rows:
            # Search ticket model
            ticket = self.env['helpdesk.ticket'].sudo().browse(row[0])
            # Send reminder email using SLA's template
            template = self.env['mail.template'].sudo().browse(row[1])
            if template and ticket.user_id:
                template.send_mail(ticket.id, force_send=True)
                ticket.is_get_reminder = True
        return True
