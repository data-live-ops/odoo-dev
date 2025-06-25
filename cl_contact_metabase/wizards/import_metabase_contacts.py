from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class ImportMetabaseContacts(models.TransientModel):
    _name = 'import.metabase.contacts'
    _description = 'Import Contacts from Metabase'
    
    metabase_config_id = fields.Many2one('metabase.config', string='Metabase Configuration', 
                                         required=True, domain=[('active', '=', True)])
    import_students = fields.Boolean(string='Import Students', default=True)
    import_parents = fields.Boolean(string='Import Parents', default=True)
    update_existing = fields.Boolean(string='Update Existing Contacts', default=True,
                                    help='If checked, existing contacts will be updated with Metabase data')
    
    def action_import(self):
        """Import contacts from Metabase"""
        self.ensure_one()
        
        if not self.import_students and not self.import_parents:
            raise UserError(_("Please select at least one type of contact to import."))
        
        if not self.metabase_config_id:
            raise UserError(_("Please select a Metabase configuration."))
        
        # Check connection
        if not self.metabase_config_id.check_session():
            raise UserError(_("Failed to connect to Metabase. Please check your configuration."))
        
        imported_count = 0
        updated_count = 0
        
        # Import students
        if self.import_students:
            student_data = self.metabase_config_id.get_student_details()
            
            for student in student_data:
                if not student[0]:  # Skip if no ID
                    continue
                    
                # Check if student already exists
                existing_student = self.env['res.partner'].search([
                    ('metabase_id', '=', student[0]),
                    ('is_student', '=', True)
                ], limit=1)
                
                if existing_student and self.update_existing:
                    # Update existing student
                    existing_student.write({
                        'name': student[1] if len(student) > 1 and student[1] else existing_student.name,
                        'email': student[2] if len(student) > 2 else existing_student.email,
                        'phone': student[3] if len(student) > 3 else existing_student.phone,
                        'city': student[4] if len(student) > 4 else existing_student.city,
                        'grade': student[5] if len(student) > 5 else existing_student.grade,
                        'curriculum': student[6] if len(student) > 6 else existing_student.curriculum,
                        'metabase_last_sync': fields.Datetime.now(),
                    })
                    updated_count += 1
                elif not existing_student:
                    # Create new student
                    vals = {
                        'metabase_id': student[0],
                        'name': student[1] if len(student) > 1 and student[1] else 'Unknown Student',
                        'email': student[2] if len(student) > 2 else False,
                        'phone': student[3] if len(student) > 3 else False,
                        'city': student[4] if len(student) > 4 else False,
                        'grade': student[5] if len(student) > 5 else False,
                        'curriculum': student[6] if len(student) > 6 else False,
                        'is_student': True,
                        'metabase_last_sync': fields.Datetime.now(),
                    }
                    self.env['res.partner'].create(vals)
                    imported_count += 1
        
        # Import parents
        if self.import_parents:
            parent_data = self.metabase_config_id.get_parent_details()
            
            for parent in parent_data:
                if not parent[0]:  # Skip if no ID
                    continue
                    
                # Check if parent already exists
                existing_parent = self.env['res.partner'].search([
                    ('metabase_id', '=', parent[0]),
                    ('is_parent', '=', True)
                ], limit=1)
                
                if existing_parent and self.update_existing:
                    # Update existing parent
                    existing_parent.write({
                        'metabase_parent_id': parent[1] if len(parent) > 1 else existing_parent.metabase_parent_id,
                        'name': parent[2] if len(parent) > 2 and parent[2] else existing_parent.name,
                        'phone': parent[3] if len(parent) > 3 else existing_parent.phone,
                        'metabase_last_sync': fields.Datetime.now(),
                    })
                    updated_count += 1
                elif not existing_parent:
                    # Create new parent
                    vals = {
                        'metabase_id': parent[0],
                        'metabase_parent_id': parent[1] if len(parent) > 1 else False,
                        'name': parent[2] if len(parent) > 2 and parent[2] else 'Unknown Parent',
                        'phone': parent[3] if len(parent) > 3 else False,
                        'is_parent': True,
                        'metabase_last_sync': fields.Datetime.now(),
                    }
                    new_parent = self.env['res.partner'].create(vals)
                    imported_count += 1
                    
                    # Link to student if exists
                    if len(parent) > 1 and parent[1]:
                        student = self.env['res.partner'].search([
                            ('metabase_id', '=', parent[1]),
                            ('is_student', '=', True)
                        ], limit=1)
                        
                        if student:
                            # Create parent-child relationship
                            student.parent_id = new_parent.id
        
        # Show success message
        message = _(f"Import completed successfully!\n\nImported: {imported_count} new contacts\nUpdated: {updated_count} existing contacts")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import Successful'),
                'message': message,
                'sticky': False,
                'type': 'success',
                'next': {
                    'type': 'ir.actions.act_window_close'
                }
            }
        }
