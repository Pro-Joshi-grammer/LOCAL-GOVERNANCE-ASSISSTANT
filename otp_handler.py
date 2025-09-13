import os
import requests
import random
from dotenv import load_dotenv

load_dotenv()

class OTPHandler:
    def __init__(self):
        self.api_key = os.environ.get("FAST2SMS_API_KEY")
        self.api_url = "https://www.fast2sms.com/dev/bulkV2"
        self.initialized = bool(self.api_key)
        if not self.initialized:
            print("[WARN] FAST2SMS_API_KEY not found in .env. OTP service will be disabled.")

    def generate_otp(self, length=4) -> str:
        """Generates a random numeric OTP of a given length."""
        return "".join([str(random.randint(0, 9)) for _ in range(length)])

    def send_otp(self, mobile_number: str, otp_value: str) -> bool:
        """
        Sends an OTP to a given mobile number using the Fast2SMS GET API.
        Returns True on success, False on failure.
        """
        if not self.initialized:
            print("[ERROR] Cannot send OTP: Fast2SMS API key is not configured.")
            return False

        params = {
            'authorization': self.api_key,
            'variables_values': otp_value,
            'route': 'otp',
            'numbers': mobile_number
        }
        try:
            response = requests.get(self.api_url, params=params)
            response.raise_for_status()  # Raise an exception for bad status codes
            result = response.json()
            
            if result.get("return") is True:
                print(f"Successfully sent OTP {otp_value} to {mobile_number}.")
                return True
            else:
                print(f"Failed to send OTP. Reason: {result.get('message')}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while calling Fast2SMS API: {e}")
            return False
