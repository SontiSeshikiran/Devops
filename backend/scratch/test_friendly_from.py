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

# Testing "Friendly From" to see if it improves delivery
data = {
    "from": "BluTOR Identity <identity@seshi.site>",
    "to": ["seshi934652@gmail.com", "shaikafsarpasha3@gmail.com"],
    "subject": "System Delivery Test (Friendly From)",
    "text": "This is a plain text test with a friendly 'From' name. Please check all folders including Spam."
}

print("Dispatching Friendly From test...")
res = requests.post(url, json=data, headers=headers)
print(f"Status Code: {res.status_code}")
print(f"Response: {res.text}")
