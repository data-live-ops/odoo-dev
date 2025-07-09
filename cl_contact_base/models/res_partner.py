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
    metabase_user_id = fields.Char(string="User ID")
    metabase_parent_id = fields.Char(string="Parent ID")
    metabase_grade = fields.Char(string="Grades")
    metabase_school = fields.Char(string="School Name")
    metabase_curriculum = fields.Char(string="Curriculum")
    metabase_city = fields.Char(string="Onboarding Location")
    metabase_lead_status = fields.Char(string="Lead Stage")
    metabase_student_phase = fields.Char(string="Student Phase")
    metabase_notification_consent = fields.Char(string="Notification Consent")

    # 'Attendance' tab
    attendance_ids = fields.One2many('res.partner.attendance', 'partner_id')
