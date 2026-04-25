from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from database import engine, Base, get_db
from models import User, Group, Policy, UserGroup, IdentityPolicy, TokenBlacklist, AuditLog
from auth import get_current_user, require_permission, get_password_hash, verify_password, create_access_token, create_refresh_token, needs_rehash
import models
from pydantic import BaseModel
import os
import re
from datetime import datetime, timedelta, timezone
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware

# Create tables matching the new schema
Base.metadata.create_all(bind=engine)

import dns.resolver

def validate_email_domain(email: str) -> bool:
    """Check if the email domain has at least one MX record. Returns True even if it fails to be non-blocking."""
    try:
        domain = email.split('@')[-1]
        # Attempt to resolve MX records for the domain
        dns.resolver.resolve(domain, 'MX')
        return True
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, Exception) as e:
        print(f"[WARN] DNS MX lookup failed for {domain} (Account creation will proceed): {e}")
        return True

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="BluTOR API v3.0 (GCP Optimized)", debug=True)

# --- CORS CONFIGURATION ---
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|.*\.ngrok-free\.app|.*\.ngrok\.io)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- OAUTH & SESSION CONFIG ---
# SessionMiddleware is required by Authlib to track OAuth state
app.add_middleware(SessionMiddleware, secret_key=os.getenv("JWT_SECRET_KEY", "oauth-session-secret"))

oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url=os.getenv("GOOGLE_CONF_URL"),
    client_kwargs={
        'scope': 'openid email profile',
    }
)

@app.on_event("startup")
def startup_event():
    print("\n" + "="*50)
    print(">>> BLUTOR IAM BACKEND STARTING")
    print(f"[*] Database: {os.getenv('DATABASE_URL', 'sqlite:///./blutor.db')}")
    print("="*50)
    
    auto_seed = os.getenv("AUTO_SEED_IAM", "true").strip().lower() in ("1", "true", "yes", "y", "on")
    if not auto_seed:
        print("[INFO] Auto-seeding is disabled.")
        return

    print("[DB] Checking database state for seeding...")
    try:
        from seed_blueprint import seed
        seed()
    except Exception as e:
        print(f"[WARN] AUTO_SEED_IAM failed: {e}")
    
    print("[OK] Startup initialization complete.\n")

def _env_flag(name: str, default: bool) -> bool:
    val = os.getenv(name, str(default)).strip().lower()
    return val in ("1", "true", "yes", "y", "on")

class UserProfile(BaseModel):
    email: str
    display_name: Optional[str] = None
    is_approved: bool
    force_password_change: bool
    groups: List[str] = []

@app.get("/api/me", response_model=UserProfile)
def read_user_me(current_user: models.User = Depends(get_current_user)):
    """Return the authenticated user's profile metadata."""
    return {
        "email": current_user.email,
        "display_name": current_user.display_name,
        "is_approved": current_user.is_approved,
        "force_password_change": current_user.force_password_change,
        "groups": [g.name for g in current_user.groups]
    }

