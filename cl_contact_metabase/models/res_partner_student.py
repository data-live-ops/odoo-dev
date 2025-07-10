from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging
import json
import time

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    # Additional fields to identify the contact type
    is_student = fields.Boolean(string='Is Student', default=False)
    is_parent = fields.Boolean(string='Is Parent', default=False)

    # Fields to store Metabase IDs
    metabase_sync_log_id = fields.Many2one(
        "metabase.sync.log", string="Metabase Sync Log", tracking=True
    )
    metabase_last_sync = fields.Datetime(string='Last Sync with Metabase')
    # metabase_sync_log_ids = fields.One2many(
    #     "metabase.sync.log", "partner_id", string="Metabase Sync Logs"
    # )

    @api.model
    def _sync_students_with_retry(self):
        """Scheduled function to sync students from Metabase with retry mechanism"""
        # Get configuration
        config = self.env["metabase.config"].search([("active", "=", True)], limit=1)
        if not config:
            _logger.error("No active Metabase configuration found")
            return False
            
        # Get retry settings
        max_retries = config.max_retries if config.max_retries > 0 else 3
        retry_delay = config.retry_delay if config.retry_delay > 0 else 5  # minutes
        
        # Try to sync
        retry_count = 0
        last_error = None
        
        while retry_count <= max_retries:
            if retry_count > 0:
                _logger.info(f"Retry attempt {retry_count}/{max_retries} for Metabase student sync")
                # Wait before retrying
                time.sleep(retry_delay * 60)  # Convert minutes to seconds
                
            success = self._sync_students()
            if success:
                if retry_count > 0:
                    _logger.info(f"Metabase student sync succeeded after {retry_count} retries")
                return True
                
            retry_count += 1
            
        _logger.error(f"Metabase student sync failed after {max_retries} retries")
        return False
    
    @api.model
    def _prepare_student_vals(self, student, sync_log):
        """Helper method to prepare student values from Metabase data"""                
        return {
            # Metabase Fields
            "metabase_user_id": str(student[0]),
            "metabase_grade": str(student[5]),
            "metabase_curriculum": str(student[6]),
            "metabase_school": str(student[7]),
            "metabase_city": str(student[4]),
            "metabase_notification_consent": str(student[8]),

            # Standard Odoo fields
            "is_student": True,
            "type": "contact",
            "name": str(student[1]),
            "email": str(student[2]),
            "phone": student[3],
            "city": str(student[4]),

            "metabase_last_sync": fields.Datetime.now(),
            "metabase_sync_log_id": sync_log.id,
        }
    
    @api.model
    def _check_metabase_session_token(self):
        config = self.env["metabase.config"].search([("active", "=", True)], limit=1)
        if not config:
            raise UserError("Metabase configuration not found")
        return config.check_session()
    
    @api.model
    def _sync_students(self):
        """Function to sync students from Metabase"""
        sync_log = False

        try:
            sync_log = self.env["metabase.sync.log"].create(
                {
                    "state": "processing",
                    "data_type": "student",
                    "start_date": fields.Datetime.now(),
                }
            )
            if self.env.context.get("from_manual_sync"):
                sync_log.write({
                    "sync_type": "manual",
                })
            
            # Get configuration
            config = self.env["metabase.config"].search(
                [("active", "=", True)], limit=1
            )
            if not config:
                raise UserError("No active Metabase configuration found")
            
            # Get token
            if not config.check_session():
                raise UserError("Failed to get valid session token")
            headers = {
                "X-Metabase-Session": config.session_token
            }
            
            # Prepare Student API endpoint URL with configurable settings
            student_question = config.student_details_question_url
            if not student_question:
                raise UserError("Student details question URL not configured")
            
            question_id = config.get_question_id(student_question)
            
            # First get the question details
            card_response = requests.get(
                f"{config.base_url.rstrip('/')}/api/card/{question_id}",
                headers=headers
            )
            
            if card_response.status_code != 200:
                raise UserError(f"Error getting question details: {card_response.text}")
            
            # Then get the results
            results_response = requests.post(
                f"{config.base_url.rstrip('/')}/api/card/{question_id}/query",
                headers=headers
            )
            
            if not results_response.status_code == 202:
                raise UserError(f"Error getting question results: {results_response.text}")
            
            data = []
            results = results_response.json()
            if results and 'data' in results and 'rows' in results['data']:
                data = results['data']['rows']

            sync_log.raw_response = results
            created_count = 0
            updated_count = 0

            for student_data in data:
                vals = self._prepare_student_vals(student_data, sync_log)
                metabase_user_id = student_data[0]
                student_contact_id = self.search([("metabase_user_id", "=", str(metabase_user_id))], limit=1)
                
                if student_contact_id:
                    student_contact_id.write(vals)
                    updated_count += 1
                else:
                    student_contact_id = self.create(vals)
                    created_count += 1

            sync_log.write(
                {
                    "state": "done",
                    "end_date": fields.Datetime.now(),
                    "total_records": len(data),
                    "created_count": created_count,
                    "updated_count": updated_count,
                }
            )
            _logger.info("Student sync completed successfully")
            return True

        except Exception as e:
            sync_log.write(
                {
                    "state": "failed",
                    "end_date": fields.Datetime.now(),
                    "error_message": str(e),
                }
            )
            sync_log.action_notify()
            _logger.error("Student sync failed: %s", str(e))
            return False
    
    def action_sync_manual_student(self):
        """Manual sync action for student data from Metabase"""
        self.ensure_one()
        if not self.is_student:
            raise UserError("Only student records can be synced from Metabase")

        sync_log = self.env["metabase.sync.log"].create({
            "state": "processing",
            "data_type": "student",
            "start_date": fields.Datetime.now(),
            "sync_type": "manual",
            "partner_id": self.id
        })

        try:
            # Get configuration
            config = self.env["metabase.config"].search(
                [("active", "=", True)], limit=1
            )
            if not config:
                raise UserError("No active Metabase configuration found")
            
            # Get token
            if not config.check_session():
                raise UserError("Failed to get valid session token")
            headers = {
                "X-Metabase-Session": config.session_token
            }
            
            # Prepare API endpoint URL with configurable settings
            student_question = config.student_details_question_url
            if not student_question:
                raise UserError("Student details question URL not configured")
            
            question_id = config.get_question_id(student_question)
            
            # First get the question details
            card_response = requests.get(
                f"{config.base_url.rstrip('/')}/api/card/{question_id}",
                headers=headers
            )
            
            if card_response.status_code != 200:
                raise UserError(f"Error getting question details: {card_response.text}")
            
            # Then get the results
            results_response = requests.post(
                f"{config.base_url.rstrip('/')}/api/card/{question_id}/query",
                headers=headers
            )
            
            if not results_response.status_code == 202:
                raise UserError(f"Error getting question results: {results_response.text}")
            
            data = []
            results = results_response.json()
            if results and 'data' in results and 'rows' in results['data']:
                data = results['data']['rows']

            sync_log.raw_response = results
            created_count = 0
            updated_count = 0

            for student_data in data:
                metabase_user_id = student_data[0]
                if self.metabase_user_id == metabase_user_id:
                    vals = self._prepare_student_vals(student_data, sync_log)
                    self.write(vals)
                    updated_count += 1

            # Update sync log
            if updated_count == 0:
                sync_log.write(
                    {
                        "state": "failed",
                        "end_date": fields.Datetime.now(),
                        "error_message": "No student data found to sync",
                    }
                )
                sync_log.action_notify()
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Error'),
                        'message': _('No student data found to sync from Metabase'),
                        'type': 'warning',
                        'sticky': False,
                    }
                }
            sync_log.write(
                {
                    "state": "done",
                    "end_date": fields.Datetime.now(),
                    "total_records": len(data),
                    "created_count": created_count,
                    "updated_count": updated_count,
                }
            )
            _logger.info("Student sync completed successfully")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Student %s successfully synced from Metabase') % self.name,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            error_message = str(e)
            _logger.error(f"Error syncing student {self.name} from Metabase: {error_message}")
            
            # Update sync log
            sync_log.write({
                'state': 'failed',
                'end_date': fields.Datetime.now(),
                'error_message': error_message,
            })
            sync_log.action_notify()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Failed to sync student %s from Metabase: %s') % (self.name, error_message),
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    def action_sync_from_metabase(self):
        """Sync this contact from Metabase data"""
        self.ensure_one()
        
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
