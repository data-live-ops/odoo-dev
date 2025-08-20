from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"


    def action_contact_sync_now(self):
        """
        Manual sync action for student, lead stage, parent, subscription, attendance, payment received, payment slot selection, payment paid access
        """
        for record in self:
            if not record.is_student:
                continue

            record.with_delay().action_sync_manual_student()
            record.with_delay().action_sync_manual_lead_stage()
            if record.student_parent_ids:
                record.student_parent_ids.with_delay().action_sync_parent_from_metabase()
            record.with_delay().action_sync_student_subscription_from_metabase()
            record.with_delay().action_sync_attendance_from_metabase()
            record.with_delay().action_sync_payment_received_from_metabase()
            record.with_delay().action_sync_payment_slot_selection_from_metabase()
            record.with_delay().action_sync_payment_paid_access_from_metabase()
        return {'type': 'ir.actions.client', 'tag': 'soft_reload'}

    def action_sync_student_from_metabase(self):
        for record in self:
            if not record.is_student:
                continue

            record.with_delay().action_sync_manual_student()
        return {'type': 'ir.actions.client', 'tag': 'soft_reload'}

    def action_sync_lead_stage_from_metabase(self):
        for record in self:
            if not record.is_student:
                continue

            record.with_delay().action_sync_manual_lead_stage()
        return {'type': 'ir.actions.client', 'tag': 'soft_reload'}

    def action_sync_subscription_from_metabase(self):
        for record in self:
            if not record.is_student:
                continue

            record.with_delay().action_sync_student_subscription_from_metabase()
        return {'type': 'ir.actions.client', 'tag': 'soft_reload'}
