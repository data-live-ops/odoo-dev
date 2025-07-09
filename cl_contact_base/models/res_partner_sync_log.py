""" Import Library """ 
from odoo import fields, models


class ResPartnerSyncLog(models.Model):
    """ New model for res.partner.sync.log """

    _name = 'res.partner.sync.log'
    _description = 'Res Partner Sync Log'

    last_sync_status = fields.Char(string='Last Sync Status', tracking=True)
    last_manual_sync_status = fields.Char(string='Last Manual Sync Status',
        tracking=True)
    last_sync = fields.Datetime(string='Last Sync', tracking=True)
    last_manual_sync = fields.Datetime(string='Last Manual Sync',
        tracking=True)
    partner_id = fields.Many2one('res.partner')
