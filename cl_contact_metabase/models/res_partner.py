from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    # Fields to store Metabase IDs
    metabase_id = fields.Char(string='Metabase ID', index=True, copy=False)
    metabase_parent_id = fields.Char(string='Metabase Parent ID', index=True, copy=False)
    metabase_last_sync = fields.Datetime(string='Last Sync with Metabase')
    
    # Additional fields from Metabase
    grade = fields.Char(string='Grade')
    curriculum = fields.Char(string='Curriculum')
    lead_stage = fields.Char(string='Lead Stage')
    is_student = fields.Boolean(string='Is Student', default=False)
    is_parent = fields.Boolean(string='Is Parent', default=False)
    
    # Subscription related fields
    subscription_status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('paused', 'Paused')
    ], string='Subscription Status')
    subscription_start_date = fields.Datetime(string='Subscription Start Date')
    subscription_end_date = fields.Datetime(string='Subscription End Date')
    subscription_package = fields.Char(string='Subscription Package')
    
    def action_sync_from_metabase(self):
        """Sync this contact from Metabase data"""
        self.ensure_one()
        if not self.metabase_id:
            raise UserError(_("This contact doesn't have a Metabase ID. Cannot sync."))
        
        metabase_config = self.env['metabase.config'].search([('active', '=', True)], limit=1)
        if not metabase_config:
            raise UserError(_("No active Metabase configuration found."))
        
        if self.is_student:
            self._sync_student_data(metabase_config)
        elif self.is_parent:
            self._sync_parent_data(metabase_config)
        
        return True
    
    def _sync_student_data(self, metabase_config):
        """Sync student data from Metabase"""
        student_data = metabase_config.get_student_details()
        
        # Find the student with matching metabase_id
        for student in student_data:
            if student[0] == self.metabase_id:
                # Update student information
                # Assuming the structure: [id, name, email, phone, city, grade, curriculum, ...]
                self.write({
                    'name': student[1] if student[1] else self.name,
                    'email': student[2] if student[2] else self.email,
                    'phone': student[3] if student[3] else self.phone,
                    'city': student[4] if student[4] else self.city,
                    'grade': student[5] if student[5] else self.grade,
                    'curriculum': student[6] if student[6] else self.curriculum,
                    'metabase_last_sync': fields.Datetime.now(),
                })
                
                # Get lead stage data
                lead_stage_data = metabase_config.get_student_lead_stage()
                for lead in lead_stage_data:
                    if lead[0] == self.metabase_id:
                        self.lead_stage = lead[1] if len(lead) > 1 else ''
                        break
                
                # Get subscription data
                subscription_data = metabase_config.get_subscription_data()
                for subscription in subscription_data:
                    if subscription[1] == self.metabase_id:  # Assuming [subscription_id, student_id, status, start_date, end_date, ...]
                        self.write({
                            'subscription_status': subscription[2] if len(subscription) > 2 else 'inactive',
                            'subscription_start_date': subscription[3] if len(subscription) > 3 else False,
                            'subscription_end_date': subscription[4] if len(subscription) > 4 else False,
                            'subscription_package': subscription[6] if len(subscription) > 6 else '',
                        })
                        break
                
                return True
        
        _logger.warning(f"Student with Metabase ID {self.metabase_id} not found in Metabase data.")
        return False
    
    def _sync_parent_data(self, metabase_config):
        """Sync parent data from Metabase"""
        parent_data = metabase_config.get_parent_details()
        
        # Find the parent with matching metabase_id
        for parent in parent_data:
            if parent[0] == self.metabase_id:
                # Update parent information
                # Assuming the structure: [id, student_id, name, phone, ...]
                self.write({
                    'name': parent[2] if len(parent) > 2 and parent[2] else self.name,
                    'phone': parent[3] if len(parent) > 3 and parent[3] else self.phone,
                    'metabase_parent_id': parent[1] if len(parent) > 1 else False,
                    'metabase_last_sync': fields.Datetime.now(),
                })
                
                # Link to student if exists
                if len(parent) > 1 and parent[1]:
                    student = self.env['res.partner'].search([
                        ('metabase_id', '=', parent[1]),
                        ('is_student', '=', True)
                    ], limit=1)
                    
                    if student:
                        # Create parent-child relationship
                        student.parent_id = self.id
                
                return True
        
        _logger.warning(f"Parent with Metabase ID {self.metabase_id} not found in Metabase data.")
        return False
    
    @api.model
    def sync_all_contacts_from_metabase(self):
        """Sync all contacts from Metabase"""
        metabase_config = self.env['metabase.config'].search([('active', '=', True)], limit=1)
        if not metabase_config:
            _logger.error("No active Metabase configuration found.")
            return False
        
        # Sync students
        self._sync_all_students(metabase_config)
        
        # Sync parents
        self._sync_all_parents(metabase_config)
        
        return True
    
    @api.model
    def _sync_all_students(self, metabase_config):
        """Sync all students from Metabase"""
        student_data = metabase_config.get_student_details()
        
        for student in student_data:
            if not student[0]:  # Skip if no ID
                continue
                
            # Check if student already exists
            existing_student = self.search([
                ('metabase_id', '=', student[0]),
                ('is_student', '=', True)
            ], limit=1)
            
            if existing_student:
                # Update existing student
                existing_student._sync_student_data(metabase_config)
            else:
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
                self.create(vals)
    
    @api.model
    def _sync_all_parents(self, metabase_config):
        """Sync all parents from Metabase"""
        parent_data = metabase_config.get_parent_details()
        
        for parent in parent_data:
            if not parent[0]:  # Skip if no ID
                continue
                
            # Check if parent already exists
            existing_parent = self.search([
                ('metabase_id', '=', parent[0]),
                ('is_parent', '=', True)
            ], limit=1)
            
            if existing_parent:
                # Update existing parent
                existing_parent._sync_parent_data(metabase_config)
            else:
                # Create new parent
                vals = {
                    'metabase_id': parent[0],
                    'metabase_parent_id': parent[1] if len(parent) > 1 else False,
                    'name': parent[2] if len(parent) > 2 and parent[2] else 'Unknown Parent',
                    'phone': parent[3] if len(parent) > 3 else False,
                    'is_parent': True,
                    'metabase_last_sync': fields.Datetime.now(),
                }
                new_parent = self.create(vals)
                
                # Link to student if exists
                if len(parent) > 1 and parent[1]:
                    student = self.search([
                        ('metabase_id', '=', parent[1]),
                        ('is_student', '=', True)
                    ], limit=1)
                    
                    if student:
                        # Create parent-child relationship
                        student.parent_id = new_parent.id
