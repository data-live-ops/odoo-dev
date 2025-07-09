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
    attendance_ids = fields.One2many('res.partner.attendance', 'partner_id')

    # 'Subscription' tab
    subscription_id = fields.Many2one('res.partner.subs')
    subscription_name = fields.Char(
        related='subscription_id.name',
        readonly=True
    )
    status = fields.Char(
        related='subscription_id.status',
        readonly=True
    )
    next_payment_date = fields.Date(
        related='subscription_id.next_payment_date',
        readonly=True
    )
    start_date = fields.Datetime(
        related='subscription_id.start_date',
        readonly=True
    )
    end_date = fields.Datetime(
        related='subscription_id.end_date',
        readonly=True
    )
    cancellation_date = fields.Char(
        related='subscription_id.cancellation_date',
        readonly=True
    )

    # 'Payment' tab
    payment_ids = fields.One2many('res.partner.payment', 'partner_id')
    sync_log_ids = fields.One2many('res.partner.sync.log', 'partner_id')
