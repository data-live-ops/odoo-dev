from odoo import fields, models


class ResPartnerAttendance(models.Model):
    """ New model for res.partner attendance """

    _name = 'res.partner.attendance'
    _description = 'Attendance'

    partner_id = fields.Many2one('res.partner')
    live_class_id = fields.Char(
        string="Class ID",
        readonly=True,
    )
    class_subject = fields.Char(readonly=True)
    class_topic = fields.Char(readonly=True)
    teacher_name = fields.Char(
        string="Class Teacher",
        readonly=True,
    )
    class_start_time = fields.Datetime(readonly=True)
    time_of_joining = fields.Datetime(
        string="Class Joined At",
        readonly=True,
    )
