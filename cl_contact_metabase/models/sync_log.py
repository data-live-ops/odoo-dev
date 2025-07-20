from odoo import models, fields, api
from werkzeug import urls


class MetabaseSyncLog(models.Model):
    _name = 'metabase.sync.log'
    _description = 'Metabase Sync Log'
    _order = 'create_date desc'

    name = fields.Char(string='Reference', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('done', 'Success'),
        ('failed', 'Failed')
    ], default='draft', string='Status')
    start_date = fields.Datetime('Start Date')
    end_date = fields.Datetime('End Date')
    total_records = fields.Integer('Total Records')
    created_count = fields.Integer('Created Records')
    updated_count = fields.Integer('Updated Records')
    error_message = fields.Text('Error Message')
    raw_response = fields.Text('Raw Response')
    sync_type = fields.Selection([
        ('auto', 'Automatic'),
        ('manual', 'Manual')
    ], default='auto', required=True, string="Sync Type")
    data_type = fields.Selection([
        ('student', 'Student'),
        ('lead', 'Lead Stages'),
        ('parent', 'Parent'),
        ('subscription', 'Subscription'),
        ('attendance', 'Attendance'),
        ('payment_received', 'Payment Received'),
        ('payment_slot_selection', 'Payment Slot Selection'),
    ], default='student', required=True, string="Data Type")
    partner_id = fields.Many2one('res.partner', string="Partner", index=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('metabase.sync.log') or 'New'
        return super().create(vals_list)

    # def name_get(self):
    #     return [(log.id, f"Sync {log.sync_type} - {log.create_date:%Y-%m-%d %H:%M:%S}") for log in self]

    def _generate_action_url(self):
        """
        generate action url
        """
        self.ensure_one()
        base_url = self.get_base_url()
        return urls.url_join(
            base_url, "/odoo/%s/%s" % (self._name, self.id)
        )
    
    def get_sync_type(self):
        sync_type = ''
        if self.sync_type == 'auto':
            sync_type = 'Automatic'
        elif self.sync_type == 'manual':
            sync_type = 'Manual'
        return sync_type
    
    def get_data_type(self):
        data_type = ''
        if self.data_type == 'student':
            data_type = 'Student'
        elif self.data_type == 'lead':
            data_type = 'Student Lead'
        elif self.data_type == 'parent':
            data_type = 'Parent'
        elif self.data_type == 'subscription':
            data_type = 'Subscription'
        return data_type
    
    def action_notify(self):
        """Send notification about sync failure to configured recipients
        
        This method sends a notification email to the configured recipients
        about the sync failure. It includes details about the error and a link
        to view the sync log record.
        
        Returns:
            dict: Action result message for user feedback
        """
        self.ensure_one()
        for log in self:
            sync_type = log.get_sync_type()
            data_type = log.get_data_type()
            config = self.env["metabase.config"].search([("active", "=", True)], limit=1)
            config.action_notify_portcities(error_type="%s Sync %s Error" % (sync_type, data_type), error_message=log.error_message, sync_log_url=log._generate_action_url())
