from odoo import fields, models


class HelpdeskTeam(models.Model):
    """ Inherit Helpdesk Team """

    _inherit = "helpdesk.team"

    new_student = fields.Boolean()
    non_paid_student = fields.Boolean()
    paid_student = fields.Boolean()

    # WhatsApp Channel Assignment
    is_whatsapp_team = fields.Boolean(
        string="WhatsApp Team",
        help="If checked, this team will be used for WhatsApp channel admin assignment"
    )
