from odoo import fields, models


class HelpdeskStage(models.Model):
    """ Inherit Helpdesk Stage """

    _inherit = "helpdesk.stage"

    is_closed_stage = fields.Boolean(
        string="Closed Stage?",
        default=False
    )
