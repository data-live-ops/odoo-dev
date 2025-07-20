from odoo import fields, models


class ResPartnerSubs(models.Model):
    """ New model for res.partner subscription """

    _name = 'res.partner.subs'
    _description = 'Subscription'
    _rec_name = 'subscription_id'

    subs_student_id = fields.Many2one('res.partner', index=True)
    subscription_id = fields.Char(
        string="Subscription ID",
        readonly=True, index=True
    )
    student_user_id = fields.Char(
        string="Student User ID",
        readonly=True, index=True
    )
    name = fields.Char(
        string="Subscription Name",
        readonly=True
    )
    status = fields.Char(
        string="Status",
        readonly=True
    )
    subs_start_date = fields.Char(
        string="Subs Start Date",
        readonly=True
    )
    subs_end_date = fields.Char(
        string="Subs End Date",
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
    subs_next_payment_date = fields.Char(
        string="Next Payment Date",
        readonly=True
    )
