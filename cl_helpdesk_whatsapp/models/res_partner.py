from odoo import api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.onchange('phone', 'country_id', 'company_id')
    def _onchange_phone_validation(self):
        """ Replace, disable method because disturb phone number in partner """
        return

    @api.onchange('mobile', 'country_id', 'company_id')
    def _onchange_mobile_validation(self):
        """ Replace, disable method because disturb phone number in partner """
        return
    
    def _find_or_create_from_number(self, number, name=False):
        """ Super, assign phone number from mobile if phone is empty """
        res = super(ResPartner, self)._find_or_create_from_number(number, name)
        if res and not res.phone:
            res.phone = res.mobile
        return res