@app.get("/api/permissions")
def get_permissions(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return the list of allowed actions for the frontend to adjust the UI."""
    from auth import PolicyEngine
    all_actions = ["drishti:read", "garuda:read", "nigha:read", "flo:read", "admin:users:read", "admin:users:write", "admin:users:delete"]
    allowed = []
    for action in all_actions:
        # Check resource generically
        resource = f"module:{action.split(':')[0]}"
        if action.startswith("admin:"): resource = "module:user-management"
        if PolicyEngine.evaluate(current_user, db, action, resource):
            allowed.append(action)
    return {"allowed_actions": allowed}

class SignupRequest(BaseModel):
    email: str
    password: str

@app.post("/api/auth/signup", status_code=status.HTTP_201_CREATED)
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    normalized_email = req.email.strip().lower()
    
    # 1. DNS MX Validation
    if _env_flag("IAM_VALIDATE_MX", True):
        if not validate_email_domain(normalized_email):
            raise HTTPException(status_code=400, detail="Invalid email domain. Please use a valid email address.")

    existing_user = db.query(models.User).filter(models.User.email == normalized_email).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Registration could not be completed.")

    new_user = models.User(
        email=normalized_email,
        hashed_password=get_password_hash(req.password),
        display_name=normalized_email.split('@')[0],
        is_approved=_env_flag("IAM_AUTO_APPROVE_SIGNUPS", False)
    )
    db.add(new_user)
    db.commit()
    
    # Assign to FreeTier group by default
    free_tier = db.query(models.Group).filter(models.Group.name == "FreeTier").first()
    if free_tier:
        db.add(models.UserGroup(user_id=new_user.id, group_id=free_tier.id))
        db.commit()
    
    return {"message": "Registration successful. Pending admin review."}

# --- GOOGLE OAUTH ENDPOINTS ---

@app.get("/api/auth/google")
async def google_login(request: Request):
    """Redirect to Google's OAuth login page."""
    redirect_uri = request.url_for('google_callback')
    # Support both localhost and potentially proxies
    if "localhost" not in str(redirect_uri) and request.headers.get("x-forwarded-proto") == "https":
        redirect_uri = str(redirect_uri).replace("http://", "https://")
    return await oauth.google.authorize_redirect(request, str(redirect_uri))

@app.get("/api/auth/google/callback")
async def google_callback(request: Request, response: Response, db: Session = Depends(get_db)):
    """Handle the callback from Google and sign in/up the user."""
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        print(f"[ERROR] OAuth Token Error: {e}")
        raise HTTPException(status_code=400, detail="OAuth authentication failed.")

    user_info = token.get('userinfo')
    if not user_info:
        raise HTTPException(status_code=400, detail="Could not retrieve user info from Google.")

    email = user_info.get('email').lower()
    google_id = user_info.get('sub')
    display_name = user_info.get('name')

    # 1. Search for existing user by Email (Account Linking) or SSO ID
    user = db.query(models.User).filter(
        (models.User.email == email) | (models.User.sso_id == google_id)
    ).first()

    if user:
        # Link Google ID if not already linked
        if not user.sso_id:
            user.sso_id = google_id
            user.sso_provider = "google"
            db.commit()
    else:
        # 2. Create New User (Auto-approved for Google SSO)
        user = models.User(
            email=email,
            display_name=display_name or email.split('@')[0],
            sso_id=google_id,
            sso_provider="google",
            is_approved=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Assign to FreeTier
        free_tier = db.query(models.Group).filter(models.Group.name == "FreeTier").first()
        if free_tier:
            db.add(models.UserGroup(user_id=user.id, group_id=free_tier.id))
            db.commit()

    if not user.is_approved:
        # For now, redirect to a landing page or return an error if it's a direct API call
        # In a real app, you'd redirect to /login?error=pending
        raise HTTPException(status_code=403, detail="OAuth login successful, but account is pending admin approval.")

    # 3. Successful Login - Issue Tokens
    access_token = create_access_token({"sub": str(user.id)}, request)
    refresh_token = create_refresh_token({"sub": str(user.id)}, request)

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5174")
    cookie_domain = os.getenv("AUTH_COOKIE_DOMAIN", None)
    
    # We set cookies and then redirect to the frontend
    from starlette.responses import RedirectResponse
    redirect_resp = RedirectResponse(url=f"{frontend_url}/dashboard")
    
    redirect_resp.set_cookie(
        key="access_token", 
        value=access_token, 
        httponly=True, 
        samesite="lax", 
        secure=False, # Set to True in production
        domain=cookie_domain
    )
    redirect_resp.set_cookie(
        key="refresh_token", 
        value=refresh_token, 
        httponly=True, 
        samesite="lax", 
        secure=False, # Set to True in production
        domain=cookie_domain
    )
    
    return redirect_resp

class LoginRequest(BaseModel):
    email: str
    password: str

class Login2FARequest(BaseModel):
    mfa_token: str
    code: str

class Verify2FARequest(BaseModel):
    code: str

class ForgotPasswordRequest(BaseModel):
    email: str

@app.post("/api/auth/login")
def login(login_data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    normalized_email = login_data.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == normalized_email).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    # Lazy migration: upgrade legacy bcrypt hashes to Argon2id on successful login
    if needs_rehash(user.hashed_password):
        user.hashed_password = get_password_hash(login_data.password)
        db.commit()
        
    if not user.is_approved:
        raise HTTPException(status_code=403, detail="Account pending admin approval.")

    # If 2FA is enabled, return an mfa_token instead of session cookies
    if user.is_2fa_enabled:
        # Short-lived MFA token (5 minutes)
        mfa_token = create_access_token({"sub": str(user.id), "type": "mfa"}, request, expires_delta=timedelta(minutes=5))
        return {
            "mfa_required": True,
            "mfa_token": mfa_token
        }

    access_token = create_access_token({"sub": str(user.id)}, request)
    refresh_token = create_refresh_token({"sub": str(user.id)}, request)

    cookie_domain = os.getenv("AUTH_COOKIE_DOMAIN", None)
    
    response.set_cookie(
        key="access_token", 
        value=access_token, 
        httponly=True, 
        samesite="lax", 
        max_age=15*60,
        domain=cookie_domain
    )
    response.set_cookie(
        key="refresh_token", 
        value=refresh_token, 
        httponly=True, 
        samesite="lax", 
        path="/api/auth/refresh", 
        max_age=7*24*60*60,
        domain=cookie_domain
    )
    
    return {
        "mfa_required": False,
        "requires_password_change": user.force_password_change,
        "user": {
            "email": user.email,
            "display_name": user.display_name,
            "groups": [g.name for g in user.groups]
        }
    }

@app.post("/api/auth/login/2fa")
def login_2fa(req: Login2FARequest, response: Response, db: Session = Depends(get_db)):
    from auth import SECRET_KEY, ALGORITHM, verify_totp
    from jose import jwt, JWTError
    
    try:
        payload = jwt.decode(req.mfa_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "mfa":
            raise HTTPException(status_code=401, detail="Invalid MFA token.")
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="MFA token expired or invalid.")
        
    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if not user or not user.is_2fa_enabled:
        raise HTTPException(status_code=401, detail="User not found or 2FA not enabled.")
        
    if not verify_totp(user.totp_secret, req.code):
        raise HTTPException(status_code=401, detail="Invalid 2FA code.")
        
    # Issue final cookies
    access_token = create_access_token({"sub": str(user.id)}, request)
    refresh_token = create_refresh_token({"sub": str(user.id)}, request)
    cookie_domain = os.getenv("AUTH_COOKIE_DOMAIN", None)
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, samesite="lax", max_age=15*60, domain=cookie_domain)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, samesite="lax", path="/api/auth/refresh", max_age=7*24*60*60, domain=cookie_domain)
    
    return {
        "user": {
            "email": user.email,
            "display_name": user.display_name,
            "groups": [g.name for g in user.groups]
        }
    }

