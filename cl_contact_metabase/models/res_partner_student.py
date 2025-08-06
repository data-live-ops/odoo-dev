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
    metabase_sync_log_ids = fields.One2many(
        "metabase.sync.log", "partner_id", string="Metabase Sync Logs"
    )

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
    def _sync_new_students_with_retry(self):
        """Scheduled function to sync new students from Metabase with retry mechanism"""
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
                _logger.info(f"Retry attempt {retry_count}/{max_retries} for Metabase new student sync")
                # Wait before retrying
                time.sleep(retry_delay * 60)  # Convert minutes to seconds
                
            success = self._sync_new_students()
            if success:
                if retry_count > 0:
                    _logger.info(f"Metabase new student sync succeeded after {retry_count} retries")
                return True
                
            retry_count += 1
            
        _logger.error(f"Metabase new student sync failed after {max_retries} retries")
        return False
    
    @api.model
    def _prepare_student_vals(self, student, sync_log):
        """Helper method to prepare student values from Metabase data"""                
        return {
            # Metabase Fields
            "metabase_user_id": str(student[0]),
            "metabase_student_id": str(student[1]),
            "metabase_grade": str(student[6]),
            "metabase_curriculum": str(student[7]),
            "metabase_school": str(student[8]),
            "metabase_notification_consent": str(student[9]),

            # Standard Odoo fields
            "is_student": True,
            "type": "contact",
            "contact_type": "student",
            "name": str(student[2]),
            "email": str(student[3]),
            "phone": student[4],
            "city": str(student[5]),
            "metabase_city": str(student[5]),

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
        """Function to sync students details from Metabase"""
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
                metabase_student_id = student_data[1]
                student_contact_id = self.search([("metabase_student_id", "=", str(metabase_student_id))], limit=1)
                
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
            if sync_log:
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
    
    @api.model
    def _sync_new_students(self):
        """Function to sync new students details from Metabase"""
        sync_log = False

        try:
            sync_vals = {
                "state": "processing",
                "data_type": "student",
                "start_date": fields.Datetime.now(),
            }
            
            if self.env.context.get("from_manual_sync"):
                sync_vals.update({
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
            student_question = config.new_student_details_question_url
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

            sync_vals.update({
                'raw_response': results,
            })
            created_count = 0
            updated_count = 0
            if not data:
                _logger.info("No data new student received from Metabase")
                return False

            sync_log = self.env["metabase.sync.log"].create(sync_vals)
            for student_data in data:
                vals = self._prepare_student_vals(student_data, sync_log)
                metabase_student_id = student_data[1]
                student_contact_id = self.search([("metabase_student_id", "=", str(metabase_student_id))], limit=1)
                
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
            if sync_log:
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
                metabase_student_id = student_data[1]
                if self.metabase_student_id == metabase_student_id:
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
