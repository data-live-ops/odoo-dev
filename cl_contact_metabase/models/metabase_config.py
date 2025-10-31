from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import requests
import logging
import json

_logger = logging.getLogger(__name__)


class MetabaseConfig(models.Model):
    _name = "metabase.config"
    _description = "Metabase Configuration"
    _rec_name = "name"

    name = fields.Char(string="Name", required=True)
    base_url = fields.Char(
        string="Base URL",
        required=True,
        help="Base URL of your Metabase instance (e.g., https://metabase.example.com)",
    )
    username = fields.Char(string="Username", required=True)
    password = fields.Char(string="Password", required=True, help="Metabase password")
    session_token = fields.Char(string="Session Token", readonly=True)
    session_expiry = fields.Datetime(string="Session Expiry", readonly=True)
    active = fields.Boolean(string="Active", default=True)
    email_notify = fields.Char(
        string="Notification Email",
        help="Email to notify when there are issues with the Metabase connection",
    )

    # Question IDs for different data types
    student_details_question_url = fields.Char(
        string="Student Details Question URL",
        default="https://metabase.dev.colearn.id/question/1137-odoo-student-details-live-class-db-v2",
    )
    parent_details_question_url = fields.Char(
        string="Parent Details Question URL",
        default="https://metabase.dev.colearn.id/question/1138-odoo-student-details-parent-v2",
    )
    student_lead_stage_question_url = fields.Char(
        string="Student Lead Stage Question URL",
        default="https://metabase.dev.colearn.id/question/1103-odoo-student-details-lead-stage",
    )
    student_phase_question_url = fields.Char(
        string="Student Phase Question URL",
        default="https://metabase.colearn.id/question/4142-student-phase-odoo",
    )
    student_phase_incremental_question_url = fields.Char(
        string="Student Phase Incremental Question URL (Last 30 min)",
        help="Question URL for incremental student phase sync (only records updated in last 30 minutes)",
    )
    subscription_data_question_url = fields.Char(
        string="Subscription Data Question URL",
        default="https://metabase.dev.colearn.id/question/1026-odoo-student-details-subscription-data",
    )
    payment_received_question_url = fields.Char(
        string="Payment Received Question URL",
        default="https://metabase.dev.colearn.id/question/1030-odoo-payment-payment-recieved",
    )
    payment_slot_selection_question_url = fields.Char(
        string="Payment Slot Selection Question URL",
        default="https://metabase.dev.colearn.id/question/1031-odoo-payment-slot-selection-succeeded",
    )
    payment_paid_access_question_url = fields.Char(
        string="Payment Paid Access Question URL",
        default="https://metabase.dev.colearn.id/question/1034-odoo-payment-paid-access-paused",
    )
    attendance_main_question_url = fields.Char(
        string="Attendance Main Question URL",
        default="https://metabase.dev.colearn.id/question/1028-odoo-attendance-paid-class-joined",
    )
    attendance_details_question_url = fields.Char(
        string="Attendance Details Question URL",
        default="https://metabase.dev.colearn.id/question/1027-odoo-attendance-paid-class-joined-class-details",
    )

    new_student_details_question_url = fields.Char(
        string="New Student Details Question URL",
        default="https://metabase.dev.colearn.id/question/1139-odoo-student-details-live-class-db-v2-filtered-last-1-hour",
    )
    new_subscription_data_question_url = fields.Char(
        string="New Subscription Data Question URL",
        default="https://metabase.dev.colearn.id/question/1141-odoo-subscription-filtered-last-1-hour",
    )
    new_parent_details_question_url = fields.Char(
        string="New Parent Details Question URL",
        default="https://metabase.dev.colearn.id/question/1140-odoo-student-details-parent-v2-filtered-last-1-hour",
    )
    new_payment_received_question_url = fields.Char(
        string="New Payment Received Question URL",
        default="https://metabase.dev.colearn.id/question/1142-odoo-payment-payment-recieved-filtered-last-1-hour",
    )
    new_payment_slot_selection_question_url = fields.Char(
        string="New Payment Slot Selection Question URL",
        default="https://metabase.dev.colearn.id/question/1144-odoo-payment-slot-selection-succeeded-filtered-last-1-hour",
    )
    new_payment_paid_access_question_url = fields.Char(
        string="New Payment Paid Access Question URL",
        default="https://metabase.dev.colearn.id/question/1143-odoo-payment-paid-access-paused-filtered-last-1-hour",
    )

    # Retry Configuration
    max_retries = fields.Integer(
        string="Max Retries",
        default=3,
        help="Maximum number of retry attempts for sync process",
    )
    retry_delay = fields.Integer(
        string="Retry Delay (minutes)",
        default=5,
        help="Delay between retry attempts in minutes",
    )

    _sql_constraints = [
        ("name_uniq", "unique(name)", "Configuration name must be unique!"),
        (
            "unique_base_url",
            "unique(base_url)",
            "This base_url is already used on another user.",
        ),
    ]

    def get_session_token(self):
        """Get a new session token from Metabase"""
        self.ensure_one()
        try:
            response = requests.post(
                f"{self.base_url.rstrip('/')}/api/session",
                json={"username": self.username, "password": self.password},
            )

            if response.status_code == 200:
                data = response.json()
                self.write(
                    {
                        "session_token": data.get("id"),
                        "session_expiry": fields.Datetime.now() + timedelta(hours=24),
                    }
                )
                return True
            else:
                _logger.error(f"Failed to get Metabase session token: {response.text}")
                return False

        except Exception as e:
            _logger.error(f"Error connecting to Metabase: {str(e)}")
            return False

    def check_session(self):
        """Check if session is valid, get new token if needed"""
        self.ensure_one()
        if (
            not self.session_token
            or not self.session_expiry
            or fields.Datetime.now() > self.session_expiry
        ):
            return self.get_session_token()
        return True

    def test_connection(self):
        """Test the connection to Metabase"""
        self.ensure_one()
        if self.get_session_token():
            # Try to get a simple question result to verify connection
            headers = {"X-Metabase-Session": self.session_token}
            try:
                response = requests.get(
                    f"{self.base_url.rstrip('/')}/api/user/current", headers=headers
                )
                if response.status_code == 200:
                    return {
                        "type": "ir.actions.client",
                        "tag": "display_notification",
                        "params": {
                            "title": _("Success"),
                            "message": _("Connection successful! Connected as %s")
                            % response.json().get("common_name", "Unknown"),
                            "type": "success",
                            "sticky": False,
                        },
                    }
                else:
                    return {
                        "type": "ir.actions.client",
                        "tag": "display_notification",
                        "params": {
                            "title": _("Error"),
                            "message": _("Connection failed! Error: %s")
                            % response.text,
                            "type": "danger",
                            "sticky": True,
                        },
                    }
            except Exception as e:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Error"),
                        "message": _("Connection failed! Error: %s") % str(e),
                        "type": "danger",
                        "sticky": True,
                    },
                }
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Error"),
                    "message": _(
                        "Failed to get session token. Please check your credentials."
                    ),
                    "type": "danger",
                    "sticky": True,
                },
            }

    @api.model
    def _get_default_notify_portcities_template(self):
        """
        default mail template for sending a mail to portcities
        """
        template_ref = (
            "cl_contact_metabase.metabase_config_notify_portcities_mail_template"
        )
        return self.env.ref(template_ref, raise_if_not_found=False)

    def action_notify_portcities(
        self, error_type=None, error_message=None, sync_log_url=None
    ):
        """Action notify portcities with enhanced error information"""
        action_mode = "portcities"
        for conf in self:
            send_to_portcities = conf.email_notify
            subject_detail = error_type or "Synchronization Issue"
            subject = _("Metabase Integration: %s", subject_detail)

            if not send_to_portcities:
                continue

            # Format recipient name from email address
            local_part = send_to_portcities.split("@")[0]
            name_part = local_part.replace(".", " ").replace("_", " ").replace("-", " ")
            notify_name = " ".join(word.capitalize() for word in name_part.split())
            if len(send_to_portcities.split("@")) > 2:
                notify_name = "Administrator"

            # Prepare context with detailed error information
            from datetime import datetime

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            context = {
                "user_name": notify_name,
                "error_type": error_type or "Synchronization Error",
                "error_message": error_message
                or "Unknown error occurred during Metabase synchronization",
                "error_time": current_time,
                "subject_detail": subject_detail,
                "sync_log_url": sync_log_url or False,
            }

            mail_mode = f"abp_{action_mode}"
            context[mail_mode] = True

            template_id = conf._get_default_notify_portcities_template()
            if not template_id:
                _logger.error("Email template for Metabase notification not found")
                continue

            conf = conf.with_context(
                **{
                    "default_subject": subject,
                    "default_email_to": send_to_portcities,
                    "mail_notify_force_send": True,
                },
                **context,
            )

            # Send mail with error handling
            try:
                template_id.with_context(**context).send_mail(
                    conf.id,
                    force_send=True,
                    raise_exception=True,
                )
                _logger.info(
                    "Notification sent to %s about Metabase integration issue: %s",
                    notify_name,
                    error_type or "Synchronization Error",
                )
            except Exception as e:
                error_msg = f"Failed to send email notification: {str(e)}"
                _logger.error(error_msg)
                # raise UserError(error_msg)
                return False

    def get_question_results(self, question_id, max_results=None):
        """Get results from a specific Metabase question/card

        Args:
            question_id: The Metabase question/card ID
            max_results: Maximum number of results to fetch (None = no limit, use with caution)
        """
        self.ensure_one()
        if not self.check_session():
            _logger.error("Failed to get valid session token")
            return None

        headers = {"X-Metabase-Session": self.session_token}

        try:
            # First get the question details
            card_response = requests.get(
                f"{self.base_url.rstrip('/')}/api/card/{question_id}", headers=headers
            )

            if card_response.status_code != 200:
                _logger.error(f"Error getting question details: {card_response.text}")
                return None

            # Use CSV export endpoint to get all data without limit for large datasets
            # Metabase /query endpoint has default 2000 row limit
            # Use /query/csv endpoint for unlimited export
            if max_results and max_results > 2000:
                # Use CSV export endpoint for large datasets (no limit)
                _logger.info(
                    f"Fetching large dataset (max_results={max_results}) using CSV export endpoint..."
                )
                results_response = requests.post(
                    f"{self.base_url.rstrip('/')}/api/card/{question_id}/query/csv",
                    headers=headers,
                )

                if results_response.status_code == 200:
                    # Parse CSV format
                    import csv
                    import io

                    rows = []
                    csv_reader = csv.reader(io.StringIO(results_response.text))

                    # Skip header row
                    header = next(csv_reader, None)

                    # Read all data rows
                    for row in csv_reader:
                        if row:  # Skip empty rows
                            rows.append(row)

                    _logger.info(
                        f"Fetched {len(rows)} rows from CSV export (columns: {header})"
                    )
                    return {"data": {"rows": rows, "columns": header}}
                else:
                    _logger.error(
                        f"Error getting CSV export: {results_response.status_code} - {results_response.text[:200]}"
                    )
                    # Fallback to standard endpoint
                    _logger.warning(
                        "Falling back to standard query endpoint (limited to 2000 rows)"
                    )
                    results_response = requests.post(
                        f"{self.base_url.rstrip('/')}/api/card/{question_id}/query",
                        headers=headers,
                    )
                    if results_response.status_code == 202:
                        return results_response.json()
                    return None
            else:
                # Standard query endpoint for small datasets (default 2000 limit)
                results_response = requests.post(
                    f"{self.base_url.rstrip('/')}/api/card/{question_id}/query",
                    headers=headers,
                )

                if results_response.status_code == 202:
                    return results_response.json()
                else:
                    _logger.error(
                        f"Error getting question results: {results_response.text}"
                    )
                    return None

        except Exception as e:
            _logger.error(f"Error executing question: {str(e)}")
            return None

    def get_rows_only(self, question_id, max_results=None):
        """Get only the rows data from a question/card result

        Args:
            question_id: The Metabase question/card ID
            max_results: Maximum number of results to fetch (None = use default 2000,
                        set to large number like 1000000 for all data)
        """
        results = self.get_question_results(question_id, max_results=max_results)
        if results and "data" in results and "rows" in results["data"]:
            return results["data"]["rows"]
        return []

    def get_question_id(self, question_url):
        """
        Get the question ID from the question URL
        Example URL : https://metabase.dev.colearn.id/question/1032-odoo-student-details-live-class-db
        return 1032
        """
        last_part = question_url.split("/")[-1]
        # Extract the numeric ID from the beginning of the last part
        question_id = last_part.split("-")[0]
        return question_id

    # Student Data Methods
    def get_student_details(self):
        """Get student details from Metabase (all records)"""
        self.ensure_one()
        question_id = self.get_question_id(self.student_details_question_url)
        # Use large max_results to get all data (default is only 2000)
        return self.get_rows_only(question_id, max_results=500000)

    def get_parent_details(self):
        """Get parent details from Metabase (all records)"""
        self.ensure_one()
        question_id = self.get_question_id(self.parent_details_question_url)
        # Use large max_results to get all data (default is only 2000)
        return self.get_rows_only(question_id, max_results=500000)

    def get_student_lead_stage(self):
        """Get student lead stage details from Metabase (all records)"""
        self.ensure_one()
        question_id = self.get_question_id(self.student_lead_stage_question_url)
        # Use large max_results to get all data (default is only 2000)
        return self.get_rows_only(question_id, max_results=500000)

    def get_student_phase(self):
        """Get student phase details from Metabase (all records)"""
        self.ensure_one()
        question_id = self.get_question_id(self.student_phase_question_url)
        # Use large max_results to get all data (default is only 2000)
        return self.get_rows_only(question_id, max_results=500000)

    def get_student_phase_incremental(self):
        """Get student phase details from Metabase (only updated in last 30 minutes)"""
        self.ensure_one()
        question_id = self.get_question_id(self.student_phase_incremental_question_url)
        # Incremental data should be small (< 2000 records), no need for large max_results
        return self.get_rows_only(question_id)

    def get_new_student_details(self):
        """Get new student details from Metabase"""
        self.ensure_one()
        question_id = self.get_question_id(self.new_student_details_question_url)
        return self.get_rows_only(question_id)

    def get_new_parent_details(self):
        """Get new parent details from Metabase"""
        self.ensure_one()
        question_id = self.get_question_id(self.new_parent_details_question_url)
        return self.get_rows_only(question_id)

    # Attendance Data Methods
    def get_attendance_main(self):
        """Get attendance main data from Metabase (all records)"""
        self.ensure_one()
        question_id = self.get_question_id(self.attendance_main_question_url)
        # Use large max_results to get all data (default is only 2000)
        return self.get_rows_only(question_id, max_results=500000)

    def get_attendance_details(self):
        """Get attendance details data from Metabase (all records)"""
        self.ensure_one()
        question_id = self.get_question_id(self.attendance_details_question_url)
        # Use large max_results to get all data (default is only 2000)
        return self.get_rows_only(question_id, max_results=500000)

    # Payment Received Data Methods
    def get_payment_received(self):
        """Get payment received data from Metabase (all records)"""
        self.ensure_one()
        question_id = self.get_question_id(self.payment_received_question_url)
        # Use large max_results to get all data (default is only 2000)
        return self.get_rows_only(question_id, max_results=500000)

    # Subscription Data Methods
    def get_subscription_data(self):
        """Get subscription data from Metabase (all records)"""
        self.ensure_one()
        question_id = self.get_question_id(self.subscription_data_question_url)
        # Use large max_results to get all data (default is only 2000)
        return self.get_rows_only(question_id, max_results=500000)

    def get_new_subscription_data(self):
        """Get new subscription data from Metabase"""
        self.ensure_one()
        question_id = self.get_question_id(self.new_subscription_data_question_url)
        return self.get_rows_only(question_id)

    # Payment Data Methods
    def get_slot_selection_succeeded(self):
        """Get data for successful slot selections from Metabase (all records)"""
        self.ensure_one()
        question_id = self.get_question_id(self.payment_slot_selection_question_url)
        # Use large max_results to get all data (default is only 2000)
        return self.get_rows_only(question_id, max_results=500000)

    def get_payment_received(self):
        """Get data for payments received from Metabase (all records)"""
        self.ensure_one()
        question_id = self.get_question_id(self.payment_received_question_url)
        # Use large max_results to get all data (default is only 2000)
        return self.get_rows_only(question_id, max_results=500000)

    def get_paid_access_paused(self):
        """Get data for paid access that has been paused from Metabase (all records)"""
        self.ensure_one()
        question_id = self.get_question_id(self.payment_paid_access_question_url)
        # Use large max_results to get all data (default is only 2000)
        return self.get_rows_only(question_id, max_results=500000)

    def get_new_slot_selection_succeeded(self):
        """Get data for successful new slot selections from Metabase"""
        self.ensure_one()
        question_id = self.get_question_id(self.new_payment_slot_selection_question_url)
        return self.get_rows_only(question_id)

    def get_new_payment_received(self):
        """Get data for new payments received from Metabase"""
        self.ensure_one()
        question_id = self.get_question_id(self.new_payment_received_question_url)
        return self.get_rows_only(question_id)

    def get_new_paid_access_paused(self):
        """Get data for new paid access that has been paused from Metabase"""
        self.ensure_one()
        question_id = self.get_question_id(self.new_payment_paid_access_question_url)
        return self.get_rows_only(question_id)

    def action_show_student_details(self):
        """Get student details from Metabase then show in the pop up view (wizard)"""
        self.ensure_one()
        student_details = self.get_student_details()

        # Format the student details as a string for display in the wizard
        formatted_details = (
            json.dumps(student_details, indent=2)
            if student_details
            else "No student details found"
        )

        # Create wizard
        wizard = self.env["response.metabase"].create(
            {"student_details": formatted_details}
        )

        # Return action to open wizard
        return {
            "type": "ir.actions.act_window",
            "res_model": "response.metabase",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
            "view_id": self.env.ref(
                "cl_contact_metabase.view_response_metabase_form"
            ).id,
            "flags": {"mode": "readonly"},
        }

    def run_action_sync_students(self):
        self.ensure_one()
        self.with_delay().action_sync_students()

    def action_sync_students(self):
        """Manually run the student synchronization"""
        self.ensure_one()
        result = (
            self.env["res.partner"]
            .with_context(from_manual_sync=True)
            ._sync_students_with_retry()
        )
        if result:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Success"),
                    "message": _("Student synchronization completed successfully."),
                    "sticky": False,
                    "type": "success",
                },
            }
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Error"),
                    "message": _(
                        "Student synchronization failed. Please check the logs for details."
                    ),
                    "sticky": True,
                    "type": "danger",
                },
            }

    def run_action_sync_lead_stage(self):
        self.ensure_one()
        self.with_delay().action_sync_lead_stage()

    def action_sync_lead_stage(self):
        """Manually run the lead stage synchronization"""
        self.ensure_one()
        result = (
            self.env["res.partner"]
            .with_context(from_manual_sync=True)
            ._sync_lead_stages_with_retry()
        )
        if result:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Success"),
                    "message": _("Lead stage synchronization completed successfully."),
                    "sticky": False,
                    "type": "success",
                },
            }
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Error"),
                    "message": _(
                        "Lead stage synchronization failed. Please check the logs for details."
                    ),
                    "sticky": True,
                    "type": "danger",
                },
            }

    def run_action_sync_parents(self):
        self.ensure_one()
        self.with_delay().action_sync_parents()

    def action_sync_parents(self):
        """Manually run the parent synchronization"""
        self.ensure_one()
        result = (
            self.env["res.partner"]
            .with_context(from_manual_sync=True)
            ._sync_parent_with_retry()
        )
        if result:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Success"),
                    "message": _("Parent synchronization completed successfully."),
                    "sticky": False,
                    "type": "success",
                },
            }
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Error"),
                    "message": _(
                        "Parent synchronization failed. Please check the logs for details."
                    ),
                    "sticky": True,
                    "type": "danger",
                },
            }

    def run_action_sync_student_subscriptions(self):
        self.ensure_one()
        self.with_delay().action_sync_student_subscriptions()

    def action_sync_student_subscriptions(self):
        """Manually run the student subscription synchronization"""
        self.ensure_one()
        result = (
            self.env["res.partner"]
            .with_context(from_manual_sync=True)
            ._sync_student_subscription_with_retry()
        )
        if result:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Success"),
                    "message": _(
                        "Student subscription synchronization completed successfully."
                    ),
                    "sticky": False,
                    "type": "success",
                },
            }
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Error"),
                    "message": _(
                        "Student subscription synchronization failed. Please check the logs for details."
                    ),
                    "sticky": True,
                    "type": "danger",
                },
            }

    def run_action_sync_student_phase(self):
        self.ensure_one()
        self.with_delay().action_sync_student_phase()

    def action_sync_student_phase(self):
        self.ensure_one()
        result = (
            self.env["res.partner"]
            .with_context(from_manual_sync=True)
            ._sync_student_phase_with_retry()
        )
        if result:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Success"),
                    "message": _(
                        "Student phase synchronization completed successfully."
                    ),
                    "sticky": False,
                    "type": "success",
                },
            }
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Error"),
                    "message": _(
                        "Student phase synchronization failed. Please check the logs for details."
                    ),
                    "sticky": True,
                    "type": "danger",
                },
            }

    def run_action_sync_student_attendance(self):
        self.ensure_one()
        self.with_delay().action_sync_student_attendance()

    def action_sync_student_attendance(self):
        """Manually run the student attendance synchronization"""
        self.ensure_one()
        result = (
            self.env["res.partner"]
            .with_context(from_manual_sync=True)
            ._sync_attendance_with_retry()
        )
        if result:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Success"),
                    "message": _(
                        "Student attendance synchronization completed successfully."
                    ),
                    "sticky": False,
                    "type": "success",
                },
            }
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Error"),
                    "message": _(
                        "Student attendance synchronization failed. Please check the logs for details."
                    ),
                    "sticky": True,
                    "type": "danger",
                },
            }

    def run_action_sync_payment_received(self):
        self.ensure_one()
        self.with_delay().action_sync_payment_received()

    def action_sync_payment_received(self):
        """Manually run the payment received synchronization"""
        self.ensure_one()
        result = (
            self.env["res.partner"]
            .with_context(from_manual_sync=True)
            ._sync_payment_received_with_retry()
        )
        if result:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Success"),
                    "message": _(
                        "Payment received synchronization completed successfully."
                    ),
                    "sticky": False,
                    "type": "success",
                },
            }
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Error"),
                    "message": _(
                        "Payment received synchronization failed. Please check the logs for details."
                    ),
                    "sticky": True,
                    "type": "danger",
                },
            }

    def run_action_sync_payment_slot_selection(self):
        self.ensure_one()
        self.with_delay().action_sync_payment_slot_selection()

    def action_sync_payment_slot_selection(self):
        """Manually run the payment slot selection synchronization"""
        self.ensure_one()
        result = (
            self.env["res.partner"]
            .with_context(from_manual_sync=True)
            ._sync_payment_slot_selection_with_retry()
        )
        if result:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Success"),
                    "message": _(
                        "Payment slot selection synchronization completed successfully."
                    ),
                    "sticky": False,
                    "type": "success",
                },
            }
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Error"),
                    "message": _(
                        "Payment slot selection synchronization failed. Please check the logs for details."
                    ),
                    "sticky": True,
                    "type": "danger",
                },
            }

    def run_action_sync_payment_paid_access(self):
        self.ensure_one()
        self.with_delay().action_sync_payment_paid_access()

    def action_sync_payment_paid_access(self):
        """Manually run the payment paid access synchronization"""
        self.ensure_one()
        result = (
            self.env["res.partner"]
            .with_context(from_manual_sync=True)
            ._sync_payment_paid_access_with_retry()
        )
        if result:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Success"),
                    "message": _(
                        "Payment paid access synchronization completed successfully."
                    ),
                    "sticky": False,
                    "type": "success",
                },
            }
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Error"),
                    "message": _(
                        "Payment paid access synchronization failed. Please check the logs for details."
                    ),
                    "sticky": True,
                    "type": "danger",
                },
            }

    def run_action_sync_new_records_from_metabase(self):
        config = self.env["metabase.config"].search([], limit=1)
        config.with_delay(priority=20, eta=10).action_sync_new_records()

    def action_sync_new_records_from_metabase(self):
        self.ensure_one()
        self.with_delay(priority=20, eta=10).action_sync_new_records()

    def action_sync_new_records(self):
        """Manually run the new records synchronization - runs directly without additional queuing"""
        self.ensure_one()

        sync_results = []

        # Check and sync new students
        new_student_details = self.get_new_student_details()
        if new_student_details:
            _logger.info(
                "New student details received from Metabase, syncing directly..."
            )
            new_students = self.env["res.partner"]._sync_new_students()
            sync_results.append(("Students", new_students))

        # Check and sync new parents
        new_parent_details = self.get_new_parent_details()
        if new_parent_details:
            _logger.info(
                "New parent details received from Metabase, syncing directly..."
            )
            new_parents = self.env["res.partner"]._sync_new_parents()
            sync_results.append(("Parents", new_parents))

        # Check and sync new subscriptions
        new_subscription_data = self.get_new_subscription_data()
        if new_subscription_data:
            _logger.info(
                "New subscription data received from Metabase, syncing directly..."
            )
            new_subscription = self.env["res.partner"]._sync_new_student_subscriptions()
            sync_results.append(("Subscriptions", new_subscription))

        # Check and sync new payment received
        new_payment_received = self.get_new_payment_received()
        if new_payment_received:
            _logger.info(
                "New payment received data received from Metabase, syncing directly..."
            )
            new_payment_received_data = self.env[
                "res.partner"
            ]._sync_new_payment_received()
            sync_results.append(("Payment Received", new_payment_received_data))

        # Check and sync new paid access paused
        new_paid_access_paused = self.get_new_paid_access_paused()
        if new_paid_access_paused:
            _logger.info(
                "New paid access paused data received from Metabase, syncing directly..."
            )
            new_paid_access_paused_data = self.env[
                "res.partner"
            ]._sync_new_payment_paid_access()
            sync_results.append(("Payment Paid Access", new_paid_access_paused_data))

        # Check and sync new slot selection succeeded
        new_slot_selection_succeeded = self.get_new_slot_selection_succeeded()
        if new_slot_selection_succeeded:
            _logger.info(
                "New slot selection succeeded data received from Metabase, syncing directly..."
            )
            new_slot_selection_succeeded_data = self.env[
                "res.partner"
            ]._sync_new_payment_slot_selection()
            sync_results.append(
                ("Payment Slot Selection", new_slot_selection_succeeded_data)
            )

        # Check if any sync was performed and successful
        if sync_results:
            successful_syncs = [name for name, result in sync_results if result]
            failed_syncs = [name for name, result in sync_results if not result]

            if successful_syncs and not failed_syncs:
                message = _(
                    "New records synchronization completed successfully for: %s"
                ) % ", ".join(successful_syncs)
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Success"),
                        "message": message,
                        "sticky": False,
                        "type": "success",
                    },
                }
            elif successful_syncs and failed_syncs:
                message = _("Partial success. Succeeded: %s. Failed: %s") % (
                    ", ".join(successful_syncs),
                    ", ".join(failed_syncs),
                )
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Partial Success"),
                        "message": message,
                        "sticky": True,
                        "type": "warning",
                    },
                }
            else:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Error"),
                        "message": _("All new records synchronization failed for: %s")
                        % ", ".join(failed_syncs),
                        "sticky": True,
                        "type": "danger",
                    },
                }
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Info"),
                    "message": _("No new records found in Metabase to synchronize."),
                    "sticky": False,
                    "type": "info",
                },
            }
