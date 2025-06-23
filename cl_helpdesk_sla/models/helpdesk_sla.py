from odoo import fields, models


class HelpdeskSLA(models.Model):
    """ Inherit helpdesk.sla """

    _inherit = 'helpdesk.sla'

    sla_reminder_email_template_id = fields.Many2one(
        'mail.template',
        string='SLA Reminder Email Templates',
        help='Email template used for SLA reminders',
        tracking=True,
    )
    sla_deadline = fields.Float(
        string='SLA Deadline',
        help='SLA deadline',
        tracking=True,
    )
