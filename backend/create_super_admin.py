from database import SessionLocal
from models import User, Group, UserGroup
import uuid

def create_super_admin():
    db = SessionLocal()
    
    # 1. Ensure the CloudAdmins group exists
    admin_group = db.query(Group).filter(Group.name == "CloudAdmins").first()
    if not admin_group:
        print("Error: CloudAdmins group not found. Run seed.py first.")
        db.close()
        return

    # 2. Check if the user already exists
    email = "Appu@gmail.com"
    existing_user = db.query(User).filter(User.email == email).first()
    
    if existing_user:
        print(f"User {email} already exists. Updating to Super Admin...")
        user = existing_user
    else:
        print(f"Creating Super Admin user: {email}")
        user = User(
            firebase_uid="super-admin-appu-uid", # Mock UID
            email=email,
            display_name="Super Admin Appu",
            role="admin",
            is_approved=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 3. Add user to CloudAdmins group if not already there
    membership = db.query(UserGroup).filter(
        UserGroup.user_id == user.id, 
        UserGroup.group_id == admin_group.id
    ).first()
    
    if not membership:
        db.add(UserGroup(user_id=user.id, group_id=admin_group.id))
        db.commit()
        print(f"User {email} added to CloudAdmins group.")
    else:
        print(f"User {email} is already a member of CloudAdmins.")

    db.close()
    print("Super Admin creation complete.")

if __name__ == "__main__":
    create_super_admin()
