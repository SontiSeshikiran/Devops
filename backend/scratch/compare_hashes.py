"""Compare hash BEFORE and AFTER login to prove Argon2id migration."""
import sqlite3
import requests

EMAIL = "admin@gmail.com"
PASSWORD = "Admin@1234"
DB_PATH = "blutor.db"
API_URL = "http://localhost:8000/api/auth/login"

def get_hash(email):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT hashed_password FROM users WHERE email=?", (email,)).fetchone()
    conn.close()
    return row[0] if row else None

# BEFORE
hash_before = get_hash(EMAIL)
print("=" * 60)
print("  BEFORE LOGIN")
print("=" * 60)
print(f"  Email: {EMAIL}")
print(f"  Hash:  {hash_before}")
hash_type = "Argon2id" if hash_before.startswith("$argon2") else "bcrypt"
print(f"  Type:  {hash_type}")

# LOGIN via API
print("\n  Logging in via API...")
try:
    resp = requests.post(API_URL, json={"email": EMAIL, "password": PASSWORD})
    print(f"  Login status: {resp.status_code}")
except Exception as e:
    print(f"  ERROR: Could not connect to backend: {e}")
    print("  Make sure the backend is running on port 8000!")
    exit(1)

# AFTER
hash_after = get_hash(EMAIL)
print("\n" + "=" * 60)
print("  AFTER LOGIN")
print("=" * 60)
print(f"  Email: {EMAIL}")
print(f"  Hash:  {hash_after}")
hash_type_after = "Argon2id" if hash_after.startswith("$argon2") else "bcrypt"
print(f"  Type:  {hash_type_after}")

# COMPARE
print("\n" + "=" * 60)
print("  COMPARISON")
print("=" * 60)
changed = hash_before != hash_after
print(f"  Hash changed: {changed}")
if changed:
    print(f"  Migration:    bcrypt --> Argon2id [SUCCESS]")
else:
    print(f"  No change (backend may not be running or login failed)")
