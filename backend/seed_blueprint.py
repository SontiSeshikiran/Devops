from database import SessionLocal, engine, Base
from models import Group, Policy, User, UserGroup, IdentityPolicy
from auth import get_password_hash
import json

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check if already seeded
        groups_count = db.query(Group).count()
        if groups_count == 0:
            print("Seeding groups and policies according to IAM blueprint...")
            # ... (group/policy creation code continues)
        else:
            print(f"Groups already seeded ({groups_count}). Checking for admin user...")

        # Ensure Groups are available for the rest of the script
        cloud_admins = db.query(Group).filter(Group.name == "CloudAdmins").first()
        law_enforcement = db.query(Group).filter(Group.name == "LawEnforcement").first()
        enterprise_tier = db.query(Group).filter(Group.name == "EnterpriseTier").first()
        free_tier = db.query(Group).filter(Group.name == "FreeTier").first()
        
        if groups_count == 0:
            # Create Policies
            admin_policy = Policy(
                name="AdminFullAccess",
                description="Allows all actions on all resources",
                policy_document={"Version": "2026-04-06", "Statement": [{"Effect": "Allow", "Action": ["*:*"], "Resource": ["*:*"]}]}
            )
            police_policy = Policy(
                name="PoliceCoreAccess",
                description="Access to all modules (Drishti, Garuda, Nigha, Flo)",
                policy_document={"Version": "2026-04-06", "Statement": [{"Effect": "Allow", "Action": ["*:*"], "Resource": ["*:*"]}]}
            )
            enterprise_policy = Policy(
                name="EnterpriseFullSuite",
                description="Access to all intelligence modules except Drishti",
                policy_document={"Version": "2026-04-06", "Statement": [
                    {"Effect": "Allow", "Action": ["garuda:*", "nigha:*", "flo:*"], 
                     "Resource": ["module:garuda", "module:nigha", "module:flo"]}
                ]}
            )
            free_user_policy = Policy(
                name="BasicFreeUser",
                description="Read-only access to Flo",
                policy_document={"Version": "2026-04-06", "Statement": [{"Effect": "Allow", "Action": ["flo:read"], "Resource": ["module:flo"]}]}
            )

            db.add_all([admin_policy, police_policy, enterprise_policy, free_user_policy])
            db.commit()

            # Create Groups
            cloud_admins = Group(name="CloudAdmins", description="Platform operators, Super Admins")
            law_enforcement = Group(name="LawEnforcement", description="Police, LEA investigators")
            enterprise_tier = Group(name="EnterpriseTier", description="Commercial security teams")
            free_tier = Group(name="FreeTier", description="Trial / public users")

            db.add_all([cloud_admins, law_enforcement, enterprise_tier, free_tier])
            db.commit()

            # Bind Policies to Groups
            db.add_all([
                IdentityPolicy(group_id=cloud_admins.id, policy_id=admin_policy.id),
                IdentityPolicy(group_id=law_enforcement.id, policy_id=police_policy.id),
                IdentityPolicy(group_id=enterprise_tier.id, policy_id=enterprise_policy.id),
                IdentityPolicy(group_id=free_tier.id, policy_id=free_user_policy.id)
            ])
            db.commit()

        # Create Default Admin
        admin_user = db.query(User).filter(User.email == "admin@blutor.app").first()
        if not admin_user:
            admin_user = User(
                email="admin@blutor.app",
                display_name="Super Admin",
                hashed_password=get_password_hash("admin123"),
                is_approved=True,
                force_password_change=False
            )
            db.add(admin_user)
            db.commit()
            
            db.add(UserGroup(user_id=admin_user.id, group_id=cloud_admins.id))
            db.commit()

        print("Seeding completed successfully.")

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
