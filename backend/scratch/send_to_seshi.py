import os
import sys

# Add parent directory to sys.path to allow imports from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from database import SessionLocal
from models import User, Group, UserGroup
from auth import get_password_hash, create_reset_token
import email_service

def send_mail_to_seshi():
    db = SessionLocal()
    email = "seshi934652@gmail.com"
    
    # 1. Provision user if not exists
    user = db.query(User).filter(User.email == email).first()
    if not user:
        group = db.query(Group).filter(Group.name == "FreeTier").first()
        user = User(
            email=email,
            hashed_password=get_password_hash("Welcome123!"),
            display_name="Seshi",
            is_approved=True,
            force_password_change=True
        )
        db.add(user)
        db.commit()
        if group:
            db.add(UserGroup(user_id=user.id, group_id=group.id))
            db.commit()
        print(f"Provisioned new user identity: {email}")

    # 2. Generate reset token
    token = create_reset_token(email)
    
    # 3. Forge link
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5174")
    link = f"{frontend_url}/reset-password?token={token}"
    
    # 4. Send email
    print(f"Sending welcome email to {email}...")
    success = email_service.send_welcome_email(email, link, "Welcome123!")
    
    if success:
        print("Email sent successfully!")
    else:
        print("Failed to send email.")

if __name__ == "__main__":
    # Ensure we are in the backend directory for imports to work if run from root
    # But I'll run it from backend directly.
    send_mail_to_seshi()
