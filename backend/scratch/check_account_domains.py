import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("UNOSEND_API_KEY")
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

# Attempt to list domains to see what is ACTUALLY verified in the account
domains_url = "https://api.unosend.co/domains"

print("Checking Uno Send account domains...")
try:
    res = requests.get(domains_url, headers=headers, timeout=10)
    print(f"Status: {res.status_code}")
    print(f"Response: {res.text}")
except Exception as e:
    print(f"Error: {e}")
