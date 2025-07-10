from odoo import fields, models


class ResPartnerSyncLog(models.Model):
    """ New model for res.partner sync log """

    _name = 'res.partner.sync.log'
    _description = 'Sync Log'

    partner_id = fields.Many2one('res.partner')
    last_sync_status = fields.Char(
        readonly=True,
        tracking=True,
    )
    last_manual_sync_status = fields.Selection(
        selection=(
            ('success', 'Success'),
            ('failed', 'Failed'),
        ),
        readonly=True,
        tracking=True,
    )
    last_sync = fields.Datetime(
        readonly=True,
        tracking=True,
    )
    last_manual_sync = fields.Datetime(
        readonly=True,
        tracking=True,
    )
