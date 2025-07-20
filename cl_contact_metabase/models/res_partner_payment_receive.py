from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging
import json
import time
from datetime import datetime

_logger = logging.getLogger(__name__)

class ResPartnerPaymentReceived(models.Model):
    _inherit = 'res.partner.payment.recieved'
    
    metabase_last_sync = fields.Datetime(string='Last Sync with Metabase')
    metabase_sync_log_id = fields.Many2one(
        "metabase.sync.log", string="Metabase Sync Log", tracking=True
    )

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    @api.model
    def _sync_payment_received_with_retry(self):
        """Scheduled function to sync payment received data from Metabase with retry mechanism"""
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
                _logger.info(f"Retry attempt {retry_count}/{max_retries} for Metabase payment received sync")
                # Wait before retrying
                time.sleep(retry_delay * 60)  # Convert minutes to seconds
                
            success = self._sync_payment_received()
            if success:
                if retry_count > 0:
                    _logger.info(f"Metabase payment received sync succeeded after {retry_count} retries")
                return True
                
            retry_count += 1
            
        _logger.error(f"Metabase payment received sync failed after {max_retries} retries")
        return False
    
    @api.model
    def _prepare_payment_received_vals(self, payment_data, sync_log):
        """Helper method to prepare payment received values from Metabase data"""                
        return {
            # Metabase Fields - mapping based on expected Metabase column order
            "metabase_user_id": str(payment_data[0]) if payment_data[0] else False,
            "paid_amount": str(payment_data[1]) if payment_data[1] else False,
            "package_name": str(payment_data[2]) if payment_data[2] else False,
            "payment_link": str(payment_data[3]) if payment_data[3] else False,
            "invoice_id": str(payment_data[4]) if payment_data[4] else False,
            "payment_method": str(payment_data[5]) if payment_data[5] else False,
            "payment_channel": str(payment_data[6]) if payment_data[6] else False,
            "sales_agent_email": str(payment_data[7]) if payment_data[7] else False,
            "payment_context": str(payment_data[8]) if payment_data[8] else False,
            "payment_for_date": str(payment_data[9]) if payment_data[9] else False,
            "retention_payment_type": str(payment_data[10]) if payment_data[10] else False,

            "metabase_last_sync": fields.Datetime.now(),
            "metabase_sync_log_id": sync_log.id,
        }
    
    @api.model
    def _sync_payment_received(self):
        """Function to sync payment received data from Metabase"""
        sync_log = False

        try:
            sync_log = self.env["metabase.sync.log"].create(
                {
                    "state": "processing",
                    "data_type": "payment_received",
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
            
            # Prepare Payment Received API endpoint URL with configurable settings
            payment_question = config.payment_received_question_url
            if not payment_question:
                raise UserError("Payment received question URL not configured")
            
            question_id = config.get_question_id(payment_question)
            
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

            for payment_data in data:
                metabase_user_id = payment_data[0]
                invoice_id = payment_data[4]  # Assuming invoice_id is at index 4
                
                # Find the student contact
                student_contact = self.search([("metabase_user_id", "=", str(metabase_user_id))], limit=1)
                
                if student_contact:
                    # Prepare payment received values
                    vals = self._prepare_payment_received_vals(payment_data, sync_log)
                    
                    # Check if payment record already exists
                    existing_payment = self.env['res.partner.payment.recieved'].search([
                        ('invoice_id', '=', invoice_id),
                        ('student_id', '=', student_contact.id)
                    ], limit=1)
                    
                    if existing_payment:
                        # Update existing payment record
                        existing_payment.write(vals)
                        updated_count += 1
                    else:
                        # Create new payment record
                        vals['student_id'] = student_contact.id
                        self.env['res.partner.payment.recieved'].create(vals)
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
            _logger.info("Payment received sync completed successfully")
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
            _logger.error("Payment received sync failed: %s", str(e))
            return False
    
    def action_sync_payment_received_from_metabase(self):
        """Manual sync action for payment received data from Metabase for a specific student"""
        self.ensure_one()
        if not self.is_student:
            raise UserError("Only student records can be synced from Metabase")

        sync_log = self.env["metabase.sync.log"].create({
            "state": "processing",
            "data_type": "payment_received",
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
            payment_question = config.payment_received_question_url
            if not payment_question:
                raise UserError("Payment received question URL not configured")
            
            question_id = config.get_question_id(payment_question)
            
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

            for payment_data in data:
                metabase_user_id = payment_data[0]
                invoice_id = payment_data[4]  # Assuming invoice_id is at index 4
                
                # Check if this payment belongs to the current student
                if str(metabase_user_id) == self.metabase_user_id:
                    # Prepare payment received values
                    vals = self._prepare_payment_received_vals(payment_data, sync_log)
                    
                    # Check if payment record already exists
                    existing_payment = self.env['res.partner.payment.recieved'].search([
                        ('invoice_id', '=', invoice_id),
                        ('student_id', '=', self.id)
                    ], limit=1)
                    
                    if existing_payment:
                        # Update existing payment record
                        existing_payment.write(vals)
                        updated_count += 1
                    else:
                        # Create new payment record
                        vals['student_id'] = self.id
                        self.env['res.partner.payment.recieved'].create(vals)
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
                    'message': _('Payment received data for %s successfully synced from Metabase') % self.name,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            error_message = str(e)
            _logger.error(f"Error syncing payment received data for {self.name} from Metabase: {error_message}")
            
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
                    'message': _('Failed to sync payment received data for %s from Metabase: %s') % (self.name, error_message),
                    'type': 'danger',
                    'sticky': True,
                }
            }
