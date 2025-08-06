from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging
import json
import time
from datetime import datetime

_logger = logging.getLogger(__name__)

class ResPartnerPaymentPaidAccess(models.Model):
    _inherit = 'res.partner.payment.paid.access'
    
    metabase_last_sync = fields.Datetime(string='Last Sync with Metabase')
    metabase_sync_log_id = fields.Many2one(
        "metabase.sync.log", string="Metabase Sync Log", tracking=True
    )

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    @api.model
    def _sync_payment_paid_access_with_retry(self):
        """Scheduled function to sync payment paid access data from Metabase with retry mechanism"""
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
                _logger.info(f"Retry attempt {retry_count}/{max_retries} for Metabase payment paid access sync")
                # Wait before retrying
                time.sleep(retry_delay * 60)  # Convert minutes to seconds
                
            success = self._sync_payment_paid_access()
            if success:
                if retry_count > 0:
                    _logger.info(f"Metabase payment paid access sync succeeded after {retry_count} retries")
                return True
                
            retry_count += 1
            
        _logger.error(f"Metabase payment paid access sync failed after {max_retries} retries")
        return False

    @api.model
    def _sync_new_payment_paid_access_with_retry(self):
        """Scheduled function to sync new payment paid access data from Metabase with retry mechanism"""
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
                _logger.info(f"Retry attempt {retry_count}/{max_retries} for Metabase payment paid access sync")
                # Wait before retrying
                time.sleep(retry_delay * 60)  # Convert minutes to seconds
                
            success = self._sync_new_payment_paid_access()
            if success:
                if retry_count > 0:
                    _logger.info(f"Metabase new payment paid access sync succeeded after {retry_count} retries")
                return True
                
            retry_count += 1
            
        _logger.error(f"Metabase new payment paid access sync failed after {max_retries} retries")
        return False

    @api.model
    def _sync_payment_paid_access(self):
        """Function to sync payment paid access data from Metabase"""
        sync_log = False

        try:
            sync_log = self.env["metabase.sync.log"].create(
                {
                    "state": "processing",
                    "data_type": "payment_paid_access",
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
            
            # Prepare Payment Paid Access API endpoint URL with configurable settings
            access_question = config.payment_paid_access_question_url
            if not access_question:
                raise UserError("Payment paid access question URL not configured")
            
            question_id = config.get_question_id(access_question)
            
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

            for access_data in data:
                metabase_user_id = access_data[0]  # metabase_user_id is at index 0
                package_id = access_data[2]  # package_id is at index 2
                
                # Find the student contact
                student_contact = self.search([("metabase_user_id", "=", str(metabase_user_id))], limit=1)
                
                if student_contact:
                    # Prepare payment paid access values
                    vals = self._prepare_payment_paid_access_vals(access_data, sync_log)
                    
                    # Check if paid access record already exists
                    existing_access = self.env['res.partner.payment.paid.access'].search([
                        ('metabase_user_id', '=', str(metabase_user_id)),
                        ('package_id', '=', str(package_id)),
                        ('student_id', '=', student_contact.id)
                    ], limit=1)
                    
                    if existing_access:
                        # Update existing paid access record
                        existing_access.write(vals)
                        updated_count += 1
                    else:
                        # Create new paid access record
                        vals['student_id'] = student_contact.id
                        self.env['res.partner.payment.paid.access'].create(vals)
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
            _logger.info("Payment paid access sync completed successfully")
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
            _logger.error("Payment paid access sync failed: %s", str(e))
            return False
    
    @api.model
    def _sync_new_payment_paid_access(self):
        """Function to sync new payment paid access data from Metabase"""
        sync_log = False

        try:
            sync_vals = {
                "state": "processing",
                "data_type": "payment_paid_access",
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
            
            # Prepare New Payment Paid Access API endpoint URL with configurable settings
            access_question = config.new_payment_paid_access_question_url
            if not access_question:
                raise UserError("New Payment paid access question URL not configured")
            
            question_id = config.get_question_id(access_question)
            
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
            sync_vals.update({
                'raw_response': results,
            })
            created_count = 0
            updated_count = 0
            if not data:
                _logger.info("No data new payment paid access from Metabase")
                return False

            sync_log = self.env["metabase.sync.log"].create(sync_vals)
            for access_data in data:
                metabase_user_id = access_data[0]  # metabase_user_id is at index 0
                package_id = access_data[2]  # package_id is at index 2
                
                # Find the student contact
                student_contact = self.search([("metabase_user_id", "=", str(metabase_user_id))], limit=1)
                
                if student_contact:
                    # Prepare payment paid access values
                    vals = self._prepare_payment_paid_access_vals(access_data, sync_log)
                    
                    # Check if paid access record already exists
                    existing_access = self.env['res.partner.payment.paid.access'].search([
                        ('metabase_user_id', '=', str(metabase_user_id)),
                        ('package_id', '=', str(package_id)),
                        ('student_id', '=', student_contact.id)
                    ], limit=1)
                    
                    if existing_access:
                        # Update existing paid access record
                        existing_access.write(vals)
                        updated_count += 1
                    else:
                        # Create new paid access record
                        vals['student_id'] = student_contact.id
                        self.env['res.partner.payment.paid.access'].create(vals)
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
            _logger.info("New Payment paid access sync completed successfully")
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
            _logger.error("New Payment paid access sync failed: %s", str(e))
            return False

    def _prepare_payment_paid_access_vals(self, access_data, sync_log):
        """Prepare payment paid access values from Metabase data"""
        return {
            # Metabase Fields - mapping based on expected Metabase column order
            "metabase_user_id": str(access_data[0]) if access_data[0] else False,
            "status": str(access_data[1]) if access_data[1] else False,
            "package_id": str(access_data[2]) if access_data[2] else False,
            "name": str(access_data[3]) if access_data[3] else False,
            "updated_at": str(access_data[4]) if access_data[4] else False,
            
            # Sync tracking fields
            "metabase_last_sync": fields.Datetime.now(),
            "metabase_sync_log_id": sync_log.id,
        }

    def action_sync_payment_paid_access_from_metabase(self):
        """Manual sync action for payment paid access data from Metabase for a specific student"""
        self.ensure_one()
        if not self.is_student:
            raise UserError("Only student records can be synced from Metabase")

        sync_log = self.env["metabase.sync.log"].create({
            "state": "processing",
            "data_type": "payment_paid_access",
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
            access_question = config.payment_paid_access_question_url
            if not access_question:
                raise UserError("Payment paid access question URL not configured")
            
            question_id = config.get_question_id(access_question)
            
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

            for access_data in data:
                metabase_user_id = access_data[0]  # metabase_user_id is at index 0
                package_id = access_data[2]  # package_id is at index 2
                
                # Check if this paid access belongs to the current student
                if str(metabase_user_id) == self.metabase_user_id:
                    # Prepare payment paid access values
                    vals = self._prepare_payment_paid_access_vals(access_data, sync_log)
                    
                    # Check if paid access record already exists
                    existing_access = self.env['res.partner.payment.paid.access'].search([
                        ('metabase_user_id', '=', str(metabase_user_id)),
                        ('package_id', '=', str(package_id)),
                        ('student_id', '=', self.id)
                    ], limit=1)
                    
                    if existing_access:
                        # Update existing paid access record
                        existing_access.write(vals)
                        updated_count += 1
                    else:
                        # Create new paid access record
                        vals['student_id'] = self.id
                        self.env['res.partner.payment.paid.access'].create(vals)
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
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Payment paid access data for %s successfully synced from Metabase') % self.name,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            error_message = str(e)
            _logger.error(f"Error syncing payment paid access data for {self.name} from Metabase: {error_message}")
            
            # Update sync log
            if sync_log:
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
                    'message': _('Failed to sync payment paid access data for %s from Metabase: %s') % (self.name, error_message),
                    'type': 'danger',
                    'sticky': True,
                }
            }
