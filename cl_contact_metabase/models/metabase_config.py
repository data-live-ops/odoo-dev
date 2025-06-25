from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import requests
import logging
import json

_logger = logging.getLogger(__name__)

class MetabaseConfig(models.Model):
    _name = 'metabase.config'
    _description = 'Metabase Configuration'
    _rec_name = 'name'

    name = fields.Char(string='Name', required=True)
    base_url = fields.Char(string='Base URL', required=True, help='Base URL of your Metabase instance (e.g., https://metabase.example.com)')
    username = fields.Char(string='Username', required=True)
    password = fields.Char(string='Password', required=True, help='Metabase password')
    session_token = fields.Char(string='Session Token', readonly=True)
    session_expiry = fields.Datetime(string='Session Expiry', readonly=True)
    active = fields.Boolean(string='Active', default=True)
    email_notify = fields.Char(string='Notification Email', help='Email to notify when there are issues with the Metabase connection')
    
    # Question IDs for different data types
    student_details_question_id = fields.Integer(string='Student Details Question ID', default=1032)
    parent_details_question_id = fields.Integer(string='Parent Details Question ID', default=1033)
    student_lead_stage_question_id = fields.Integer(string='Student Lead Stage Question ID', default=1103)
    paid_class_joined_question_id = fields.Integer(string='Paid Class Joined Question ID', default=1028)
    paid_class_details_question_id = fields.Integer(string='Paid Class Details Question ID', default=1027)
    subscription_data_question_id = fields.Integer(string='Subscription Data Question ID', default=1026)
    slot_selection_succeeded_question_id = fields.Integer(string='Slot Selection Succeeded Question ID', default=1031)
    payment_received_question_id = fields.Integer(string='Payment Received Question ID', default=1030)
    paid_access_paused_question_id = fields.Integer(string='Paid Access Paused Question ID', default=1034)
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Configuration name must be unique!')
    ]
    
    def get_session_token(self):
        """Get a new session token from Metabase"""
        self.ensure_one()
        try:
            response = requests.post(
                f"{self.base_url.rstrip('/')}/api/session",
                json={
                    "username": self.username,
                    "password": self.password
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.write({
                    'session_token': data.get('id'),
                    'session_expiry': fields.Datetime.now() + timedelta(hours=24)
                })
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
        if not self.session_token or not self.session_expiry or fields.Datetime.now() > self.session_expiry:
            return self.get_session_token()
        return True
    
    def test_connection(self):
        """Test the connection to Metabase"""
        self.ensure_one()
        if self.get_session_token():
            # Try to get a simple question result to verify connection
            headers = {
                "X-Metabase-Session": self.session_token
            }
            try:
                response = requests.get(
                    f"{self.base_url.rstrip('/')}/api/user/current",
                    headers=headers
                )
                if response.status_code == 200:
                    raise UserError(_("Connection successful! Connected as %s") % response.json().get('common_name', 'Unknown'))
                else:
                    raise UserError(_("Connection failed! Error: %s") % response.text)
            except Exception as e:
                raise UserError(_("Connection failed! Error: %s") % str(e))
        else:
            raise UserError(_("Failed to get session token. Please check your credentials."))
    
    def notify_admin(self, subject, message):
        """Send notification email to admin"""
        self.ensure_one()
        if self.email_notify:
            try:
                template_id = self.env.ref('mail.mail_notification_light')
                template_values = {
                    'subject': subject,
                    'body_html': message,
                    'email_to': self.email_notify,
                }
                template_id.send_mail(self.id, email_values=template_values, force_send=True)
                return True
            except Exception as e:
                _logger.error(f"Failed to send notification email: {str(e)}")
        return False
    
    def get_question_results(self, question_id):
        """Get results from a specific Metabase question/card"""
        self.ensure_one()
        if not self.check_session():
            _logger.error("Failed to get valid session token")
            return None
            
        headers = {
            "X-Metabase-Session": self.session_token
        }
        
        try:
            # First get the question details
            card_response = requests.get(
                f"{self.base_url.rstrip('/')}/api/card/{question_id}",
                headers=headers
            )
            
            if card_response.status_code != 200:
                _logger.error(f"Error getting question details: {card_response.text}")
                return None
            
            # Then get the results
            results_response = requests.post(
                f"{self.base_url.rstrip('/')}/api/card/{question_id}/query",
                headers=headers
            )
            
            if results_response.status_code == 202:
                return results_response.json()
            else:
                _logger.error(f"Error getting question results: {results_response.text}")
                return None
                
        except Exception as e:
            _logger.error(f"Error executing question: {str(e)}")
            return None
    
    def get_rows_only(self, question_id):
        """Get only the rows data from a question/card result"""
        results = self.get_question_results(question_id)
        if results and 'data' in results and 'rows' in results['data']:
            return results['data']['rows']
        return []
    
    # Student Data Methods
    def get_student_details(self):
        """Get student details from Metabase"""
        self.ensure_one()
        return self.get_rows_only(self.student_details_question_id)
    
    def get_parent_details(self):
        """Get parent details from Metabase"""
        self.ensure_one()
        return self.get_rows_only(self.parent_details_question_id)
    
    def get_student_lead_stage(self):
        """Get student lead stage details from Metabase"""
        self.ensure_one()
        return self.get_rows_only(self.student_lead_stage_question_id)
    
    # Attendance Data Methods
    def get_paid_class_joined_events(self):
        """Get data for paid classes that students joined from Metabase"""
        self.ensure_one()
        return self.get_rows_only(self.paid_class_joined_question_id)
    
    def get_paid_class_details(self):
        """Get detailed information about paid classes from Metabase"""
        self.ensure_one()
        return self.get_rows_only(self.paid_class_details_question_id)
    
    # Subscription Data Methods
    def get_subscription_data(self):
        """Get subscription data from Metabase"""
        self.ensure_one()
        return self.get_rows_only(self.subscription_data_question_id)
    
    # Payment Data Methods
    def get_slot_selection_succeeded(self):
        """Get data for successful slot selections from Metabase"""
        self.ensure_one()
        return self.get_rows_only(self.slot_selection_succeeded_question_id)
    
    def get_payment_received(self):
        """Get data for payments received from Metabase"""
        self.ensure_one()
        return self.get_rows_only(self.payment_received_question_id)
    
    def get_paid_access_paused(self):
        """Get data for paid access that has been paused from Metabase"""
        self.ensure_one()
        return self.get_rows_only(self.paid_access_paused_question_id)
