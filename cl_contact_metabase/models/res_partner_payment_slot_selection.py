from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging
import json
import time
from datetime import datetime

_logger = logging.getLogger(__name__)

class ResPartnerPaymentSlotSelection(models.Model):
    _inherit = 'res.partner.payment.slot.selection'
    
    metabase_last_sync = fields.Datetime(string='Last Sync with Metabase')
    metabase_sync_log_id = fields.Many2one(
        "metabase.sync.log", string="Metabase Sync Log", tracking=True
    )

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    @api.model
    def _sync_payment_slot_selection_with_retry(self):
        """Scheduled function to sync payment slot selection data from Metabase with retry mechanism"""
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
                _logger.info(f"Retry attempt {retry_count}/{max_retries} for Metabase payment slot selection sync")
                # Wait before retrying
                time.sleep(retry_delay * 60)  # Convert minutes to seconds
                
            success = self._sync_payment_slot_selection()
            if success:
                if retry_count > 0:
                    _logger.info(f"Metabase payment slot selection sync succeeded after {retry_count} retries")
                return True
                
            retry_count += 1
            
        _logger.error(f"Metabase payment slot selection sync failed after {max_retries} retries")
        return False

    @api.model
    def _sync_new_payment_slot_selection_with_retry(self):
        """Scheduled function to sync new payment slot selection data from Metabase with retry mechanism"""
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
                _logger.info(f"Retry attempt {retry_count}/{max_retries} for Metabase payment slot selection sync")
                # Wait before retrying
                time.sleep(retry_delay * 60)  # Convert minutes to seconds
                
            success = self._sync_new_payment_slot_selection()
            if success:
                if retry_count > 0:
                    _logger.info(f"Metabase new payment slot selection sync succeeded after {retry_count} retries")
                return True
                
            retry_count += 1
            
        _logger.error(f"Metabase new payment slot selection sync failed after {max_retries} retries")
        return False

    @api.model
    def _prepare_payment_slot_selection_vals(self, slot_data, sync_log):
        """Helper method to prepare payment slot selection values from Metabase data"""                
        return {
            # Metabase Fields - mapping based on expected Metabase column order
            "hash_id": str(slot_data[0]) if slot_data[0] else False,
            "package_subscription_id": str(slot_data[1]) if slot_data[1] else False,
            "metabase_user_id": str(slot_data[2]) if slot_data[2] else False,
            "package_id": str(slot_data[3]) if slot_data[3] else False,
            "course_batch_pairs": str(slot_data[4]) if slot_data[4] else False,
            "status": str(slot_data[5]) if slot_data[5] else False,
            "rounded_opt_in_date": str(slot_data[6]) if slot_data[6] else False,

            "metabase_last_sync": fields.Datetime.now(),
            "metabase_sync_log_id": sync_log.id,
        }

    @api.model
    def _sync_payment_slot_selection(self):
        """Function to sync payment slot selection data from Metabase"""
        sync_log = False

        try:
            sync_log = self.env["metabase.sync.log"].create(
                {
                    "state": "processing",
                    "data_type": "payment_slot_selection",
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

            # Get payment slot selection data from Metabase (using config method with max_results support)
            _logger.info("Fetching payment slot selection details from Metabase...")
            data = config.get_slot_selection_succeeded()

            if not data:
                raise UserError("No data received from Metabase")

            # Store raw response for debugging (don't store all data to save space)
            total_records = len(data)
            sync_log.raw_response = {"data": {"rows": []}, "row_count": total_records}

            created_count = 0
            updated_count = 0
            skipped_count = 0

            # Process in batches to avoid timeout for large datasets
            batch_size = 1000
            total_batches = (total_records + batch_size - 1) // batch_size

            _logger.info(f"Processing {total_records} records in {total_batches} batches of {batch_size}")

            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, total_records)
                batch_data = data[start_idx:end_idx]

                batch_created = 0
                batch_updated = 0
                batch_skipped = 0

                for slot_data in batch_data:
                    try:
                        metabase_user_id = slot_data[2]  # user_id is at index 2
                        hash_id = slot_data[0]  # hash_id is at index 0

                        # Find the student contact
                        student_contact = self.search([("metabase_user_id", "=", str(metabase_user_id))], limit=1)

                        if student_contact:
                            # Prepare payment slot selection values
                            vals = self._prepare_payment_slot_selection_vals(slot_data, sync_log)

                            # Check if slot selection record already exists
                            existing_slot = self.env['res.partner.payment.slot.selection'].search([
                                ('hash_id', '=', hash_id),
                                ('student_id', '=', student_contact.id)
                            ], limit=1)

                            if existing_slot:
                                # Update existing slot selection record
                                existing_slot.write(vals)
                                batch_updated += 1
                            else:
                                # Create new slot selection record
                                vals['student_id'] = student_contact.id
                                self.env['res.partner.payment.slot.selection'].create(vals)
                                batch_created += 1
                        else:
                            batch_skipped += 1
                    except Exception as e:
                        _logger.warning(f"Error processing payment slot selection for hash {hash_id}: {str(e)}")
                        batch_skipped += 1
                        continue

                created_count += batch_created
                updated_count += batch_updated
                skipped_count += batch_skipped

                # Commit after each batch to save progress
                self.env.cr.commit()

                # Log progress
                progress_pct = ((batch_num + 1) / total_batches) * 100
                _logger.info(
                    f"Batch {batch_num + 1}/{total_batches} ({progress_pct:.1f}%): "
                    f"Created {batch_created}, Updated {batch_updated}, Skipped {batch_skipped}. "
                    f"Total so far: {created_count} created, {updated_count} updated, {skipped_count} skipped"
                )

                # Update sync log progress periodically (every 10 batches)
                if (batch_num + 1) % 10 == 0 or (batch_num + 1) == total_batches:
                    sync_log.write({
                        "created_count": created_count,
                        "updated_count": updated_count,
                        "skipped_count": skipped_count,
                    })
                    self.env.cr.commit()

            sync_log.write(
                {
                    "state": "done",
                    "end_date": fields.Datetime.now(),
                    "total_records": total_records,
                    "created_count": created_count,
                    "updated_count": updated_count,
                    "skipped_count": skipped_count,
                }
            )
            self.env.cr.commit()

            _logger.info(
                f"Payment slot selection sync completed successfully. Created: {created_count}, "
                f"Updated: {updated_count}, Skipped: {skipped_count}"
            )
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
            _logger.error("Payment slot selection sync failed: %s", str(e))
            return False
    
    @api.model
    def _sync_new_payment_slot_selection(self):
        """Function to sync new payment slot selection data from Metabase"""
        sync_log = False

        try:
            sync_vals = {
                "state": "processing",
                "data_type": "payment_slot_selection",
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
            
            # Prepare new Payment Slot Selection API endpoint URL with configurable settings
            slot_question = config.new_payment_slot_selection_question_url
            if not slot_question:
                raise UserError("Payment slot selection question URL not configured")
            
            question_id = config.get_question_id(slot_question)
            
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
                _logger.info("No data new payment slot selection from Metabase")
                return False

            sync_log = self.env["metabase.sync.log"].create(sync_vals)
            for slot_data in data:
                metabase_user_id = slot_data[2]  # user_id is at index 2
                hash_id = slot_data[0]  # hash_id is at index 0
                
                # Find the student contact
                student_contact = self.search([("metabase_user_id", "=", str(metabase_user_id))], limit=1)
                
                if student_contact:
                    # Prepare payment slot selection values
                    vals = self._prepare_payment_slot_selection_vals(slot_data, sync_log)
                    
                    # Check if slot selection record already exists
                    existing_slot = self.env['res.partner.payment.slot.selection'].search([
                        ('hash_id', '=', hash_id),
                        ('student_id', '=', student_contact.id)
                    ], limit=1)
                    
                    if existing_slot:
                        # Update existing slot selection record
                        existing_slot.write(vals)
                        updated_count += 1
                    else:
                        # Create new slot selection record
                        vals['student_id'] = student_contact.id
                        self.env['res.partner.payment.slot.selection'].create(vals)
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
            _logger.info("New Payment slot selection sync completed successfully")
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
            _logger.error("New Payment slot selection sync failed: %s", str(e))
            return False

    def action_sync_payment_slot_selection_from_metabase(self):
        """Manual sync action for payment slot selection data from Metabase for a specific student"""
        self.ensure_one()
        if not self.is_student:
            raise UserError("Only student records can be synced from Metabase")

        sync_log = self.env["metabase.sync.log"].create({
            "state": "processing",
            "data_type": "payment_slot_selection",
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
            slot_question = config.payment_slot_selection_question_url
            if not slot_question:
                raise UserError("Payment slot selection question URL not configured")
            
            question_id = config.get_question_id(slot_question)
            
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

            for slot_data in data:
                metabase_user_id = slot_data[2]  # user_id is at index 2
                hash_id = slot_data[0]  # hash_id is at index 0
                
                # Check if this slot selection belongs to the current student
                if str(metabase_user_id) == self.metabase_user_id:
                    # Prepare payment slot selection values
                    vals = self._prepare_payment_slot_selection_vals(slot_data, sync_log)
                    
                    # Check if slot selection record already exists
                    existing_slot = self.env['res.partner.payment.slot.selection'].search([
                        ('hash_id', '=', hash_id),
                        ('student_id', '=', self.id)
                    ], limit=1)
                    
                    if existing_slot:
                        # Update existing slot selection record
                        existing_slot.write(vals)
                        updated_count += 1
                    else:
                        # Create new slot selection record
                        vals['student_id'] = self.id
                        self.env['res.partner.payment.slot.selection'].create(vals)
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
                    'message': _('Payment slot selection data for %s successfully synced from Metabase') % self.name,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            error_message = str(e)
            _logger.error(f"Error syncing payment slot selection data for {self.name} from Metabase: {error_message}")
            
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
                    'message': _('Failed to sync payment slot selection data for %s from Metabase: %s') % (self.name, error_message),
                    'type': 'danger',
                    'sticky': True,
                }
            }
