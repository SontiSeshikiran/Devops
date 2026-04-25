import os, json, fnmatch, uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import Depends, HTTPException, status, Request
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from database import get_db
from models import User, Group, Policy, IdentityPolicy, UserGroup, TokenBlacklist

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-key-for-dev-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

import hashlib

def get_fingerprint(request: Request) -> str:
    """Generate a stable fingerprint based on User-Agent and IP."""
    ua = request.headers.get("user-agent", "unknown")
    # We use User-Agent only for better stability across dynamic IPs (like mobile)
    # but could include IP if preferred.
    return hashlib.sha256(ua.encode()).hexdigest()

import bcrypt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_ph = PasswordHasher()

def verify_password(plain_password, hashed_password):
    """Verify password against Argon2id or legacy bcrypt hash."""
    if hashed_password.startswith('$argon2'):
        # Argon2id hash
        try:
            return _ph.verify(hashed_password, plain_password)
        except VerifyMismatchError:
            return False
    else:
        # Legacy bcrypt hash fallback
        if not isinstance(plain_password, bytes):
            plain_password = plain_password.encode('utf-8')
        if not isinstance(hashed_password, bytes):
            hashed_password = hashed_password.encode('utf-8')
        return bcrypt.checkpw(plain_password, hashed_password)

def get_password_hash(password):
    """Hash password using Argon2id."""
    return _ph.hash(password)

def needs_rehash(hashed_password):
    """Check if a hash is legacy bcrypt and needs upgrade to Argon2id."""
    return not hashed_password.startswith('$argon2')

def create_access_token(data: dict, request: Request, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    now_utc = datetime.now(timezone.utc)
    if expires_delta:
        expire = now_utc + expires_delta
    else:
        expire = now_utc + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    fingerprint = get_fingerprint(request)
    to_encode.update({"exp": expire, "iat": now_utc, "type": "access", "fpt": fingerprint})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, request: Request):
    to_encode = data.copy()
    now_utc = datetime.now(timezone.utc)
    expire = now_utc + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())
    
    fingerprint = get_fingerprint(request)
    to_encode.update({"exp": expire, "iat": now_utc, "type": "refresh", "jti": jti, "fpt": fingerprint})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_reset_token(email: str):
    now_utc = datetime.now(timezone.utc)
    expire = now_utc + timedelta(hours=24)
    to_encode = {"sub": email, "type": "reset", "exp": expire, "iat": now_utc}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_reset_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "reset":
            return None
        return payload.get("sub")
    except JWTError:
        return None

import pyotp
import qrcode
import io
import base64

def generate_totp_secret():
    return pyotp.random_base32()

def get_totp_uri(secret: str, email: str):
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name="BluTOR")

def verify_totp(secret: str, code: str):
    totp = pyotp.TOTP(secret)
    return totp.verify(code)

def generate_qr_code(uri: str):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated."
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        token_type: str = payload.get("type")
        token_fpt: str = payload.get("fpt")
        
        # Verify Fingerprint to prevent token reuse on different devices
        current_fpt = get_fingerprint(request)
        if token_fpt != current_fpt:
            print(f"[SECURITY] Fingerprint mismatch: {token_fpt} vs {current_fpt}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session binding error.")

        if user_id is None or token_type != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")
    except JWTError as e:
        print("JWT Decode Error:", repr(e))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature.")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    
    if not user.is_approved:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account pending admin approval.")
        
    return user

class PolicyEngine:
    @staticmethod
    def evaluate(user: User, db: Session, action: str, resource: str):
        # 1. Collect all policies (Direct + Group)
        policies = []
        
        # Direct policies
        direct_policies = (
            db.query(Policy)
            .join(IdentityPolicy, IdentityPolicy.policy_id == Policy.id)
            .filter(IdentityPolicy.user_id == user.id)
            .all()
        )
        policies.extend([p.policy_document for p in direct_policies])
        
        # Group policies
        group_policies = (
            db.query(Policy)
            .join(IdentityPolicy, IdentityPolicy.policy_id == Policy.id)
            .join(Group, IdentityPolicy.group_id == Group.id)
            .join(UserGroup, UserGroup.group_id == Group.id)
            .filter(UserGroup.user_id == user.id)
            .all()
        )
        policies.extend([p.policy_document for p in group_policies])
        
        # 2. Flatten Statements
        statements = []
        for doc in policies:
            if "Statement" in doc:
                statements.extend(doc["Statement"])
        
        # 3. Decision Logic: Explicit Deny wins
        for stmt in statements:
            if stmt.get("Effect") == "Deny":
                if PolicyEngine._match(stmt, action, resource):
                    return False
        
        # 4. Decision Logic: Explicit Allow
        for stmt in statements:
            if stmt.get("Effect") == "Allow":
                if PolicyEngine._match(stmt, action, resource):
                    return True
        
        # 5. Implicit Deny
        return False

    @staticmethod
    def _match(statement: dict, action: str, resource: str):
        actions = statement.get("Action", [])
        if isinstance(actions, str): actions = [actions]
        
        resources = statement.get("Resource", [])
        if isinstance(resources, str): resources = [resources]
        
        action_match = any(fnmatch.fnmatch(action, a) for a in actions)
        resource_match = any(fnmatch.fnmatch(resource, r) for r in resources)
        
        return action_match and resource_match

def require_permission(action: str, resource: str):
    def dependency(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        if not PolicyEngine.evaluate(user, db, action, resource):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access Denied: Missing permission '{action}' for '{resource}'"
            )
        return True
    return dependency
