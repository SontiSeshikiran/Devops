import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("UNOSEND_API_KEY")
url = "https://api.unosend.co/emails"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

from_addresses = [
    "identity@seshi.site",
    "identity@send.seshi.site",
    "noreply@send.seshi.site",
    "shaik@send.seshi.site"
]

for from_addr in from_addresses:
    print(f"Testing From: {from_addr}")
    data = {
        "from": from_addr,
        "to": ["seshi934652@gmail.com"],
        "subject": f"Verification Test: {from_addr}",
        "text": f"This is a test from {from_addr}. If you get this, this address is working."
    }
    try:
        res = requests.post(url, json=data, headers=headers, timeout=10)
        print(f"Status: {res.status_code}")
        print(f"Response: {res.text}")
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 20)
