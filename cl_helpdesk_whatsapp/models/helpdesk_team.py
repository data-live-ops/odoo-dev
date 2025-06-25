from odoo import fields, models


class HelpdeskTeam(models.Model):
    """ Inherit Helpdesk Team """

    _inherit = "helpdesk.team"

    new_student = fields.Boolean()
    non_paid_student = fields.Boolean()
    paid_student = fields.Boolean()
