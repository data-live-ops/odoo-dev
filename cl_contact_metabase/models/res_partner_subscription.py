from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging
import json
import time
from datetime import datetime

_logger = logging.getLogger(__name__)

class ResPartnerSubscription(models.Model):
    _inherit = 'res.partner.subs'
    
    metabase_last_sync = fields.Datetime(string='Last Sync with Metabase')
    metabase_sync_log_id = fields.Many2one(
        "metabase.sync.log", string="Metabase Sync Log", tracking=True
    )

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    @api.model
    def _sync_student_subscription_with_retry(self):
        """Scheduled function to sync student subscriptions from Metabase with retry mechanism"""
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
                _logger.info(f"Retry attempt {retry_count}/{max_retries} for Metabase subscription sync")
                # Wait before retrying
                time.sleep(retry_delay * 60)  # Convert minutes to seconds
                
            success = self._sync_student_subscriptions()
            if success:
                if retry_count > 0:
                    _logger.info(f"Metabase subscription sync succeeded after {retry_count} retries")
                return True
                
            retry_count += 1
            
        _logger.error(f"Metabase subscription sync failed after {max_retries} retries")
        return False
    
    def _sync_new_subscription_with_retry(self):
        """Scheduled function to sync new student subscriptions from Metabase with retry mechanism"""
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
                _logger.info(f"Retry attempt {retry_count}/{max_retries} for Metabase new subscription sync")
                # Wait before retrying
                time.sleep(retry_delay * 60)  # Convert minutes to seconds
                
            success = self._sync_new_student_subscriptions()
            if success:
                if retry_count > 0:
                    _logger.info(f"Metabase new subscription sync succeeded after {retry_count} retries")
                return True
                
            retry_count += 1
            
        _logger.error(f"Metabase new subscription sync failed after {max_retries} retries")
        return False
    
    @api.model
    def _prepare_subscription_vals(self, subscription_data, sync_log):
        """Helper method to prepare subscription values from Metabase data"""                
        return {
            # Metabase Fields
            "subscription_id": str(subscription_data[0]),
            "student_user_id": str(subscription_data[1]),
            "status": str(subscription_data[2]),
            "subs_start_date": str(subscription_data[3]),
            "subs_end_date": str(subscription_data[4]),
            "cancellation_date": str(subscription_data[5]),
            "name": str(subscription_data[6]) if subscription_data[6] else False,
            "payment_type": str(subscription_data[7]) if subscription_data[7] else False,
            "subs_next_payment_date": str(subscription_data[8]),

            "metabase_last_sync": fields.Datetime.now(),
            "metabase_sync_log_id": sync_log.id,
        }
    
    @api.model
    def _sync_student_subscriptions(self):
        """Function to sync student subscriptions from Metabase"""
        sync_log = False

        try:
            sync_log = self.env["metabase.sync.log"].create(
                {
                    "state": "processing",
                    "data_type": "subscription",
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
            
            # Prepare Subscription API endpoint URL with configurable settings
            subscription_question = config.subscription_data_question_url
            if not subscription_question:
                raise UserError("Subscription data question URL not configured")
            
            question_id = config.get_question_id(subscription_question)
            
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

            for subscription_data in data:
                subscription_id = subscription_data[0]
                student_user_id = subscription_data[1]
                
                # Find the student contact
                student_contact = self.search([("metabase_user_id", "=", str(student_user_id))], limit=1)
                
                if student_contact:
                    # Prepare subscription values
                    vals = self._prepare_subscription_vals(subscription_data, sync_log)
                    
                    # Check if subscription already exists
                    existing_subscription = self.env['res.partner.subs'].search([
                        ('subscription_id', '=', subscription_id),
                        ('subs_student_id', '=', student_contact.id)
                    ], limit=1)
                    
                    if existing_subscription:
                        # Update existing subscription
                        existing_subscription.write(vals)
                        updated_count += 1
                    else:
                        # Create new subscription
                        vals['subs_student_id'] = student_contact.id
                        self.env['res.partner.subs'].create(vals)
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
            _logger.info("Student subscription sync completed successfully")
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
            _logger.error("Student subscription sync failed: %s", str(e))
            return False
    
    @api.model
    def _sync_new_student_subscriptions(self):
        """Function to sync new student subscriptions from Metabase"""
        sync_log = False

        try:
            sync_vals = {
                "state": "processing",
                "data_type": "subscription",
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
            
            # Prepare Subscription API endpoint URL with configurable settings
            subscription_question = config.new_subscription_data_question_url
            if not subscription_question:
                raise UserError("New subscription data question URL not configured")
            
            question_id = config.get_question_id(subscription_question)
            
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
                _logger.info("No data new subscription received from Metabase")
                return False

            sync_log = self.env["metabase.sync.log"].create(sync_vals)
            for subscription_data in data:
                subscription_id = subscription_data[0]
                student_user_id = subscription_data[1]
                
                # Find the student contact
                student_contact = self.search([("metabase_user_id", "=", str(student_user_id))], limit=1)
                
                if student_contact:
                    # Prepare subscription values
                    vals = self._prepare_subscription_vals(subscription_data, sync_log)
                    
                    # Check if subscription already exists
                    existing_subscription = self.env['res.partner.subs'].search([
                        ('subscription_id', '=', subscription_id),
                        ('subs_student_id', '=', student_contact.id)
                    ], limit=1)
                    
                    if existing_subscription:
                        # Update existing subscription
                        existing_subscription.write(vals)
                        updated_count += 1
                    else:
                        # Create new subscription
                        vals['subs_student_id'] = student_contact.id
                        self.env['res.partner.subs'].create(vals)
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
            _logger.info("Student subscription sync completed successfully")
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
            _logger.error("Student subscription sync failed: %s", str(e))
            return False
    
    def action_sync_student_subscription_from_metabase(self):
        """Manual sync action for subscription data from Metabase for a specific student"""
        self.ensure_one()
        if not self.is_student:
            raise UserError("Only student records can be synced from Metabase")

        sync_log = self.env["metabase.sync.log"].create({
            "state": "processing",
            "data_type": "subscription",
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
            subscription_question = config.subscription_data_question_url
            if not subscription_question:
                raise UserError("Subscription data question URL not configured")
            
            question_id = config.get_question_id(subscription_question)
            
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

            for subscription_data in data:
                subscription_id = subscription_data[0]
                student_user_id = subscription_data[1]
                
                # Check if this subscription belongs to the current student
                if str(student_user_id) == self.metabase_user_id:
                    # Prepare subscription values
                    vals = self._prepare_subscription_vals(subscription_data, sync_log)
                    
                    # Check if subscription already exists
                    existing_subscription = self.env['res.partner.subs'].search([
                        ('subscription_id', '=', subscription_id),
                        ('subs_student_id', '=', self.id)
                    ], limit=1)
                    
                    if existing_subscription:
                        # Update existing subscription
                        existing_subscription.write(vals)
                        updated_count += 1
                    else:
                        # Create new subscription
                        vals['subs_student_id'] = self.id
                        self.env['res.partner.subs'].create(vals)
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
                    'message': _('Subscription data for %s successfully synced from Metabase') % self.name,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            error_message = str(e)
            _logger.error(f"Error syncing subscription data for {self.name} from Metabase: {error_message}")
            
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
                    'message': _('Failed to sync subscription data for %s from Metabase: %s') % (self.name, error_message),
                    'type': 'danger',
                    'sticky': True,
                }
            }