@app.post("/api/auth/logout")
def logout(response: Response, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    refresh_token_cookie = request.cookies.get("refresh_token")
    if refresh_token_cookie:
        from jose import jwt, JWTError
        SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-key-for-dev-change-in-prod")
        try:
            payload = jwt.decode(refresh_token_cookie, SECRET_KEY, algorithms=["HS256"])
            jti = payload.get("jti")
            expires = datetime.fromtimestamp(payload.get("exp"))
            if jti:
                db.add(models.TokenBlacklist(jti=jti, user_id=current_user.id, expires_at=expires))
                db.commit()
        except JWTError:
            pass

    cookie_domain = os.getenv("AUTH_COOKIE_DOMAIN", None)
    response.delete_cookie(key="access_token", domain=cookie_domain)
    response.delete_cookie(key="refresh_token", path="/api/auth/refresh", domain=cookie_domain)
    return {"message": "Logout successful"}

@app.post("/api/auth/refresh")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token_cookie = request.cookies.get("refresh_token")
    if not refresh_token_cookie:
        raise HTTPException(status_code=401, detail="Refresh token missing.")
    
    from jose import jwt, JWTError
    import os
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-key-for-dev-change-in-prod")
    try:
        payload = jwt.decode(refresh_token_cookie, SECRET_KEY, algorithms=["HS256"])
        jti = payload.get("jti")
        user_id = payload.get("sub")
        iat = payload.get("iat")
        
        blacklisted = db.query(models.TokenBlacklist).filter(models.TokenBlacklist.jti == jti).first()
        if blacklisted:
            raise HTTPException(status_code=401, detail="Refresh token blacklisted.")
            
        user = db.query(models.User).filter(models.User.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=401, detail="User related to token not found.")

        # Stateless Invalidation Check:
        # Reject if token issued before the user's last password change
        if user.password_changed_at:
            db_iat = int(user.password_changed_at.replace(tzinfo=timezone.utc).timestamp())
            if iat < db_iat:
                raise HTTPException(status_code=401, detail="Session expired due to password change.")

        # --- REFRESH TOKEN ROTATION ---
        # 1. Blacklist the old refresh token immediately
        db.add(models.TokenBlacklist(jti=jti, user_id=int(user_id), expires_at=datetime.fromtimestamp(payload.get("exp"))))
        db.commit()

        # 2. Issue NEW access AND refresh tokens
        access_token = create_access_token({"sub": str(user_id)}, request)
        new_refresh_token = create_refresh_token({"sub": str(user_id)}, request)

        cookie_domain = os.getenv("AUTH_COOKIE_DOMAIN", None)
        response.set_cookie(key="access_token", value=access_token, httponly=True, samesite="lax", max_age=15*60, domain=cookie_domain)
        response.set_cookie(key="refresh_token", value=new_refresh_token, httponly=True, samesite="lax", path="/api/auth/refresh", max_age=7*24*60*60, domain=cookie_domain)

        return {"message": "Token refreshed and rotated."}
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token.")

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@app.post("/api/auth/change-password")
def change_password(req: ChangePasswordRequest, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # 1. Verify Current Password
    if not verify_password(req.current_password, current_user.hashed_password):
        raise HTTPException(status_code=403, detail="Invalid current password.")
    
    # 2. Validate New Password Complexity
    # Min 8 chars, at least one uppercase, one lowercase, one digit, one special character.
    password_regex = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
    if not re.match(password_regex, req.new_password):
        raise HTTPException(
            status_code=400, 
            detail="Password must be at least 8 characters long and contain uppercase, lowercase, numbers, and special characters."
        )

    # 3. Update Password and Reset Flag
    current_user.hashed_password = get_password_hash(req.new_password)
    current_user.force_password_change = False
    current_user.password_changed_at = datetime.now(timezone.utc).replace(tzinfo=None) # Store as naive UTC for SQLite
    
    # 4. Audit Log
    client_host = request.client.host if request.client else "unknown"
    db.add(models.AuditLog(
        actor_email=current_user.email,
        actor_ip=client_host,
        action="PASSWORD_CHANGED",
        resource_type="User",
        resource_id=str(current_user.id),
        status="SUCCESS",
        details={"method": "force_reset"}
    ))
    
    db.commit()
    return {"message": "Password updated successfully. All other sessions invalidated."}

@app.post("/api/auth/2fa/setup")
def setup_2fa(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    from auth import generate_totp_secret, get_totp_uri, generate_qr_code
    
    # Generate temporary secret (not saved until verified)
    secret = generate_totp_secret()
    uri = get_totp_uri(secret, current_user.email)
    qr_code = generate_qr_code(uri)
    
    # Store secret in a temporary state (in this demo, we'll store it in the user record
    # but with is_2fa_enabled=False until verified)
    current_user.totp_secret = secret
    db.commit()
    
    return {
        "secret": secret,
        "qr_code": f"data:image/png;base64,{qr_code}"
    }

@app.post("/api/auth/2fa/verify")
def verify_2fa_setup(req: Verify2FARequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    from auth import verify_totp
    
    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA setup not initiated.")
        
    if verify_totp(current_user.totp_secret, req.code):
        current_user.is_2fa_enabled = True
        db.commit()
        return {"message": "2FA successfully enabled."}
    else:
        raise HTTPException(status_code=400, detail="Invalid verification code.")

@app.post("/api/auth/2fa/disable")
def disable_2fa(req: Verify2FARequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    from auth import verify_totp
    
    if not current_user.is_2fa_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled.")
        
    if verify_totp(current_user.totp_secret, req.code):
        current_user.is_2fa_enabled = False
        current_user.totp_secret = None
        db.commit()
        return {"message": "2FA disabled."}
    else:
        raise HTTPException(status_code=400, detail="Invalid verification code.")


# Protected Application Modules
@app.get("/api/drishti", dependencies=[Depends(require_permission("drishti:read", "module:drishti"))])
def get_drishti_data():
    return {"module": "Drishti", "data": "Deep Forensic Traffic Correlation Results."}

@app.get("/api/garuda", dependencies=[Depends(require_permission("garuda:read", "module:garuda"))])
def get_garuda_data():
    return {"module": "Garuda", "data": "Falcon Crawler feed active - Monitoring 142 targets."}

@app.get("/api/nigha", dependencies=[Depends(require_permission("nigha:read", "module:nigha"))])
def get_nigha_data():
    return {"module": "Nigha", "data": "Breach Exposure Intelligence synced."}

@app.get("/api/flo", dependencies=[Depends(require_permission("flo:read", "module:flo"))])
def get_flo_data():
    return {"module": "Flo", "data": "Global Sentinel network telemetry streaming live."}

# Administrative Controls
@app.get("/api/admin/users", dependencies=[Depends(require_permission("admin:users:read", "module:user-management"))])
def list_users(db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    user_list = []
    for u in users:
        user_list.append({
            "id": u.id,
            "email": u.email,
            "display_name": u.display_name,
            "is_approved": u.is_approved,
            "force_password_change": u.force_password_change,
            "groups": [g.name for g in u.groups],
            "created_at": u.created_at
        })
    return {"users": user_list}

class ProvisionUserRequest(BaseModel):
    email: str
    password: str
    group_name: str

@app.post("/api/admin/users/provision", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("admin:users:write", "module:user-management"))])
def provision_user(req: ProvisionUserRequest, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    normalized_email = req.email.strip().lower()
    
    # 1. DNS MX Validation
    if not validate_email_domain(normalized_email):
        raise HTTPException(status_code=422, detail="Invalid email domain. Provisioning aborted.")

    existing = db.query(models.User).filter(models.User.email == normalized_email).first()
    if existing:
        print(f"Provisioning conflict: {normalized_email} already exists (ID: {existing.id})")
        raise HTTPException(status_code=409, detail=f"Identity '{normalized_email}' is already registered in the system.")
        
    group = db.query(models.Group).filter(models.Group.name == req.group_name).first()
    if not group:
        raise HTTPException(status_code=422, detail="Group not found.")
    
    new_user = models.User(
        email=normalized_email,
        hashed_password=get_password_hash(req.password),
        display_name=normalized_email.split('@')[0],
        is_approved=True,
        force_password_change=True
    )
    db.add(new_user)
    db.commit()
    
    db.add(models.UserGroup(user_id=new_user.id, group_id=group.id))
    
    # Audit Log
    client_host = request.client.host if request.client else "unknown"
    db.add(models.AuditLog(
        actor_email=current_user.email,
        actor_ip=client_host,
        action="USER_PROVISIONED",
        resource_type="User",
        resource_id=str(new_user.id),
        status="SUCCESS",
        details={"email": normalized_email, "group": req.group_name}
    ))
    
    db.commit()
    
    from auth import create_reset_token
    import email_service
    import os
    
    # We pass None or dummy for request here as reset tokens aren't device-bound 
    # to allow opening the link from a different device (like mobile email -> desktop).
    reset_token = create_reset_token(normalized_email)
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5174")
    reset_link = f"{frontend_url}/?token={reset_token}&email={normalized_email}"
    
    email_sent = False
    try:
        email_sent = email_service.send_welcome_email(to_email=normalized_email, reset_link=reset_link, password=req.password)
    except Exception as e:
        print(f"[ERROR] Email delivery failed for {normalized_email}: {e}")

    msg = "User provisioned successfully."
    if email_sent:
        msg += " Welcome email sent."
    else:
        msg += " (Warning: Welcome email could not be delivered, please share credentials manually)."

    return {"user_id": new_user.id, "message": msg, "email_sent": email_sent}

class ResetPasswordWithTokenRequest(BaseModel):
    token: str
    new_password: str

@app.post("/api/auth/reset-password-with-token")
def reset_password_with_token(req: ResetPasswordWithTokenRequest, request: Request, db: Session = Depends(get_db)):
    from auth import verify_reset_token
    import re
    # 1. Verify token
    email = verify_reset_token(req.token)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid or expired reset token.")
        
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
        
    # 2. Validate New Password Complexity
    password_regex = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
    if not re.match(password_regex, req.new_password):
        raise HTTPException(
            status_code=400, 
            detail="Password must be at least 8 characters long and contain uppercase, lowercase, numbers, and special characters."
        )

    # 3. Update Password and Reset Flag, and approve user just in case
    user.hashed_password = get_password_hash(req.new_password)
    user.force_password_change = False
    user.is_approved = True
    user.password_changed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    
    # 4. Audit Log
    client_host = request.client.host if request.client else "unknown"
    db.add(models.AuditLog(
        actor_email=user.email,
        actor_ip=client_host,
        action="PASSWORD_CHANGED_VIA_TOKEN",
        resource_type="User",
        resource_id=str(user.id),
        status="SUCCESS",
        details={"method": "token_reset"}
    ))
    
    db.commit()
    return {"message": "Password updated successfully. You can now login."}

@app.post("/api/auth/forgot-password")
def forgot_password(req: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    from auth import create_reset_token
    import email_service
    import os
    
    normalized_email = req.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == normalized_email).first()
    
    # Security: Always return success to prevent email enumeration
    if user:
        reset_token = create_reset_token(normalized_email)
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5174")
        reset_link = f"{frontend_url}/reset-password?token={reset_token}"
        
        email_service.send_reset_password_email(to_email=normalized_email, reset_link=reset_link)
        
        # Audit Log
        client_host = request.client.host if request.client else "unknown"
        db.add(models.AuditLog(
            actor_email=normalized_email,
            actor_ip=client_host,
            action="PASSWORD_RESET_REQUESTED",
            resource_type="User",
            resource_id=str(user.id),
            status="SUCCESS",
            details={"method": "forgot_password"}
        ))
        db.commit()
        
    return {"message": "If that email is registered, a reset link has been sent."}

@app.post("/api/admin/users/{user_id}/approve", dependencies=[Depends(require_permission("admin:users:write", "module:user-management"))])
def approve_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Identity not found.")
    if user.is_approved:
        raise HTTPException(status_code=409, detail="User is already approved.")
    user.is_approved = True
    db.commit()
    return {"message": "User approved."}

class RejectUserRequest(BaseModel):
    reason: Optional[str] = None

@app.post("/api/admin/users/{user_id}/reject", dependencies=[Depends(require_permission("admin:users:write", "module:user-management"))])
def reject_user(user_id: int, req: Optional[RejectUserRequest] = None, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Identity not found.")
    db.delete(user)
    db.commit()
    return {"message": "User rejected."}

class UpdateGroupsRequest(BaseModel):
    group_names: List[str]

@app.patch("/api/admin/users/{user_id}/groups", dependencies=[Depends(require_permission("admin:users:write", "module:user-management"))])
def update_user_groups(user_id: int, req: UpdateGroupsRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Identity not found.")
        
    groups_to_add = []
    for g_name in req.group_names:
        g = db.query(models.Group).filter(models.Group.name == g_name).first()
        if not g:
            raise HTTPException(status_code=422, detail=f"Group {g_name} not found.")
        groups_to_add.append(g)
        
    db.query(models.UserGroup).filter(models.UserGroup.user_id == user.id).delete()
    for g in groups_to_add:
        db.add(models.UserGroup(user_id=user.id, group_id=g.id))
    db.commit()
    
    return {"message": "Group membership updated.", "groups": req.group_names}

@app.delete("/api/admin/users/{user_id}", dependencies=[Depends(require_permission("admin:users:delete", "module:user-management"))])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Identity not found.")
    db.delete(user)
    db.commit()
    return {"message": "User access revoked."}
