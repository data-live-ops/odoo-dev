from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging
import json
import time
from datetime import datetime

_logger = logging.getLogger(__name__)

class ResPartnerAttendanceMain(models.Model):
    _inherit = 'res.partner.attendance.main'
    
    metabase_last_sync = fields.Datetime(string='Last Sync with Metabase')
    metabase_sync_log_id = fields.Many2one(
        "metabase.sync.log", string="Metabase Sync Log", tracking=True
    )

class ResPartnerAttendanceDetail(models.Model):
    _inherit = 'res.partner.attendance.detail'
    
    metabase_last_sync = fields.Datetime(string='Last Sync with Metabase')
    metabase_sync_log_id = fields.Many2one(
        "metabase.sync.log", string="Metabase Sync Log", tracking=True
    )

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    @api.model
    def _sync_attendance_main_with_retry(self):
        """Scheduled function to sync attendance main from Metabase with retry mechanism"""
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
                _logger.info(f"Retry attempt {retry_count}/{max_retries} for Metabase attendance main sync")
                # Wait before retrying
                time.sleep(retry_delay * 60)  # Convert minutes to seconds
                
            success = self._sync_attendance_main()
            if success:
                if retry_count > 0:
                    _logger.info(f"Metabase attendance main sync succeeded after {retry_count} retries")
                return True
                
            retry_count += 1
            
        _logger.error(f"Metabase attendance main sync failed after {max_retries} retries")
        return False
    
    @api.model
    def _sync_attendance_details_with_retry(self):
        """Scheduled function to sync attendance details from Metabase with retry mechanism"""
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
                _logger.info(f"Retry attempt {retry_count}/{max_retries} for Metabase attendance details sync")
                # Wait before retrying
                time.sleep(retry_delay * 60)  # Convert minutes to seconds
                
            success = self._sync_attendance_details()
            if success:
                if retry_count > 0:
                    _logger.info(f"Metabase attendance details sync succeeded after {retry_count} retries")
                return True
                
            retry_count += 1
            
        _logger.error(f"Metabase attendance details sync failed after {max_retries} retries")
        return False
    
    @api.model
    def _sync_attendance_with_retry(self):
        """Scheduled function to sync both attendance main and details from Metabase with retry mechanism"""
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
        
        while retry_count <= max_retries:
            if retry_count > 0:
                _logger.info(f"Retry attempt {retry_count}/{max_retries} for Metabase attendance sync")
                # Wait before retrying
                time.sleep(retry_delay * 60)  # Convert minutes to seconds
                
            # Sync attendance main first, then details
            main_success = self._sync_attendance_main()
            details_success = self._sync_attendance_details()
            
            if main_success and details_success:
                if retry_count > 0:
                    _logger.info(f"Metabase attendance sync succeeded after {retry_count} retries")
                return True
            elif main_success and not details_success:
                _logger.warning("Attendance main sync succeeded but details sync failed")
            elif not main_success and details_success:
                _logger.warning("Attendance details sync succeeded but main sync failed")
                
            retry_count += 1
            
        _logger.error(f"Metabase attendance sync failed after {max_retries} retries")
        return False
    
    @api.model
    def _prepare_attendance_main_vals(self, attendance_data, sync_log):
        """Helper method to prepare attendance main values from Metabase data"""                
        return {
            # Metabase Fields - adjust indices based on actual API response structure
            "student_user_id": str(attendance_data[0]) if attendance_data[0] else False,
            "live_class_id": str(attendance_data[1]) if attendance_data[1] else False,
            "time_of_joining": str(attendance_data[2]) if attendance_data[2] else False,
            # "class_topic": str(attendance_data[3]) if attendance_data[3] else False,
            # "class_subject": str(attendance_data[4]) if attendance_data[4] else False,
            # "teacher_name": str(attendance_data[5]) if attendance_data[5] else False,
            
            "metabase_last_sync": fields.Datetime.now(),
            "metabase_sync_log_id": sync_log.id,
        }
    
    @api.model
    def _prepare_attendance_details_vals(self, attendance_data, sync_log):
        """Helper method to prepare attendance details values from Metabase data"""                
        return {
            # Metabase Fields - adjust indices based on actual API response structure
            "live_class_id": str(attendance_data[0]) if attendance_data[0] else False,
            "class_topic": str(attendance_data[1]) if attendance_data[1] else False,
            "class_subject": str(attendance_data[2]) if attendance_data[2] else False,
            "class_start_time": str(attendance_data[3]) if attendance_data[3] else False,
            "teacher_name": str(attendance_data[4]) if attendance_data[4] else False,
            
            "metabase_last_sync": fields.Datetime.now(),
            "metabase_sync_log_id": sync_log.id,
        }
    
    @api.model
    def _sync_attendance_main(self):
        """Function to sync attendance main from Metabase"""
        sync_log = False

        try:
            sync_log = self.env["metabase.sync.log"].create(
                {
                    "state": "processing",
                    "data_type": "attendance",
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

            # Get attendance main data from Metabase (using config method with max_results support)
            _logger.info("Fetching attendance main details from Metabase...")
            data = config.get_attendance_main()

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

                for attendance_data in batch_data:
                    try:
                        student_user_id = attendance_data[0]
                        live_class_id = attendance_data[1]

                        # Find the student contact
                        student_contact = self.search([("metabase_user_id", "=", str(student_user_id))], limit=1)

                        if student_contact:
                            # Prepare attendance main values
                            vals = self._prepare_attendance_main_vals(attendance_data, sync_log)

                            # Check if attendance main already exists
                            existing_attendance = self.env['res.partner.attendance.main'].search([
                                ('partner_id', '=', student_contact.id),
                                ('live_class_id', '=', str(live_class_id)),
                            ], limit=1)

                            if existing_attendance:
                                # Update existing attendance main
                                existing_attendance.write(vals)
                                batch_updated += 1
                            else:
                                # Create new attendance main
                                vals['partner_id'] = student_contact.id
                                self.env['res.partner.attendance.main'].create(vals)
                                batch_created += 1
                        else:
                            batch_skipped += 1
                    except Exception as e:
                        _logger.warning(f"Error processing attendance main for user {student_user_id}: {str(e)}")
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
                f"Attendance main sync completed successfully. Created: {created_count}, "
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
            _logger.error("Attendance main sync failed: %s", str(e))
            return False
    
    @api.model
    def _sync_attendance_details(self):
        """Function to sync attendance details from Metabase"""
        sync_log = False

        try:
            sync_log = self.env["metabase.sync.log"].create(
                {
                    "state": "processing",
                    "data_type": "attendance",
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

            # Get attendance details data from Metabase (using config method with max_results support)
            _logger.info("Fetching attendance details from Metabase...")
            data = config.get_attendance_details()

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

                for attendance_data in batch_data:
                    try:
                        live_class_id = attendance_data[0]

                        # Find the attendance main record by live_class_id
                        attendance_main = self.env['res.partner.attendance.main'].search([
                            ('live_class_id', '=', str(live_class_id))
                        ], limit=1)

                        if attendance_main:
                            # Prepare attendance details values
                            vals = self._prepare_attendance_details_vals(attendance_data, sync_log)

                            # Check if attendance detail already exists
                            existing_detail = self.env['res.partner.attendance.detail'].search([
                                ('live_class_id', '=', str(live_class_id)),
                                ('attendance_main_id', '=', attendance_main.id)
                            ], limit=1)

                            if existing_detail:
                                # Update existing attendance detail
                                existing_detail.write(vals)
                                batch_updated += 1
                            else:
                                # Create new attendance detail
                                vals['attendance_main_id'] = attendance_main.id
                                self.env['res.partner.attendance.detail'].create(vals)
                                batch_created += 1

                            # set field class_topic, class_subject, teacher_name, class_start_time in attendance main
                            attendance_main.write(
                                {
                                    "class_topic": str(attendance_data[1]) if attendance_data[1] else False,
                                    "class_subject": str(attendance_data[2]) if attendance_data[2] else False,
                                    "class_start_time": str(attendance_data[3]) if attendance_data[3] else False,
                                    "teacher_name": str(attendance_data[4]) if attendance_data[4] else False,
                                }
                            )
                        else:
                            batch_skipped += 1
                    except Exception as e:
                        _logger.warning(f"Error processing attendance details for class {live_class_id}: {str(e)}")
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
                f"Attendance details sync completed successfully. Created: {created_count}, "
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
            _logger.error("Attendance details sync failed: %s", str(e))
            return False
    
    def action_sync_attendance_main_from_metabase(self):
        """Manual sync action for attendance main data from Metabase for a specific student"""
        self.ensure_one()
        if not self.is_student:
            raise UserError("Only student records can be synced from Metabase")

        sync_log = self.env["metabase.sync.log"].create({
            "state": "processing",
            "data_type": "attendance",
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
            attendance_main_question = config.attendance_main_question_url
            if not attendance_main_question:
                raise UserError("Attendance main question URL not configured")
            
            question_id = config.get_question_id(attendance_main_question)
            
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

            for attendance_data in data:
                student_user_id = attendance_data[0]
                live_class_id = attendance_data[1]
                
                # Check if this attendance belongs to the current student
                if str(student_user_id) == self.metabase_user_id:
                    # Prepare attendance main values
                    vals = self._prepare_attendance_main_vals(attendance_data, sync_log)
                    
                    # Check if attendance main already exists
                    existing_attendance = self.env['res.partner.attendance.main'].search([
                        ('student_user_id', '=', str(student_user_id)),
                        ('live_class_id', '=', str(live_class_id)),
                        ('partner_id', '=', self.id)
                    ], limit=1)
                    
                    if existing_attendance:
                        # Update existing attendance main
                        existing_attendance.write(vals)
                        updated_count += 1
                    else:
                        # Create new attendance main
                        vals['partner_id'] = self.id
                        self.env['res.partner.attendance.main'].create(vals)
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
                    'message': _('Attendance main data for %s successfully synced from Metabase') % self.name,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            error_message = str(e)
            _logger.error(f"Error syncing attendance main data for {self.name} from Metabase: {error_message}")
            
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
                    'message': _('Failed to sync attendance main data for %s from Metabase: %s') % (self.name, error_message),
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    def action_sync_attendance_details_from_metabase(self):
        """Manual sync action for attendance details data from Metabase for a specific student"""
        self.ensure_one()
        if not self.is_student:
            raise UserError("Only student records can be synced from Metabase")

        sync_log = self.env["metabase.sync.log"].create({
            "state": "processing",
            "data_type": "attendance",
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
            attendance_details_question = config.attendance_details_question_url
            if not attendance_details_question:
                raise UserError("Attendance details question URL not configured")
            
            question_id = config.get_question_id(attendance_details_question)
            
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

            # Get all attendance main records for this student
            student_attendance_mains = self.env['res.partner.attendance.main'].search([
                ('partner_id', '=', self.id)
            ])

            for attendance_data in data:
                live_class_id = attendance_data[0]
                
                # Find the attendance main record by live_class_id for this student
                attendance_main = student_attendance_mains.filtered(
                    lambda x: x.live_class_id == str(live_class_id)
                )
                
                if attendance_main:
                    # Prepare attendance details values
                    vals = self._prepare_attendance_details_vals(attendance_data, sync_log)
                    
                    # Check if attendance detail already exists
                    existing_detail = self.env['res.partner.attendance.detail'].search([
                        ('live_class_id', '=', str(live_class_id)),
                        ('attendance_main_id', '=', attendance_main.id)
                    ], limit=1)
                    
                    if existing_detail:
                        # Update existing attendance detail
                        existing_detail.write(vals)
                        updated_count += 1
                    else:
                        # Create new attendance detail
                        vals['attendance_main_id'] = attendance_main.id
                        self.env['res.partner.attendance.detail'].create(vals)
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
                    'message': _('Attendance details data for %s successfully synced from Metabase') % self.name,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            error_message = str(e)
            _logger.error(f"Error syncing attendance details data for {self.name} from Metabase: {error_message}")
            
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
                    'message': _('Failed to sync attendance details data for %s from Metabase: %s') % (self.name, error_message),
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    def action_sync_attendance_from_metabase(self):
        """Manual sync action for both attendance main and details data from Metabase for a specific student"""
        self.ensure_one()
        if not self.is_student:
            raise UserError("Only student records can be synced from Metabase")

        try:
            # Sync attendance main first
            main_result = self.action_sync_attendance_main_from_metabase()
            
            # Sync attendance details
            details_result = self.action_sync_attendance_details_from_metabase()
            
            # Check if both succeeded
            if (main_result.get('params', {}).get('type') == 'success' and 
                details_result.get('params', {}).get('type') == 'success'):
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Attendance data (main and details) for %s successfully synced from Metabase') % self.name,
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                # Partial success or failure
                error_messages = []
                if main_result.get('params', {}).get('type') != 'success':
                    error_messages.append('Main attendance sync failed')
                if details_result.get('params', {}).get('type') != 'success':
                    error_messages.append('Details attendance sync failed')
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Partial Success'),
                        'message': _('Attendance sync for %s completed with issues: %s') % (self.name, ', '.join(error_messages)),
                        'type': 'warning',
                        'sticky': True,
                    }
                }
                
        except Exception as e:
            error_message = str(e)
            _logger.error(f"Error syncing attendance data for {self.name} from Metabase: {error_message}")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Failed to sync attendance data for %s from Metabase: %s') % (self.name, error_message),
                    'type': 'danger',
                    'sticky': True,
                }
            }
