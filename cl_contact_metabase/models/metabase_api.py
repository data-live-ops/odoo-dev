import requests
import json
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class MetabaseAPI:
    """
    Utility class for Metabase API interactions.
    This is used internally by the metabase.config model.
    """
    
    def __init__(self, base_url, username, password):
        """
        Initialize MetabaseAPI with connection details
        
        Args:
            base_url: Base URL of your Metabase instance (e.g., 'http://localhost:3000')
            username: Metabase username
            password: Metabase password
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session_token = None
        self.session_time = None
    
    def connect(self):
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
            
            _logger.error(f"Failed to connect to Metabase: {response.text}")
            return False
            
        except Exception as e:
            _logger.error(f"Error connecting to Metabase: {str(e)}")
            return False
    
    def check_session(self):
        """Check if session is valid, reconnect if needed"""
        if not self.session_token or not self.session_time:
            return self.connect()
        elif datetime.now() - self.session_time > timedelta(hours=24):
            # Reconnect if session is older than 24 hours
            return self.connect()
        return True
    
    def get_question_results(self, question_id):
        """
        Get results from a specific Metabase question/card
        
        Args:
            question_id: ID of the Metabase question/card
            
        Returns:
            dict: Question results or None if error occurs
        """
        try:
            if not self.check_session():
                return None
            
            headers = {
                "X-Metabase-Session": self.session_token
            }
            
            # First get the question details
            card_response = requests.get(
                f"{self.base_url}/api/card/{question_id}",
                headers=headers
            )
            
            if card_response.status_code != 200:
                _logger.error(f"Error getting question details: {card_response.text}")
                return None
            
            # Then get the results
            results_response = requests.post(
                f"{self.base_url}/api/card/{question_id}/query",
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
        """
        Get only the rows data from a question/card result
        
        Args:
            question_id: ID of the Metabase question/card
            
        Returns:
            list: List of rows or empty list if error occurs
        """
        results = self.get_question_results(question_id)
        if results and 'data' in results and 'rows' in results['data']:
            return results['data']['rows']
        return []
