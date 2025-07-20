from odoo import fields, models


class ResPartnerPaymentRecieved(models.Model):
    """ New model for res.partner payment received """

    _name = 'res.partner.payment.recieved'
    _description = 'Payment Received'
    _rec_name = 'invoice_id'

    # Core fields
    student_id = fields.Many2one('res.partner', string="Student", index=True)
    metabase_user_id = fields.Char(string="Metabase User ID", index=True)
    invoice_id = fields.Char(string="Invoice ID", index=True)
    
    # Payment details
    paid_amount = fields.Char(string="Paid Amount", readonly=True)
    package_name = fields.Char(string="Package Name", readonly=True)
    payment_link = fields.Char(string="Payment Link", readonly=True)
    payment_method = fields.Char(string="Payment Method", readonly=True)
    payment_channel = fields.Char(string="Payment Channel", readonly=True)
    
    # Sales and context information
    sales_agent_email = fields.Char(string="Sales Agent Email", readonly=True)
    payment_context = fields.Char(string="Payment Context", readonly=True)
    payment_for_date = fields.Char(string="Payment For Date", readonly=True)
    retention_payment_type = fields.Char(string="Retention Payment Type", readonly=True)
