from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging
import json
import time

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    @api.model
    def _sync_lead_stages_with_retry(self):
        """Scheduled function to sync lead stages from Metabase with retry mechanism"""
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
                _logger.info(f"Retry attempt {retry_count}/{max_retries} for Metabase lead stage sync")
                # Wait before retrying
                time.sleep(retry_delay * 60)  # Convert minutes to seconds
                
            success = self._sync_lead_stages()
            if success:
                if retry_count > 0:
                    _logger.info(f"Metabase lead stage sync succeeded after {retry_count} retries")
                return True
                
            retry_count += 1
            
        _logger.error(f"Metabase lead stage sync failed after {max_retries} retries")
        return False
    
    @api.model
    def _prepare_lead_stage_vals(self, lead_stage, sync_log):
        """Helper method to prepare lead stage values from Metabase data"""                
        return {
            # Metabase Fields
            "metabase_lead_status": str(lead_stage[1]),

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
    def _sync_lead_stages(self):
        """Function to sync lead stages from Metabase"""
        sync_log = False

        try:
            sync_log = self.env["metabase.sync.log"].create(
                {
                    "state": "processing",
                    "data_type": "lead",
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

            # Get lead stage data from Metabase (using config method with max_results support)
            _logger.info("Fetching lead stage details from Metabase...")
            data = config.get_student_lead_stage()

            if not data:
                raise UserError("No data received from Metabase")

            # Store raw response for debugging (don't store all data to save space)
            total_records = len(data)
            sync_log.raw_response = {"data": {"rows": []}, "row_count": total_records}

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

                batch_updated = 0
                batch_skipped = 0

                for lead_stage_data in batch_data:
                    try:
                        vals = self._prepare_lead_stage_vals(lead_stage_data, sync_log)
                        metabase_user_id = lead_stage_data[0]
                        student_contact_id = self.search([("metabase_user_id", "=", str(metabase_user_id))], limit=1)

                        if student_contact_id:
                            student_contact_id.write(vals)
                            batch_updated += 1
                        else:
                            batch_skipped += 1
                    except Exception as e:
                        _logger.warning(f"Error processing lead stage for user {metabase_user_id}: {str(e)}")
                        batch_skipped += 1
                        continue

                updated_count += batch_updated
                skipped_count += batch_skipped

                # Commit after each batch to save progress
                self.env.cr.commit()

                # Log progress
                progress_pct = ((batch_num + 1) / total_batches) * 100
                _logger.info(
                    f"Batch {batch_num + 1}/{total_batches} ({progress_pct:.1f}%): "
                    f"Updated {batch_updated}, Skipped {batch_skipped}. "
                    f"Total so far: {updated_count} updated, {skipped_count} skipped"
                )

                # Update sync log progress periodically (every 10 batches)
                if (batch_num + 1) % 10 == 0 or (batch_num + 1) == total_batches:
                    sync_log.write({
                        "updated_count": updated_count,
                        "skipped_count": skipped_count,
                    })
                    self.env.cr.commit()

            sync_log.write(
                {
                    "state": "done",
                    "end_date": fields.Datetime.now(),
                    "total_records": total_records,
                    "updated_count": updated_count,
                    "skipped_count": skipped_count,
                }
            )
            self.env.cr.commit()

            _logger.info(
                f"Lead stage sync completed successfully. Updated: {updated_count}, Skipped: {skipped_count}"
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
            _logger.error("Lead stage sync failed: %s", str(e))
            return False
    
    def action_sync_manual_lead_stage(self):
        """Manual sync action for lead stage data from Metabase"""
        self.ensure_one()
        if not self.is_student:
            raise UserError("Only student records can be synced from Metabase")

        sync_log = self.env["metabase.sync.log"].create({
            "state": "processing",
            "data_type": "lead",
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
            lead_stage_question = config.student_lead_stage_question_url
            if not lead_stage_question:
                raise UserError("Student lead stage question URL not configured")
            
            question_id = config.get_question_id(lead_stage_question)
            
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

            for lead_stage_data in data:
                metabase_user_id = lead_stage_data[0]
                if self.metabase_user_id == metabase_user_id:
                    vals = self._prepare_lead_stage_vals(lead_stage_data, sync_log)
                    self.write(vals)
                    sync_log.partner_id = self.id
                    updated_count += 1

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
