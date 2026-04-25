import os
import requests
import datetime
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("UNOSEND_API_KEY")
from_email = os.getenv("UNOSEND_FROM_EMAIL", "identity@seshi.site")
target_email = "seshi934652@gmail.com"

url = "https://api.unosend.co/emails"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

data = {
    "from": from_email,
    "to": [target_email],
    "subject": f"CRITICAL: Final Identity Verification Test [{timestamp}]",
    "text": f"This is a unique test message sent at {timestamp} to ensure delivery is still active. If you receive this, the system is fully functional."
}

print(f"Dispatching unique verification email to {target_email}...")
res = requests.post(url, json=data, headers=headers)
print(f"Status: {res.status_code}")
print(f"Response: {res.text}")
