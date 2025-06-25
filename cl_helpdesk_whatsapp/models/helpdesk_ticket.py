from odoo import _, api, fields, models


class HelpdeskTicket(models.Model):
    """ Inherit Helpdesk Ticket """

    _inherit = "helpdesk.ticket"

    user_id = fields.Many2one(
        required=True,
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
        selection=[
            ('paid_student', 'Paid Student'),
            ('new_student', 'New Student'),
            ('non_paid_student', 'Non Paid Student'),
        ],
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
