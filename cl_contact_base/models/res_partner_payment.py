from odoo import fields, models


class ResPartnerPayment(models.Model):
    """ New model for res.partner payment """

    _name = 'res.partner.payment'
    _description = 'Res Partner Payment'

    partner_id = fields.Many2one('res.partner')
    rounded_opt_in_date = fields.Datetime(
        string="Slot Selected At",
        readonly=True,
    )
    course_batch_pairs = fields.Char(
        string="Course & Slot Selected",
        readonly=True,
    )
    paid_amount = fields.Char(
        string="Total Nominal Pembayaran (Rp)",
        readonly=True,
    )
    package_name = fields.Char(
        string="Paket Belajar CoLearn",
        readonly=True,
    )
    payment_link = fields.Char(
        readonly=True,
    )
    invoice_id = fields.Char(
        string="Invoice ID",
        readonly=True,
    )
    payment_method = fields.Char(
        string="Payment Mode",
        readonly=True,
    )
    payment_channel = fields.Char(
        readonly=True,
    )
    sales_agent_email = fields.Char(
        readonly=True,
    )
    payment_context = fields.Char(
        readonly=True,
    )
    payment_for_date = fields.Date(
        string="Payment for Date",
        readonly=True,
    )
    retention_payment_type = fields.Char(
        readonly=True,
    )
    name = fields.Char(
        string="Package Name",
        readonly=True,
    )
