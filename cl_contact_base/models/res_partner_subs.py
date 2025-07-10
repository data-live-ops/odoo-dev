from odoo import fields, models


class ResPartnerSubs(models.Model):
    """ New model for res.partner subscription """

    _name = 'res.partner.subs'
    _description = 'Subscription'
    _rec_name = 'subscription_id'

    subscription_id = fields.Char(
        string="Subscription ID",
        readonly=True
    )
    name = fields.Char(
        string="Package Name",
        readonly=True
    )
    status = fields.Char(
        string="Subscription Status",
        readonly=True
    )
    next_payment_date = fields.Date(
        readonly=True
    )
    start_date = fields.Datetime(
        string="Subscription Start Date",
        readonly=True
    )
    end_date = fields.Datetime(
        string="Subscription End Date",
        readonly=True
    )
    cancellation_date = fields.Char(
        string="Cancellation Date",
        readonly=True
    )
