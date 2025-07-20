from odoo import fields, models


class ResPartner(models.Model):
    """ Inherit res.partner """

    _inherit = 'res.partner'

    # Form header
    contact_type = fields.Selection(
        [
            ('student', 'Student'),
            ('parent', 'Parent'),
        ],
    )
    parent_type = fields.Selection([
        ('ayah', 'Ayah'),
        ('ibu', 'Ibu'),
    ])
    related_parent_id = fields.Many2one('res.partner')
    metabase_user_id = fields.Char(string="User ID", index=True)
    metabase_parent_id = fields.Char(string="Parent ID", index=True)
    metabase_grade = fields.Char(string="Grades")
    metabase_school = fields.Char(string="School Name")
    metabase_curriculum = fields.Char(string="Curriculum")
    metabase_city = fields.Char(string="Onboarding Location")
    metabase_lead_status = fields.Char(string="Lead Stage")
    metabase_student_phase = fields.Selection(selection=[
        ('paid', 'Paid Student'),
        ('new', 'New Student'),
        ('non_paid', 'Non Paid Student'),
    ], string="Student Phase", copy=False)
    metabase_notification_consent = fields.Char(string="Notification Consent")

    # 'Attendance' tab
    attendance_ids = fields.One2many('res.partner.attendance.main', 'partner_id')

    # 'Subscription' tab
    subscription_ids = fields.One2many('res.partner.subs', 'subs_student_id')
    subscription_id = fields.Many2one('res.partner.subs')
    subscription_name = fields.Char(
        related='subscription_id.name',
        readonly=True
    )
    status = fields.Char(
        related='subscription_id.status',
        readonly=True
    )
    next_payment_date = fields.Char(
        related='subscription_id.subs_next_payment_date',
        readonly=True
    )
    start_date = fields.Char(
        related='subscription_id.subs_start_date',
        readonly=True
    )
    end_date = fields.Char(
        related='subscription_id.subs_end_date',
        readonly=True
    )
    cancellation_date = fields.Char(
        related='subscription_id.cancellation_date',
        readonly=True
    )

    # 'Payment' tab
    payment_received_ids = fields.One2many('res.partner.payment.recieved', 'student_id', string="Payment Received")
    payment_slot_selection_ids = fields.One2many('res.partner.payment.slot.selection', 'student_id', string="Payment Slot Selection")
    payment_paid_access_ids = fields.One2many('res.partner.payment.paid.access', 'student_id', string="Payment Paid Access")

    # 'Sync Log' tab
    sync_log_id = fields.Many2one('res.partner.sync.log')
    last_sync_status = fields.Char(
        related='sync_log_id.last_sync_status',
        readonly=True,
        tracking=True,
    )
    last_manual_sync_status = fields.Selection(
        related='sync_log_id.last_manual_sync_status',
        readonly=True,
        tracking=True,
    )
    last_sync = fields.Datetime(
        related='sync_log_id.last_sync',
        readonly=True,
        tracking=True,
    )
    last_manual_sync = fields.Datetime(
        related='sync_log_id.last_manual_sync',
        readonly=True,
        tracking=True,
    )
