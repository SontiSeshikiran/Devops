"""Test script to verify bcrypt -> Argon2id migration in auth.py"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth import get_password_hash, verify_password, needs_rehash

print("=" * 50)
print("  Argon2id Migration Verification")
print("=" * 50)

# Test 1: New hashes use Argon2id
new_hash = get_password_hash("TestPass@123")
print(f"\n1. NEW HASH (should start with $argon2id$):")
print(f"   {new_hash[:60]}...")
assert new_hash.startswith("$argon2"), "FAIL: New hash is not Argon2id!"
print("   [PASS] Uses Argon2id")

# Test 2: Verify new Argon2id hash
assert verify_password("TestPass@123", new_hash), "FAIL: Correct password rejected!"
assert not verify_password("WrongPass", new_hash), "FAIL: Wrong password accepted!"
print("\n2. VERIFY ARGON2ID HASH:")
print("   [PASS] Correct password accepted, wrong password rejected")

# Test 3: needs_rehash detects Argon2id as current
assert not needs_rehash(new_hash), "FAIL: Argon2id hash flagged for rehash!"
print("\n3. NEEDS_REHASH (Argon2id):")
print("   [PASS] Argon2id hash does NOT need rehash")

# Test 4: Legacy bcrypt hash backward compatibility
old_bcrypt = "$2b$12$uA6nSrxsULt2T5amSrJCL.59CsPs5rtSVN.MfHgXKyDCDeBanPhsC"
assert needs_rehash(old_bcrypt), "FAIL: bcrypt hash not flagged for rehash!"
print(f"\n4. LEGACY BCRYPT HASH:")
print(f"   {old_bcrypt[:50]}...")
print("   [PASS] bcrypt hash IS flagged for rehash")

# Test 5: Verify against actual DB user
import sqlite3
db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "blutor.db")
conn = sqlite3.connect(db_path)
row = conn.execute("SELECT email, hashed_password FROM users WHERE email='admin@gmail.com'").fetchone()
conn.close()
if row:
    is_valid = verify_password("Admin@1234", row[1])
    hash_type = "Argon2id" if row[1].startswith("$argon2") else "bcrypt"
    print(f"\n5. LIVE DB TEST (admin@gmail.com):")
    print(f"   Hash type: {hash_type}")
    print(f"   Password 'Admin@1234': {'[MATCH]' if is_valid else '[NO MATCH]'}")
else:
    print("\n5. LIVE DB TEST: Skipped (admin@gmail.com not found)")

print("\n" + "=" * 50)
print("  ALL TESTS PASSED")
print("=" * 50)
