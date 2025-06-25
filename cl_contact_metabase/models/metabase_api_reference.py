import requests
import json
from typing import Dict, Any, Optional
import os
from datetime import datetime, timedelta

class MetabaseAPI:
    def __init__(self, base_url: str, username: str, password: str):
        """
        Initialize MetabaseAPI with connection details
        
        Args:
            base_url (str): Base URL of your Metabase instance (e.g., 'http://localhost:3000')
            username (str): Metabase username
            password (str): Metabase password
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session_token = None
        self.session_time = None
        
    def connect(self) -> bool:
        """
        Establish connection with Metabase and get session token
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/session",
                json={
                    "username": self.username,
                    "password": self.password
                }
            )
            
            if response.status_code == 200:
                self.session_token = response.json()["id"]
                self.session_time = datetime.now()
                return True
            return False
            
        except Exception as e:
            print(f"Error connecting to Metabase: {str(e)}")
            return False
    
    def _check_session(self):
        """Check if session is valid, reconnect if needed"""
        if not self.session_token or not self.session_time:
            self.connect()
        elif datetime.now() - self.session_time > timedelta(hours=24):
            # Reconnect if session is older than 24 hours
            self.connect()
    
    def get_question_results(self, question_id: int) -> Optional[Dict[str, Any]]:
        """
        Get results from a specific Metabase question/card
        
        Args:
            question_id (int): ID of the Metabase question/card
            
        Returns:
            Optional[Dict[str, Any]]: Question results or None if error occurs
        """
        try:
            self._check_session()
            
            headers = {
                "X-Metabase-Session": self.session_token
            }
            
            # First get the question details
            card_response = requests.get(
                f"{self.base_url}/api/card/{question_id}",
                headers=headers
            )
            
            if card_response.status_code != 200:
                print(f"Error getting question details: {str(321)}")
                return None
            
            # Then get the results
            results_response = requests.post(
                f"{self.base_url}/api/card/{question_id}/query",
                headers=headers
            )
            print(results_response.status_code)
            if results_response.status_code == 202:
                return results_response.json()
            else:
                print(f"Error getting question results: {str(123)}")
                return None
                
        except Exception as e:
            print(f"Error executing question: {str(e)}")
            return None

    def get_rows_only(self, question_id: int) -> Optional[list]:
        """
        Get only the rows data from a question/card result
        
        Args:
            question_id (int): ID of the Metabase question/card
            
        Returns:
            Optional[list]: List of rows or None if error occurs
        """
        results = self.get_question_results(question_id)
        if results and 'data' in results and 'rows' in results['data']:
            return results['data']['rows']
        return None
    
    # ============================
    # Student Data Methods
    # ============================
    
    def get_student_details(self) -> Optional[list]:
        """
        Get student details from Metabase
        Question URL: https://metabase.dev.colearn.id/question/1032-odoo-student-details-live-class-db
        
        Returns:
            Optional[list]: List of student details or None if error occurs
        """
        return self.get_rows_only(1032)
    
    def get_parent_details(self) -> Optional[list]:
        """
        Get parent details from Metabase
        Question URL: https://metabase.dev.colearn.id/question/1033-odoo-student-details-parent
        
        Returns:
            Optional[list]: List of parent details or None if error occurs
        """
        return self.get_rows_only(1033)
    
    def get_student_lead_stage(self) -> Optional[list]:
        """
        Get student lead stage details from Metabase
        Question URL: https://metabase.dev.colearn.id/question/1103-odoo-student-details-lead-stage
        
        Returns:
            Optional[list]: List of student lead stage details or None if error occurs
        """
        return self.get_rows_only(1103)
    
    # ============================
    # Attendance Data Methods
    # ============================
    
    def get_paid_class_joined_events(self) -> Optional[list]:
        """
        Get data for paid classes that students joined from Metabase
        Question URL: https://metabase.dev.colearn.id/question/1028-odoo-attendance-paid-class-joined
        
        Returns:
            Optional[list]: List of paid class joined events or None if error occurs
        """
        return self.get_rows_only(1028)
    
    def get_paid_class_details(self) -> Optional[list]:
        """
        Get detailed information about paid classes from Metabase
        Question URL: https://metabase.dev.colearn.id/question/1027-odoo-attendance-paid-class-joined-class-details
        
        Returns:
            Optional[list]: List of paid class details or None if error occurs
        """
        return self.get_rows_only(1027)
    
    # ============================
    # Subscription Data Methods
    # ============================
    
    def get_subscription_data(self) -> Optional[list]:
        """
        Get subscription data from Metabase
        Question URL: https://metabase.dev.colearn.id/question/1026-odoo-subscription
        
        Returns:
            Optional[list]: List of subscription data or None if error occurs
        """
        return self.get_rows_only(1026)
    
    # ============================
    # Payment Data Methods
    # ============================
    
    def get_slot_selection_succeeded(self) -> Optional[list]:
        """
        Get data for successful slot selections from Metabase
        Question URL: https://metabase.dev.colearn.id/question/1031-odoo-payment-slot-selection-succeeded
        
        Returns:
            Optional[list]: List of slot selection succeeded events or None if error occurs
        """
        return self.get_rows_only(1031)
    
    def get_payment_received(self) -> Optional[list]:
        """
        Get data for payments received from Metabase
        Question URL: https://metabase.dev.colearn.id/question/1030-odoo-payment-payment-recieved
        
        Returns:
            Optional[list]: List of payment received events or None if error occurs
        """
        return self.get_rows_only(1030)
    
    def get_paid_access_paused(self) -> Optional[list]:
        """
        Get data for paid access that has been paused from Metabase
        Question URL: https://metabase.dev.colearn.id/question/1034-odoo-payment-paid-access-paused
        
        Returns:
            Optional[list]: List of paid access paused events or None if error occurs
        """
        return self.get_rows_only(1034)

# Example usage
if __name__ == "__main__":
    # Replace these with your actual Metabase details
    METABASE_URL = "https://metabase.dev.colearn.id"
    METABASE_USERNAME = "portcities@colearn.id"
    METABASE_PASSWORD = "-U2CaemCOsKfmG"
    
    # Initialize the API
    mb = MetabaseAPI(METABASE_URL, METABASE_USERNAME, METABASE_PASSWORD)
    
    # Connect to Metabase
    if mb.connect():
        print("Successfully connected to Metabase!")

        # Example 1: Get student details
        print("\n1. Student Details:")
        students = mb.get_student_details()
        if students:
            for student in students[:3]:  # show first 3 students only
                print(student)
        
        # Example 2: Get parent details
        print("\n2. Parent Details:")
        parents = mb.get_parent_details()
        if parents:
            for parent in parents[:3]:  # show first 3 parents only
                print(parent)
                
        # Example 3: Get attendance data
        print("\n3. Paid Class Joined Events:")
        attendance = mb.get_paid_class_joined_events()
        if attendance:
            for event in attendance[:3]:  # show first 3 events only
                print(event)
                
        # Example 4: Get subscription data
        print("\n4. Subscription Data:")
        subscriptions = mb.get_subscription_data()
        if subscriptions:
            for subscription in subscriptions[:3]:  # show first 3 subscriptions only
                print(subscription)
                
        # Example 5: Get payment data
        print("\n5. Payment Data (Slot Selection Succeeded):")
        payments = mb.get_slot_selection_succeeded()
        if payments:
            for payment in payments[:3]:  # show first 3 payments only
                print(payment)
                
    else:
        print("Failed to connect to Metabase")
