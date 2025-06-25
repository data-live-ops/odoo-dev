from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WhatsappTemplate(models.Model):
    """ Inherit Whatsapp Template """

    _inherit = "whatsapp.template"

    is_autoreply = fields.Boolean(
        string="Use as Autoreply",
        default=False,
    )
    timed_delay = fields.Float(default=15)
    button_create_ticket_id = fields.Many2one(
        "whatsapp.template.button",
    )

    def _check_autoreply(self):
        """Ensure only one template is set as autoreply at a time"""
        if self.is_autoreply:
            another_record = self.search([
                ('is_autoreply', '=', True),
                ('id', '!=', self.id),
            ], limit=1)
            if another_record:
                raise UserError(_(
                    "Autoreply already set on '%s'" % another_record.name
                ))

    @api.model
    def create(self, vals):
        """Override to check autoreply"""
        res = super(WhatsappTemplate, self).create(vals)
        if vals.get('is_autoreply'):
            res._check_autoreply()
        return res

    def write(self, vals):
        """Override to check autoreply"""
        res = super(WhatsappTemplate, self).write(vals)
        if vals.get('is_autoreply'):
            self._check_autoreply()
        return res
