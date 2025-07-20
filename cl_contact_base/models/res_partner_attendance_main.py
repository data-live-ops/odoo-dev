from odoo import fields, models


class ResPartnerAttendanceMain(models.Model):
    """ New model for res.partner attendance main """

    _name = 'res.partner.attendance.main'
    _description = 'Attendance'

    partner_id = fields.Many2one('res.partner', string="Partner", index=True)
    student_user_id = fields.Char(
        string="Student User ID",
        readonly=True, index=True
    )
    live_class_id = fields.Char(
        string="Class ID",
        readonly=True, index=True
    )
    time_of_joining = fields.Char(
        string="Class Joined At",
        readonly=True,
    )
    class_attendance_ids = fields.One2many(
        'res.partner.attendance.detail',
        'attendance_main_id',
        string="Class Attendance",
    )
    class_topic = fields.Char(readonly=True)
    class_subject = fields.Char(readonly=True)
    teacher_name = fields.Char(
        string="Class Teacher",
        readonly=True,
    )

class ResPartnerAttendanceDetail(models.Model):
    """ New model for res.partner attendance detail """

    _name = 'res.partner.attendance.detail'
    _description = 'Attendance Detail'

    attendance_main_id = fields.Many2one('res.partner.attendance.main')
    live_class_id = fields.Char(
        string="Class ID",
        readonly=True,
    )
    class_topic = fields.Char(readonly=True)
    class_subject = fields.Char(readonly=True)
    teacher_name = fields.Char(
        string="Class Teacher",
        readonly=True,
    )
    class_start_time = fields.Char(readonly=True)
