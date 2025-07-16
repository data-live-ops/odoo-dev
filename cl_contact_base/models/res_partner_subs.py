from odoo import fields, models


class ResPartnerSubs(models.Model):
    """ New model for res.partner subscription """

    _name = 'res.partner.subs'
    _description = 'Subscription'
    _rec_name = 'subscription_id'

    subs_student_id = fields.Many2one('res.partner')
    subscription_id = fields.Char(
        string="Subscription ID",
        readonly=True
    )
    student_user_id = fields.Char(
        string="Student User ID",
        readonly=True
    )
    name = fields.Char(
        string="Subscription Name",
        readonly=True
    )
    status = fields.Char(
        string="Status",
        readonly=True
    )
    start_date = fields.Datetime(
        string="Start Date",
        readonly=True
    )
    end_date = fields.Datetime(
        string="End Date",
        readonly=True
    )
    cancellation_date = fields.Char(
        string="Cancellation Date",
        readonly=True
    )
    payment_type = fields.Char(
        string="Payment Type",
        readonly=True
    )
    next_payment_date = fields.Date(
        string="Next Payment Date",
        readonly=True
    )
