import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("UNOSEND_API_KEY")
url = "https://api.unosend.co/domains"
headers = {
    "Authorization": f"Bearer {api_key}"
}

try:
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        data = res.json()
        print(f"Success: Found {len(data.get('data', []))} domains")
        for d in data.get("data", []):
            print(f"- Domain: {d.get('name')}, Status: {d.get('status')}, ID: {d.get('id')}")
    else:
        print(f"Error: {res.status_code}")
        print(res.text)
except Exception as e:
    print(f"Exception: {e}")
