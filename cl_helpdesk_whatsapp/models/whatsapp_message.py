from odoo import fields, models


class WhatsappMessage(models.Model):
    """ Inherit Whatsapp Message """

    _inherit = "whatsapp.message"

    helpdesk_ticket_id = fields.Many2one(
        "helpdesk.ticket",
        string="Ticket",
    )
    is_autoreply = fields.Boolean(
        string="Is Autoreply",
        default=False,
        help="Indicates if this message was sent as an automatic reply"
    )
