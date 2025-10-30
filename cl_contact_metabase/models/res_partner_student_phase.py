from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging
import time

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _sync_student_phase_with_retry(self):
        """Scheduled function to sync student phase from Metabase with retry mechanism"""
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
                _logger.info(
                    f"Retry attempt {retry_count}/{max_retries} for Metabase student phase sync"
                )
                # Wait before retrying
                time.sleep(retry_delay * 60)  # Convert minutes to seconds

            success = self._sync_student_phase()
            if success:
                if retry_count > 0:
                    _logger.info(
                        f"Metabase student phase sync succeeded after {retry_count} retries"
                    )
                return True

            retry_count += 1

        _logger.error(
            f"Metabase student phase sync failed after {max_retries} retries"
        )
        return False

    @api.model
    def _prepare_student_phase_vals(self, student_phase_data, sync_log):
        """Helper method to prepare student phase values from Metabase data"""
        # Mapping dari nilai Metabase ke selection value
        phase_mapping = {
            "new student": "new",
            "paid student": "paid",
            "non paid": "non_paid",
            "non paid student": "non_paid",
        }

        # Get student_phase value dari Metabase (field index 1)
        metabase_phase_value = str(student_phase_data[1]).lower().strip()

        # Map ke selection value
        phase_value = phase_mapping.get(metabase_phase_value)

        if not phase_value:
            _logger.warning(
                f"Unknown student phase value from Metabase: {student_phase_data[1]}"
            )

        return {
            # Metabase Fields
            "metabase_student_phase": phase_value,
            "metabase_last_sync": fields.Datetime.now(),
            "metabase_sync_log_id": sync_log.id,
        }

    @api.model
    def _sync_student_phase(self):
        """Function to sync student phase from Metabase"""
        sync_log = False

        try:
            sync_log = self.env["metabase.sync.log"].create(
                {
                    "state": "processing",
                    "data_type": "student_phase",
                    "start_date": fields.Datetime.now(),
                }
            )
            if self.env.context.get("from_manual_sync"):
                sync_log.write(
                    {
                        "sync_type": "manual",
                    }
                )

            # Get configuration
            config = self.env["metabase.config"].search(
                [("active", "=", True)], limit=1
            )
            if not config:
                raise UserError("No active Metabase configuration found")

            # Get student phase data from Metabase (using config method with max_results support)
            _logger.info("Fetching student phase data from Metabase...")
            data = config.get_student_phase()

            if not data:
                raise UserError("No data received from Metabase")

            # Store raw response for debugging (get last query result)
            total_records = len(data)
            sync_log.raw_response = {"data": {"rows": []}, "row_count": total_records}  # Don't store all data to save space

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

                for student_phase_data in batch_data:
                    # Get user_id dari Metabase (field index 0)
                    metabase_user_id = student_phase_data[0]

                    # Find partner by metabase_user_id
                    student_contact_id = self.search(
                        [("metabase_user_id", "=", str(metabase_user_id))], limit=1
                    )

                    if student_contact_id:
                        # Skip if already has student phase (for resume capability)
                        if student_contact_id.metabase_student_phase:
                            batch_skipped += 1
                            continue

                        vals = self._prepare_student_phase_vals(student_phase_data, sync_log)
                        if vals.get("metabase_student_phase"):
                            student_contact_id.write(vals)
                            batch_updated += 1
                        else:
                            batch_skipped += 1
                    else:
                        batch_skipped += 1

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
                f"Student phase sync completed successfully. Updated: {updated_count}, Skipped: {skipped_count}"
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
            _logger.error("Student phase sync failed: %s", str(e))
            return False

    @api.model
    def _sync_student_phase_incremental(self):
        """
        Incremental sync for student phase - only process records updated in last 30 minutes
        Designed to run frequently (every 15 minutes) with small dataset
        """
        sync_log = False

        try:
            sync_log = self.env["metabase.sync.log"].create(
                {
                    "state": "processing",
                    "data_type": "student_phase_incremental",
                    "start_date": fields.Datetime.now(),
                }
            )
            if self.env.context.get("from_manual_sync"):
                sync_log.write(
                    {
                        "sync_type": "manual",
                    }
                )

            # Get configuration
            config = self.env["metabase.config"].search(
                [("active", "=", True)], limit=1
            )
            if not config:
                raise UserError("No active Metabase configuration found")

            # Get incremental student phase data (updated last 30 mins)
            _logger.info("Fetching incremental student phase data from Metabase...")
            data = config.get_student_phase_incremental()

            if not data:
                _logger.info("No recent student phase updates found")
                sync_log.write(
                    {
                        "state": "done",
                        "end_date": fields.Datetime.now(),
                        "total_records": 0,
                    }
                )
                return True

            # Store raw response for debugging
            total_records = len(data)
            sync_log.raw_response = {"data": {"rows": []}, "row_count": total_records}

            updated_count = 0
            created_count = 0
            skipped_count = 0

            _logger.info(f"Processing {total_records} recently updated student phase records")

            for student_phase_data in data:
                # Get user_id dari Metabase (field index 0)
                metabase_user_id = student_phase_data[0]

                # Find partner by metabase_user_id
                student_contact_id = self.search(
                    [("metabase_user_id", "=", str(metabase_user_id))], limit=1
                )

                if not student_contact_id:
                    skipped_count += 1
                    continue

                # Prepare new values
                vals = self._prepare_student_phase_vals(student_phase_data, sync_log)
                if not vals.get("metabase_student_phase"):
                    skipped_count += 1
                    continue

                # Compare with current value - only update if different or empty
                current_phase = student_contact_id.metabase_student_phase
                new_phase = vals.get("metabase_student_phase")

                if current_phase != new_phase:
                    # Value changed or was empty - UPDATE
                    student_contact_id.write(vals)

                    if current_phase:
                        # Phase changed (e.g., new -> paid)
                        _logger.info(
                            f"Student phase changed for {student_contact_id.name} "
                            f"(user_id: {metabase_user_id}): {current_phase} → {new_phase}"
                        )
                        updated_count += 1
                    else:
                        # First time fill
                        _logger.info(
                            f"Student phase set for {student_contact_id.name} "
                            f"(user_id: {metabase_user_id}): {new_phase}"
                        )
                        created_count += 1
                else:
                    # Same value - skip (no change)
                    skipped_count += 1

            sync_log.write(
                {
                    "state": "done",
                    "end_date": fields.Datetime.now(),
                    "total_records": total_records,
                    "updated_count": updated_count,
                    "created_count": created_count,
                    "skipped_count": skipped_count,
                }
            )

            _logger.info(
                f"Incremental student phase sync completed: "
                f"{created_count} new, {updated_count} changed, {skipped_count} unchanged"
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
            _logger.error("Incremental student phase sync failed: %s", str(e))
            return False

    @api.model
    def _sync_student_phase_incremental_with_retry(self):
        """Scheduled function with retry for incremental sync"""
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
                _logger.info(
                    f"Retry attempt {retry_count}/{max_retries} for incremental student phase sync"
                )
                # Wait before retrying
                time.sleep(retry_delay * 60)  # Convert minutes to seconds

            success = self._sync_student_phase_incremental()
            if success:
                if retry_count > 0:
                    _logger.info(
                        f"Incremental student phase sync succeeded after {retry_count} retries"
                    )
                return True

            retry_count += 1

        _logger.error(
            f"Incremental student phase sync failed after {max_retries} retries"
        )
        return False

    def action_sync_manual_student_phase(self):
        """Manual sync action for student phase data from Metabase"""
        self.ensure_one()
        if not self.metabase_user_id:
            raise UserError(
                "This contact does not have a Metabase User ID. Cannot sync student phase."
            )

        sync_log = self.env["metabase.sync.log"].create(
            {
                "state": "processing",
                "data_type": "student_phase",
                "start_date": fields.Datetime.now(),
                "sync_type": "manual",
                "partner_id": self.id,
            }
        )

        try:
            # Get configuration
            config = self.env["metabase.config"].search(
                [("active", "=", True)], limit=1
            )
            if not config:
                raise UserError("No active Metabase configuration found")

            # Get student phase data from Metabase (using config method with max_results support)
            _logger.info(f"Fetching student phase data for contact {self.name}...")
            data = config.get_student_phase()

            if not data:
                raise UserError("No data received from Metabase")

            # Store raw response for debugging
            sync_log.raw_response = {"data": {"rows": data}, "row_count": len(data)}
            updated_count = 0

            for student_phase_data in data:
                metabase_user_id = str(student_phase_data[0])
                if self.metabase_user_id == metabase_user_id:
                    vals = self._prepare_student_phase_vals(student_phase_data, sync_log)
                    if vals.get("metabase_student_phase"):
                        self.write(vals)
                        sync_log.partner_id = self.id
                        updated_count += 1
                        break

            if updated_count == 0:
                raise UserError(
                    f"No student phase data found in Metabase for user_id: {self.metabase_user_id}"
                )

            sync_log.write(
                {
                    "state": "done",
                    "end_date": fields.Datetime.now(),
                    "total_records": len(data),
                    "updated_count": updated_count,
                }
            )
            _logger.info("Student phase sync completed successfully")

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Success"),
                    "message": _("Student phase for %s successfully synced from Metabase")
                    % self.name,
                    "type": "success",
                    "sticky": False,
                },
            }
        except Exception as e:
            error_message = str(e)
            _logger.error(
                f"Error syncing student phase for {self.name} from Metabase: {error_message}"
            )

            # Update sync log
            sync_log.write(
                {
                    "state": "failed",
                    "end_date": fields.Datetime.now(),
                    "error_message": error_message,
                }
            )
            sync_log.action_notify()

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Error"),
                    "message": _("Failed to sync student phase for %s from Metabase: %s")
                    % (self.name, error_message),
                    "type": "danger",
                    "sticky": True,
                },
            }
