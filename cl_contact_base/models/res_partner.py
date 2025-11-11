from odoo import fields, models, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """ Inherit res.partner """

    _inherit = 'res.partner'

    # Form header
    contact_type = fields.Selection([
        ('regular', 'Regular'),
        ('student', 'Student'),
        ('parent', 'Parent'),
    ])
    parent_type = fields.Selection([
        ('ayah', 'Ayah'),
        ('ibu', 'Ibu'),
    ])
    related_parent_id = fields.Many2one('res.partner')
    metabase_user_id = fields.Char(string="User ID", index=True)
    metabase_student_id = fields.Char(string="Student ID", index=True)
    metabase_parent_id = fields.Char(string="Parent ID", index=True)
    metabase_grade = fields.Char(string="Grades")
    metabase_school = fields.Char(string="School Name")
    metabase_curriculum = fields.Char(string="Curriculum")
    metabase_city = fields.Char(string="Onboarding Location")
    metabase_lead_status = fields.Char(string="Lead Stage")
    metabase_student_phase = fields.Selection(selection=[
        ('paid', 'Paid Student'),
        ('new', 'New Student'),
        ('non_paid', 'Non Paid Student'),
    ], string="Student Phase", copy=False)
    metabase_notification_consent = fields.Char(string="Notification Consent")

    # 'Attendance' tab
    attendance_ids = fields.One2many('res.partner.attendance.main', 'partner_id')

    # 'Subscription' tab
    subscription_ids = fields.One2many('res.partner.subs', 'subs_student_id')
    subscription_id = fields.Many2one('res.partner.subs')
    subscription_name = fields.Char(
        related='subscription_id.name',
        readonly=True
    )
    status = fields.Char(
        related='subscription_id.status',
        readonly=True
    )
    next_payment_date = fields.Char(
        related='subscription_id.subs_next_payment_date',
        readonly=True
    )
    start_date = fields.Char(
        related='subscription_id.subs_start_date',
        readonly=True
    )
    end_date = fields.Char(
        related='subscription_id.subs_end_date',
        readonly=True
    )
    cancellation_date = fields.Char(
        related='subscription_id.cancellation_date',
        readonly=True
    )

    # 'Payment' tab
    payment_received_ids = fields.One2many('res.partner.payment.recieved', 'student_id', string="Payment Received")
    payment_slot_selection_ids = fields.One2many('res.partner.payment.slot.selection', 'student_id', string="Payment Slot Selection")
    payment_paid_access_ids = fields.One2many('res.partner.payment.paid.access', 'student_id', string="Payment Paid Access")

    # 'Sync Log' tab
    sync_log_id = fields.Many2one('res.partner.sync.log')
    last_sync_status = fields.Char(
        related='sync_log_id.last_sync_status',
        readonly=True,
        tracking=True,
    )
    last_manual_sync_status = fields.Selection(
        related='sync_log_id.last_manual_sync_status',
        readonly=True,
        tracking=True,
    )
    last_sync = fields.Datetime(
        related='sync_log_id.last_sync',
        readonly=True,
        tracking=True,
    )
    last_manual_sync = fields.Datetime(
        related='sync_log_id.last_manual_sync',
        readonly=True,
        tracking=True,
    )

    def _merge_with_duplicates(self, duplicates):
        """
        Merge duplicate contacts into this master contact

        Args:
            duplicates: recordset of res.partner to merge into self
        """
        self.ensure_one()

        if not duplicates:
            return

        _logger.info(f"[Contact Merge] Merging {len(duplicates)} duplicates into {self.name} (ID: {self.id})")

        # Collect all IDs for updating references
        duplicate_ids = duplicates.ids

        # 1. Merge fields (keep master's data, fill empty fields from duplicates)
        fields_to_merge = [
            'email', 'phone', 'mobile', 'street', 'street2', 'city', 'state_id',
            'zip', 'country_id', 'metabase_user_id', 'metabase_student_id',
            'metabase_parent_id', 'metabase_grade', 'metabase_school',
            'metabase_curriculum', 'metabase_city', 'metabase_lead_status',
            'metabase_student_phase', 'metabase_notification_consent'
        ]

        merge_vals = {}
        for field in fields_to_merge:
            if not self[field]:
                # Master doesn't have this field, try to get from duplicates
                for dup in duplicates:
                    if dup[field]:
                        merge_vals[field] = dup[field]
                        _logger.info(f"[Contact Merge] Filling {field} from duplicate: {dup[field]}")
                        break

        if merge_vals:
            try:
                self.write(merge_vals)
            except Exception as e:
                _logger.warning(f"[Contact Merge] Could not update master fields: {e}")

        # 2. Update all references to point to master contact
        try:
            with self.env.cr.savepoint():
                self._update_references_to_master(duplicate_ids)
        except Exception as e:
            _logger.warning(f"[Contact Merge] Could not update references: {e}")

        # 3. Merge One2many relations (attendance, subscription, payment)
        try:
            with self.env.cr.savepoint():
                self._merge_one2many_relations(duplicates)
        except Exception as e:
            _logger.warning(f"[Contact Merge] Could not merge one2many relations: {e}")

        # 4. Merge Many2many relations (student_parent_ids if exists)
        try:
            with self.env.cr.savepoint():
                self._merge_many2many_relations(duplicates)
        except Exception as e:
            _logger.warning(f"[Contact Merge] Could not merge many2many relations: {e}")

        # 5. Add note to chatter about merge (optional, don't fail if this errors)
        try:
            merge_note = f"Merged duplicate contacts: {', '.join([f'{d.name} (ID:{d.id})' for d in duplicates])}"
            self.message_post(body=merge_note)
        except Exception as e:
            _logger.warning(f"[Contact Merge] Could not post merge note to chatter: {e}")

        # 6. Archive duplicates instead of delete (safer)
        try:
            duplicates.write({'active': False})
        except Exception as e:
            _logger.error(f"[Contact Merge] Could not archive duplicates: {e}")
            raise

        _logger.info(f"[Contact Merge] Successfully merged {len(duplicates)} contacts into {self.name}")

    def _update_references_to_master(self, duplicate_ids):
        """Update all database references from duplicates to master"""
        models_to_update = [
            ('helpdesk.ticket', 'partner_id'),
            ('discuss.channel', 'channel_partner_ids'),
            ('mail.message', 'partner_ids'),
            ('mail.followers', 'partner_id'),
        ]

        for model_name, field_name in models_to_update:
            try:
                with self.env.cr.savepoint():
                    # SQL update for performance
                    self.env.cr.execute(f"""
                        UPDATE {model_name.replace('.', '_')}
                        SET {field_name} = %s
                        WHERE {field_name} IN %s
                    """, (self.id, tuple(duplicate_ids)))
                    _logger.info(f"[Contact Merge] Updated {model_name}.{field_name} references")
            except Exception as e:
                _logger.warning(f"[Contact Merge] Could not update {model_name}.{field_name}: {e}")

    def _merge_one2many_relations(self, duplicates):
        """Merge One2many relations from duplicates to master"""
        # Update attendance records
        if 'attendance_ids' in self._fields and 'res.partner.attendance.main' in self.env:
            try:
                with self.env.cr.savepoint():
                    self.env['res.partner.attendance.main'].search([
                        ('partner_id', 'in', duplicates.ids)
                    ]).write({'partner_id': self.id})
            except Exception as e:
                _logger.warning(f"[Contact Merge] Could not merge attendance records: {e}")

        # Update subscription records
        if 'subscription_ids' in self._fields and 'res.partner.subs' in self.env:
            try:
                with self.env.cr.savepoint():
                    self.env['res.partner.subs'].search([
                        ('subs_student_id', 'in', duplicates.ids)
                    ]).write({'subs_student_id': self.id})
            except Exception as e:
                _logger.warning(f"[Contact Merge] Could not merge subscription records: {e}")

        # Update payment records
        if 'payment_received_ids' in self._fields and 'res.partner.payment.recieved' in self.env:
            try:
                with self.env.cr.savepoint():
                    self.env['res.partner.payment.recieved'].search([
                        ('student_id', 'in', duplicates.ids)
                    ]).write({'student_id': self.id})
            except Exception as e:
                _logger.warning(f"[Contact Merge] Could not merge payment received records: {e}")

        if 'payment_slot_selection_ids' in self._fields and 'res.partner.payment.slot.selection' in self.env:
            try:
                with self.env.cr.savepoint():
                    self.env['res.partner.payment.slot.selection'].search([
                        ('student_id', 'in', duplicates.ids)
                    ]).write({'student_id': self.id})
            except Exception as e:
                _logger.warning(f"[Contact Merge] Could not merge payment slot selection records: {e}")

        if 'payment_paid_access_ids' in self._fields and 'res.partner.payment.paid.access' in self.env:
            try:
                with self.env.cr.savepoint():
                    self.env['res.partner.payment.paid.access'].search([
                        ('student_id', 'in', duplicates.ids)
                    ]).write({'student_id': self.id})
            except Exception as e:
                _logger.warning(f"[Contact Merge] Could not merge payment paid access records: {e}")

    def _merge_many2many_relations(self, duplicates):
        """Merge Many2many relations from duplicates to master"""
        # Merge student_parent_ids if exists
        if 'student_parent_ids' in self._fields:
            try:
                for dup in duplicates:
                    if 'student_parent_ids' in dup._fields:
                        dup_parents = dup.student_parent_ids
                        if dup_parents:
                            # Add duplicate's parents to master
                            master_parent_ids = self.student_parent_ids.ids
                            for parent in dup_parents:
                                if parent.id not in master_parent_ids:
                                    self.student_parent_ids = [(4, parent.id)]
            except Exception as e:
                _logger.warning(f"[Contact Merge] Could not merge many2many relations: {e}")
