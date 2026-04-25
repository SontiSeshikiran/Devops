import json
from database import SessionLocal, engine
from models import User, Group, Policy, IdentityPolicy, UserGroup, Base

# Ensure all tables are created
Base.metadata.create_all(bind=engine)

def seed():
    db = SessionLocal()
    
    # Check if we have already seeded the database
    if db.query(Policy).first():
        print("Database already seeded. Skipping initial IAM bootstrap.")
        db.close()
        return
    
    # 1. Define Default Policy Documents (AWS IAM Style)
    admin_policy_doc = {
        "Version": "2026-04-06",
        "Statement": [{"Effect": "Allow", "Action": ["*:*"], "Resource": ["*:*"]}]
    }
    
    police_policy_doc = {
        "Version": "2026-04-06",
        "Statement": [
            {"Effect": "Allow", "Action": ["drishti:*", "flo:*"], "Resource": ["module:drishti", "module:flo"]}
        ]
    }
    
    enterprise_policy_doc = {
        "Version": "2026-04-06",
        "Statement": [
            {"Effect": "Allow", "Action": ["drishti:*", "garuda:*", "nigha:*", "flo:*"], 
             "Resource": ["module:drishti", "module:garuda", "module:nigha", "module:flo"]}
        ]
    }
    
    free_policy_doc = {
        "Version": "2026-04-06",
        "Statement": [{"Effect": "Allow", "Action": ["flo:read"], "Resource": ["module:flo"]}]
    }
    
    # 2. Save Policy Records
    p_admin = Policy(name="AdminFullAccess", description="Full control over all modules.", policy_document=admin_policy_doc)
    p_police = Policy(name="PoliceCoreAccess", description="Access to Drishti and Network Maps.", policy_document=police_policy_doc)
    p_enterprise = Policy(name="EnterpriseFullSuite", description="Access to all intelligence modules.", policy_document=enterprise_policy_doc)
    p_free = Policy(name="BasicFreeUser", description="Read-only access to Global Sentinel maps.", policy_document=free_policy_doc)
    
    db.add_all([p_admin, p_police, p_enterprise, p_free])
    db.commit()
    
    # 3. Create Default Groups
    g_admins = Group(name="CloudAdmins", description="Strategic platform administrators.")
    g_police = Group(name="LawEnforcement", description="Law enforcement operators with forensic access.")
    g_enterprise = Group(name="EnterpriseTier", description="Commercial enterprise users.")
    g_free = Group(name="FreeTier", description="Public/Free tier users.")
    
    db.add_all([g_admins, g_police, g_enterprise, g_free])
    db.commit()
    
    # 4. Attach Policies to Groups (Identity Mapping)
    db.add_all([
        IdentityPolicy(policy_id=p_admin.id, group_id=g_admins.id),
        IdentityPolicy(policy_id=p_police.id, group_id=g_police.id),
        IdentityPolicy(policy_id=p_enterprise.id, group_id=g_enterprise.id),
        IdentityPolicy(policy_id=p_free.id, group_id=g_free.id)
    ])
    db.commit()
    
    print("Database seeding completed: IAM policies and groups configured.")
    db.close()

if __name__ == "__main__":
    seed()
