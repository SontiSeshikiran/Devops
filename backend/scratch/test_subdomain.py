import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("UNOSEND_API_KEY")
from_email = "identity@send.seshi.site" # Testing the subdomain mentioned in conversation history
target_email = "seshi934652@gmail.com"

url = "https://api.unosend.co/emails"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

data = {
    "from": from_email,
    "to": [target_email],
    "subject": "Subdomain Proof-of-Concept",
    "text": f"This email is sent from the subdomain: {from_email}. If you receive this, the subdomain is properly verified."
}

print(f"Dispatching POC email from {from_email} to {target_email}...")
res = requests.post(url, json=data, headers=headers)
print(f"Status Code: {res.status_code}")
print(f"Response: {res.text}")
