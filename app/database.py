from motor.motor_asyncio import AsyncIOMotorClient
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    database: AsyncIOMotorDatabase = None

db = Database()

async def connect_to_mongo():
    """Create database connection"""
    try:
        db.client = AsyncIOMotorClient(settings.mongodb_url)
        db.database = db.client[settings.database_name]
        
        # Test connection
        await db.client.admin.command('ping')
        logger.info("Connected to MongoDB")
        
        # Create indexes
        await create_indexes()
        
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

async def close_mongo_connection():
    """Close database connection"""
    if db.client:
        db.client.close()
        logger.info("Disconnected from MongoDB")

async def create_indexes():
    """Create necessary database indexes"""
    try:
        # Users collection indexes
        await db.database.users.create_index("email", unique=True)
        
        # Workspaces collection indexes
        await db.database.workspaces.create_index("admin_id")
        
        # Chats collection indexes
        await db.database.chats.create_index([("workspace_id", 1), ("customer_phone", 1)])
        await db.database.chats.create_index("workspace_id")
        await db.database.chats.create_index("phone_number")
        
        # Messages collection indexes
        await db.database.messages.create_index("chat_id")
        await db.database.messages.create_index([("chat_id", 1), ("timestamp", -1)])
        
        # Documents collection indexes
        await db.database.documents.create_index("workspace_id")
        await db.database.documents.create_index([("workspace_id", 1), ("status", 1)])
        await db.database.documents.create_index([("workspace_id", 1), ("document_type", 1)])
        await db.database.documents.create_index([("title", "text"), ("description", "text")])
        
        # Document chunks collection indexes
        await db.database.document_chunks.create_index("document_id")
        await db.database.document_chunks.create_index("workspace_id")
        await db.database.document_chunks.create_index([("workspace_id", 1), ("document_id", 1)])
        
        # Phone numbers collection indexes
        await db.database.phone_numbers.create_index("workspace_id")
        await db.database.phone_numbers.create_index("phone_number", unique=True)
        
        # Workflow steps collection indexes
        await db.database.workflow_steps.create_index("workspace_id")
        await db.database.workflow_steps.create_index([("workspace_id", 1), ("step_number", 1)])
        
        # Chat workflow progress collection indexes
        await db.database.chat_workflow_progress.create_index("chat_id", unique=True)
        await db.database.chat_workflow_progress.create_index("workspace_id")
        
        # Audit logs collection indexes
        await db.database.audit_logs.create_index("workspace_id")
        await db.database.audit_logs.create_index("user_id")
        await db.database.audit_logs.create_index("action")
        await db.database.audit_logs.create_index("timestamp")
        await db.database.audit_logs.create_index([("workspace_id", 1), ("action", 1), ("timestamp", -1)])
        
        # Message queue collection indexes
        await db.database.message_queue.create_index("message_id", unique=True)
        await db.database.message_queue.create_index("status")
        await db.database.message_queue.create_index("created_at")
        await db.database.message_queue.create_index([("status", 1), ("created_at", -1)])
        await db.database.message_queue.create_index("phone_number")
        
        # System logs collection indexes
        await db.database.system_logs.create_index("timestamp")
        await db.database.system_logs.create_index("type")
        await db.database.system_logs.create_index("job_id")
        
        # Export logs collection indexes
        await db.database.export_logs.create_index("workspace_id")
        await db.database.export_logs.create_index("export_type")
        await db.database.export_logs.create_index("export_timestamp")
        await db.database.export_logs.create_index([("workspace_id", 1), ("export_type", 1)], unique=True)
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")

def get_database() -> AsyncIOMotorDatabase:
    """Get database instance"""
    return db.database