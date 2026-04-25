import os
import sys

# Add parent directory to sys.path to allow imports from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import User, UserGroup

def delete_test_user():
    db = SessionLocal()
    email = "seshi934652@gmail.com"
    user = db.query(User).filter(User.email == email).first()
    if user:
        # Delete from UserGroup first if needed, though CASCADE might handle it
        db.query(UserGroup).filter(UserGroup.user_id == user.id).delete()
        db.delete(user)
        db.commit()
        print(f"User {email} deleted successfully.")
    else:
        print(f"User {email} not found.")

if __name__ == "__main__":
    delete_test_user()
