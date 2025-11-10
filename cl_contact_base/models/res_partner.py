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
            self.write(merge_vals)

        # 2. Update all references to point to master contact
        self._update_references_to_master(duplicate_ids)

        # 3. Merge One2many relations (attendance, subscription, payment)
        self._merge_one2many_relations(duplicates)

        # 4. Merge Many2many relations (student_parent_ids if exists)
        self._merge_many2many_relations(duplicates)

        # 5. Add note to chatter about merge
        merge_note = f"Merged duplicate contacts: {', '.join([f'{d.name} (ID:{d.id})' for d in duplicates])}"
        self.message_post(body=merge_note)

        # 6. Archive duplicates instead of delete (safer)
        duplicates.write({'active': False})

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
        if hasattr(self, 'attendance_ids'):
            self.env['res.partner.attendance.main'].search([
                ('partner_id', 'in', duplicates.ids)
            ]).write({'partner_id': self.id})

        # Update subscription records
        if hasattr(self, 'subscription_ids'):
            self.env['res.partner.subs'].search([
                ('subs_student_id', 'in', duplicates.ids)
            ]).write({'subs_student_id': self.id})

        # Update payment records
        if hasattr(self, 'payment_received_ids'):
            self.env['res.partner.payment.recieved'].search([
                ('student_id', 'in', duplicates.ids)
            ]).write({'student_id': self.id})

        if hasattr(self, 'payment_slot_selection_ids'):
            self.env['res.partner.payment.slot.selection'].search([
                ('student_id', 'in', duplicates.ids)
            ]).write({'student_id': self.id})

        if hasattr(self, 'payment_paid_access_ids'):
            self.env['res.partner.payment.paid.access'].search([
                ('student_id', 'in', duplicates.ids)
            ]).write({'student_id': self.id})

    def _merge_many2many_relations(self, duplicates):
        """Merge Many2many relations from duplicates to master"""
        # Merge student_parent_ids if exists
        if hasattr(self, 'student_parent_ids'):
            for dup in duplicates:
                if dup.student_parent_ids:
                    # Add duplicate's parents to master
                    for parent in dup.student_parent_ids:
                        if parent.id not in self.student_parent_ids.ids:
                            self.student_parent_ids = [(4, parent.id)]
