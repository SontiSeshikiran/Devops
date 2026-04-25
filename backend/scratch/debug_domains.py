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

domains_to_test = [
    "identity@seshi.site",
    "identity@send.seshi.site"
]

for domain in domains_to_test:
    print(f"Testing domain: {domain}")
    data = {
        "from": domain,
        "to": ["seshi934652@gmail.com"],
        "subject": "Domain Test",
        "text": f"Testing if {domain} is verified."
    }
    res = requests.post(url, json=data, headers=headers)
    print(f"Status Code: {res.status_code}")
    print(f"Response: {res.text}")
    print("-" * 20)
