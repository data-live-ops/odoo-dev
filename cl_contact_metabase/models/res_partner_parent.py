from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging
import json
import time

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'


    metabase_student_ids = fields.Char(string="Student IDs")
    student_parent_ids = fields.Many2many('res.partner', 'student_parent_rel_guardian', 'metabase_user_id', 'metabase_parent_id', string='Student Parents')


    @api.model
    def _sync_parent_with_retry(self):
        """Scheduled function to sync parents from Metabase with retry mechanism"""
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
                _logger.info(f"Retry attempt {retry_count}/{max_retries} for Metabase parent sync")
                # Wait before retrying
                time.sleep(retry_delay * 60)  # Convert minutes to seconds
                
            success = self._sync_parents()
            if success:
                if retry_count > 0:
                    _logger.info(f"Metabase parent sync succeeded after {retry_count} retries")
                return True
                
            retry_count += 1
            
        _logger.error(f"Metabase parent sync failed after {max_retries} retries")
        return False
    
    @api.model
    def _sync_new_parent_with_retry(self):
        """Scheduled function to sync new parents from Metabase with retry mechanism"""
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
                _logger.info(f"Retry attempt {retry_count}/{max_retries} for Metabase parent sync")
                # Wait before retrying
                time.sleep(retry_delay * 60)  # Convert minutes to seconds
                
            success = self._sync_new_parents()
            if success:
                if retry_count > 0:
                    _logger.info(f"Metabase new parent sync succeeded after {retry_count} retries")
                return True
                
            retry_count += 1
            
        _logger.error(f"Metabase new parent sync failed after {max_retries} retries")
        return False
    
    @api.model
    def _prepare_parent_vals(self, parent, sync_log):
        """Helper method to prepare parent values from Metabase data"""                
        return {
            # Metabase Fields
            "metabase_parent_id": str(parent[0]),

            # Standard Odoo fields
            "is_parent": True,
            "type": "contact",
            "contact_type": "parent",
            "name": str(parent[2]),
            "phone": parent[3],

            "metabase_last_sync": fields.Datetime.now(),
            "metabase_sync_log_id": sync_log.id,
        }
    
    @api.model
    def _sync_parents(self):
        """Function to sync parents from Metabase"""
        sync_log = False

        try:
            sync_log = self.env["metabase.sync.log"].create(
                {
                    "state": "processing",
                    "data_type": "parent",
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
            
            # Prepare Parent API endpoint URL with configurable settings
            parent_question = config.parent_details_question_url
            if not parent_question:
                raise UserError("Parent details question URL not configured")
            
            question_id = config.get_question_id(parent_question)
            
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

            for parent_data in data:
                metabase_parent_id = parent_data[0]
                metabase_student_id = parent_data[1]
                
                student_id = self.search([("metabase_student_id", "=", str(metabase_student_id))], limit=1)
                # Skip if student not found
                if not student_id:
                    _logger.warning(f"Student with ID {metabase_student_id} not found, skipping parent import")
                    continue
                
                vals = self._prepare_parent_vals(parent_data, sync_log)
                if not vals['name']:
                    vals['name'] = "Parent of " + student_id.name
                parent_contact_id = self.search([("metabase_parent_id", "=", str(metabase_parent_id))], limit=1)

                if parent_contact_id:
                    if parent_contact_id.metabase_student_ids and metabase_student_id:
                        # Convert existing student_ids to a set to remove duplicates
                        existing_student_ids = set(parent_contact_id.metabase_student_ids.split(','))
                        # Add new student_id if it doesn't already exist
                        new_id = metabase_student_id
                        if new_id not in existing_student_ids:
                            existing_student_ids.add(new_id)
                        # Convert back to comma-separated string
                        vals['metabase_student_ids'] = ','.join(existing_student_ids)
                    elif metabase_student_id:
                        vals['metabase_student_ids'] = metabase_student_id

                    parent_contact_id.write(vals)
                    updated_count += 1
                else:
                    # Handle case when metabase_student_ids is False or empty
                    if metabase_student_id:
                        # For new records, just use the guardian_id directly
                        # No need to check for duplicates since it's a new record
                        vals['metabase_student_ids'] = metabase_student_id
                    # Create new parent
                    parent_contact_id = self.create(vals)
                    created_count += 1
                
                student_id.student_parent_ids = [(4, parent_contact_id.id)]
                parent_contact_id.student_parent_ids = [(4, student_id.id)]

            sync_log.write(
                {
                    "state": "done",
                    "end_date": fields.Datetime.now(),
                    "total_records": len(data),
                    "created_count": created_count,
                    "updated_count": updated_count,
                }
            )

            if created_count == 0 and updated_count == 0:
                sync_log.write(
                    {
                        "state": "failed",
                        "error_message": "No parents matched with student records",
                    }
                )
                # sync_log.action_notify()
                return False

            _logger.info(f"Parent sync completed successfully: {created_count} created, {updated_count} updated")
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
            _logger.error("Parent sync failed: %s", str(e))
            return False
    
    @api.model
    def _sync_new_parents(self):
        """Function to sync new parents from Metabase"""
        sync_log = False

        try:
            sync_vals = {
                "state": "processing",
                "data_type": "parent",
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
            
            # Prepare new Parent API endpoint URL with configurable settings
            parent_question = config.new_parent_details_question_url
            if not parent_question:
                raise UserError("New parent details question URL not configured")
            
            question_id = config.get_question_id(parent_question)
            
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
                _logger.info("No data new parent received from Metabase")
                return False

            sync_log = self.env["metabase.sync.log"].create(sync_vals)
            for parent_data in data:
                metabase_parent_id = parent_data[0]
                metabase_student_id = parent_data[1]
                
                student_id = self.search([("metabase_student_id", "=", str(metabase_student_id))], limit=1)
                # Skip if student not found
                if not student_id:
                    _logger.warning(f"Student with ID {metabase_student_id} not found, skipping parent import")
                    continue
                
                vals = self._prepare_parent_vals(parent_data, sync_log)
                if not vals['name']:
                    vals['name'] = "Parent of " + student_id.name
                parent_contact_id = self.search([("metabase_parent_id", "=", str(metabase_parent_id))], limit=1)

                if parent_contact_id:
                    if parent_contact_id.metabase_student_ids and metabase_student_id:
                        # Convert existing student_ids to a set to remove duplicates
                        existing_student_ids = set(parent_contact_id.metabase_student_ids.split(','))
                        # Add new student_id if it doesn't already exist
                        new_id = metabase_student_id
                        if new_id not in existing_student_ids:
                            existing_student_ids.add(new_id)
                        # Convert back to comma-separated string
                        vals['metabase_student_ids'] = ','.join(existing_student_ids)
                    elif metabase_student_id:
                        vals['metabase_student_ids'] = metabase_student_id

                    parent_contact_id.write(vals)
                    updated_count += 1
                else:
                    # Handle case when metabase_student_ids is False or empty
                    if metabase_student_id:
                        # For new records, just use the guardian_id directly
                        # No need to check for duplicates since it's a new record
                        vals['metabase_student_ids'] = metabase_student_id
                    # Create new parent
                    parent_contact_id = self.create(vals)
                    created_count += 1
                
                student_id.student_parent_ids = [(4, parent_contact_id.id)]
                parent_contact_id.student_parent_ids = [(4, student_id.id)]

            sync_log.write(
                {
                    "state": "done",
                    "end_date": fields.Datetime.now(),
                    "total_records": len(data),
                    "created_count": created_count,
                    "updated_count": updated_count,
                }
            )

            if created_count == 0 and updated_count == 0:
                sync_log.write(
                    {
                        "state": "failed",
                        "error_message": "No new parents matched with student records",
                    }
                )
                # sync_log.action_notify()
                return False

            _logger.info(f"New parent sync completed successfully: {created_count} created, {updated_count} updated")
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
            _logger.error("New parent sync failed: %s", str(e))
            return False
    
    def action_sync_parent_from_metabase(self):
        """Manual sync action for parent data from Metabase"""
        self.ensure_one()
        if not self.is_parent:
            raise UserError("Only parent records can be synced from Metabase")

        sync_log = self.env["metabase.sync.log"].create({
            "state": "processing",
            "data_type": "parent",
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
            parent_question = config.parent_details_question_url
            if not parent_question:
                raise UserError("Parent details question URL not configured")
            
            question_id = config.get_question_id(parent_question)
            
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

            for parent_data in data:
                metabase_parent_id = parent_data[0]
                if self.metabase_parent_id == metabase_parent_id:
                    vals = self._prepare_parent_vals(parent_data, sync_log)
                    self.write(vals)
                    updated_count += 1

            # Update sync log
            if updated_count == 0:
                sync_log.write(
                    {
                        "state": "failed",
                        "end_date": fields.Datetime.now(),
                        "error_message": "No parent data found to sync",
                    }
                )
                sync_log.action_notify()
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Error'),
                        'message': _('No parent data found to sync from Metabase'),
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
            _logger.info("Parent sync completed successfully")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Parent %s successfully synced from Metabase') % self.name,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            error_message = str(e)
            _logger.error(f"Error syncing parent {self.name} from Metabase: {error_message}")
            
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
                    'message': _('Failed to sync parent %s from Metabase: %s') % (self.name, error_message),
                    'type': 'danger',
                    'sticky': True,
                }
            }
