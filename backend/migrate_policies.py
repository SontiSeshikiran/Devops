from database import SessionLocal
from models import Policy
import json

def migrate():
    db = SessionLocal()
    try:
        print("Migrating policies to match new requirements...")
        
        # 1. Update Police Policy
        police_policy = db.query(Policy).filter(Policy.name == "PoliceCoreAccess").first()
        if police_policy:
            print("Updating PoliceCoreAccess policy...")
            police_policy.description = "Access to all modules (Drishti, Garuda, Nigha, Flo)"
            police_policy.policy_document = {
                "Version": "2026-04-06", 
                "Statement": [{"Effect": "Allow", "Action": ["*:*"], "Resource": ["*:*"]}]
            }
        
        # 2. Update Enterprise Policy
        enterprise_policy = db.query(Policy).filter(Policy.name == "EnterpriseFullSuite").first()
        if enterprise_policy:
            print("Updating EnterpriseFullSuite policy...")
            enterprise_policy.description = "Access to all intelligence modules except Drishti"
            enterprise_policy.policy_document = {
                "Version": "2026-04-06", 
                "Statement": [
                    {"Effect": "Allow", "Action": ["garuda:*", "nigha:*", "flo:*"], 
                     "Resource": ["module:garuda", "module:nigha", "module:flo"]}
                ]
            }
            
        db.commit()
        print("Migration completed successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error during migration: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
