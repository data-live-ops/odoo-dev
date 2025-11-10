from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ContactMergeWizard(models.TransientModel):
    _name = 'contact.merge.wizard'
    _description = 'Contact Merge Wizard'

    duplicate_group_ids = fields.One2many(
        'contact.merge.duplicate.group',
        'wizard_id',
        string='Duplicate Groups'
    )
    total_duplicates = fields.Integer(
        string='Total Duplicate Groups',
        compute='_compute_total_duplicates'
    )

    @api.depends('duplicate_group_ids')
    def _compute_total_duplicates(self):
        for wizard in self:
            wizard.total_duplicates = len(wizard.duplicate_group_ids)

    def action_find_duplicates(self):
        """Find duplicate contacts based on normalized phone numbers"""
        self.ensure_one()

        # Clear existing groups
        self.duplicate_group_ids.unlink()

        # Get all contacts with phone or mobile
        contacts = self.env['res.partner'].search([
            '|',
            ('mobile', '!=', False),
            ('phone', '!=', False),
        ])

        # Group by normalized phone
        phone_groups = {}

        for contact in contacts:
            # Normalize phone numbers
            phones = []
            if contact.mobile:
                phones.append(self._normalize_phone(contact.mobile))
            if contact.phone and contact.phone != contact.mobile:
                phones.append(self._normalize_phone(contact.phone))

            # Add to groups
            for normalized_phone in phones:
                if normalized_phone:
                    if normalized_phone not in phone_groups:
                        phone_groups[normalized_phone] = []
                    if contact.id not in [c.id for c in phone_groups[normalized_phone]]:
                        phone_groups[normalized_phone].append(contact)

        # Create duplicate groups (only where count > 1)
        duplicate_count = 0
        for normalized_phone, contacts_list in phone_groups.items():
            if len(contacts_list) > 1:
                # Create group
                group = self.env['contact.merge.duplicate.group'].create({
                    'wizard_id': self.id,
                    'normalized_phone': normalized_phone,
                    'contact_count': len(contacts_list),
                })

                # Create contact lines
                for contact in contacts_list:
                    self.env['contact.merge.contact.line'].create({
                        'group_id': group.id,
                        'partner_id': contact.id,
                        'is_master': False,  # User will select master manually
                    })

                duplicate_count += 1

        _logger.info(f"[Contact Merge] Found {duplicate_count} duplicate groups")

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'contact.merge.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _normalize_phone(self, phone):
        """
        Normalize phone number for comparison
        Returns: 628xxx format (standard Indonesian WhatsApp format)
        """
        if not phone:
            return False

        # Clean phone number
        cleaned = str(phone).replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')

        # Convert to 628xxx format
        if cleaned.startswith('628'):
            return cleaned
        elif cleaned.startswith('08'):
            return '628' + cleaned[1:]
        elif cleaned.startswith('8') and len(cleaned) >= 10:
            return '628' + cleaned
        elif cleaned.startswith('62') and not cleaned.startswith('628'):
            return '628' + cleaned[2:]

        return cleaned  # Return as is if no pattern matches

    def action_merge_all(self):
        """Merge all duplicate groups (auto-select master)"""
        self.ensure_one()

        merged_count = 0
        for group in self.duplicate_group_ids:
            # Auto-select master: prefer contact with most data
            master = group._auto_select_master()
            if master:
                group.action_merge()
                merged_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Merged %s duplicate groups successfully') % merged_count,
                'type': 'success',
                'sticky': False,
            }
        }


class ContactMergeDuplicateGroup(models.TransientModel):
    _name = 'contact.merge.duplicate.group'
    _description = 'Contact Merge Duplicate Group'

    wizard_id = fields.Many2one('contact.merge.wizard', required=True, ondelete='cascade')
    normalized_phone = fields.Char(string='Phone Number', readonly=True)
    contact_count = fields.Integer(string='Duplicate Count', readonly=True)
    contact_line_ids = fields.One2many(
        'contact.merge.contact.line',
        'group_id',
        string='Contacts'
    )
    master_contact_id = fields.Many2one(
        'res.partner',
        string='Master Contact',
        compute='_compute_master_contact',
        store=True
    )

    @api.depends('contact_line_ids.is_master')
    def _compute_master_contact(self):
        for group in self:
            master_line = group.contact_line_ids.filtered('is_master')
            group.master_contact_id = master_line[0].partner_id if master_line else False

    def action_merge(self):
        """Merge duplicate contacts in this group"""
        self.ensure_one()

        master_line = self.contact_line_ids.filtered('is_master')
        if not master_line:
            raise UserError(_('Please select a master contact to keep'))

        master = master_line[0].partner_id
        duplicates = self.contact_line_ids.filtered(lambda l: not l.is_master).mapped('partner_id')

        if not duplicates:
            raise UserError(_('No duplicate contacts to merge'))

        # Merge logic
        master._merge_with_duplicates(duplicates)

        # Remove this group from wizard
        self.unlink()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Contacts merged successfully into %s') % master.name,
                'type': 'success',
                'sticky': False,
            }
        }

    def _auto_select_master(self):
        """Auto-select master based on data completeness"""
        if not self.contact_line_ids:
            return False

        # Score each contact
        best_contact = False
        best_score = -1

        for line in self.contact_line_ids:
            contact = line.partner_id
            score = 0

            # Prefer contact with more data
            if contact.email: score += 10
            if contact.metabase_student_id: score += 20
            if contact.metabase_parent_id: score += 20
            if contact.metabase_user_id: score += 15
            if contact.metabase_student_phase: score += 10
            if contact.metabase_grade: score += 5
            if contact.subscription_ids: score += len(contact.subscription_ids) * 2
            if contact.attendance_ids: score += len(contact.attendance_ids)

            # Prefer older contact (created first)
            if contact.create_date:
                score += 5

            if score > best_score:
                best_score = score
                best_contact = line

        if best_contact:
            best_contact.is_master = True
            return best_contact.partner_id

        return False


class ContactMergeContactLine(models.TransientModel):
    _name = 'contact.merge.contact.line'
    _description = 'Contact Merge Contact Line'

    group_id = fields.Many2one('contact.merge.duplicate.group', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Contact', required=True)
    is_master = fields.Boolean(string='Keep This Contact', default=False)

    # Display fields
    name = fields.Char(related='partner_id.name', readonly=True)
    mobile = fields.Char(related='partner_id.mobile', readonly=True)
    phone = fields.Char(related='partner_id.phone', readonly=True)
    email = fields.Char(related='partner_id.email', readonly=True)
    metabase_student_id = fields.Char(related='partner_id.metabase_student_id', readonly=True)
    metabase_student_phase = fields.Selection(related='partner_id.metabase_student_phase', readonly=True)
    create_date = fields.Datetime(related='partner_id.create_date', readonly=True)

    @api.onchange('is_master')
    def _onchange_is_master(self):
        """Ensure only one master per group"""
        if self.is_master:
            # Uncheck other masters in same group
            other_lines = self.group_id.contact_line_ids.filtered(
                lambda l: l.id != self.id and l.is_master
            )
            for line in other_lines:
                line.is_master = False
