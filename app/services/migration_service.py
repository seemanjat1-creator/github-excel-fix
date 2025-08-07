"""
Migration service to fix existing users without is_admin field
"""

import asyncio
import logging
from app.database import get_database
from datetime import datetime

logger = logging.getLogger(__name__)

class MigrationService:
    """Service to handle database migrations and fixes"""
    
    async def fix_user_admin_fields(self):
        """Add is_admin field to existing users who don't have it"""
        try:
            db = get_database()
            
            # Find users without is_admin field
            users_without_admin = await db.users.find({"is_admin": {"$exists": False}}).to_list(None)
            
            if not users_without_admin:
                logger.info("All users already have is_admin field")
                return
            
            logger.info(f"Found {len(users_without_admin)} users without is_admin field")
            
            # Check if there are any existing admins
            existing_admins = await db.users.count_documents({"is_admin": True})
            
            # Update users
            for user in users_without_admin:
                user_id = user["_id"]
                
                # Make first user admin if no admins exist
                is_admin = existing_admins == 0
                
                await db.users.update_one(
                    {"_id": user_id},
                    {"$set": {
                        "is_admin": is_admin,
                        "updated_at": datetime.utcnow()
                    }}
                )
                
                logger.info(f"Updated user {user['email']}: is_admin={is_admin}")
                
                # Only make first user admin
                if is_admin:
                    existing_admins = 1
            
            logger.info("User admin field migration completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to fix user admin fields: {e}")
            raise
    
    async def ensure_workspace_admins(self):
        """Ensure all workspaces have valid admin assignments"""
        try:
            db = get_database()
            
            # Get all workspaces
            workspaces = await db.workspaces.find({}).to_list(None)
            
            if not workspaces:
                logger.info("No workspaces found")
                return
            
            # Get first global admin
            global_admin = await db.users.find_one({"is_admin": True})
            
            if not global_admin:
                logger.warning("No global admin found")
                return
            
            admin_id = global_admin["_id"]
            updated_count = 0
            
            for workspace in workspaces:
                # Check if workspace admin exists
                admin_exists = await db.users.find_one({"_id": workspace["admin_id"]})
                
                if not admin_exists:
                    # Update workspace to use global admin
                    await db.workspaces.update_one(
                        {"_id": workspace["_id"]},
                        {"$set": {
                            "admin_id": admin_id,
                            "updated_at": datetime.utcnow()
                        }}
                    )
                    updated_count += 1
                    logger.info(f"Updated workspace {workspace['name']} admin to {global_admin['email']}")
            
            logger.info(f"Updated {updated_count} workspaces with valid admin assignments")
            
        except Exception as e:
            logger.error(f"Failed to ensure workspace admins: {e}")
            raise

# Global migration service instance
migration_service = MigrationService()

async def run_migrations():
    """Run all necessary migrations"""
    try:
        logger.info("Starting database migrations")
        
        await migration_service.fix_user_admin_fields()
        await migration_service.ensure_workspace_admins()
        
        logger.info("All migrations completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

if __name__ == "__main__":
    # Run migrations directly
    asyncio.run(run_migrations())