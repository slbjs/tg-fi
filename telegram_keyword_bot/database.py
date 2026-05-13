import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "telegram_bot")


class Database:
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.keywords_col = None

    async def connect(self):
        self.client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[DB_NAME]
        self.keywords_col = self.db["keywords"]

        # Create index for fast lookup
        await self.keywords_col.create_index("keyword", unique=True)
        logger.info(f"Connected to MongoDB: {DB_NAME}")

    async def upsert_keyword(self, keyword: str, reply: str, buttons: list = None):
        """Insert or update a keyword"""
        doc = {
            "keyword": keyword.lower().strip(),
            "reply": reply,
            "buttons": buttons or []
        }
        await self.keywords_col.update_one(
            {"keyword": keyword.lower().strip()},
            {"$set": doc},
            upsert=True
        )

    async def find_keyword(self, text: str) -> Optional[dict]:
        """Find exact keyword match"""
        return await self.keywords_col.find_one({"keyword": text.lower().strip()})

    async def find_keyword_partial(self, text: str) -> Optional[dict]:
        """Find if text CONTAINS any saved keyword"""
        text_lower = text.lower().strip()
        # Get all keywords and check if any appear in the message
        cursor = self.keywords_col.find({})
        async for doc in cursor:
            if doc["keyword"] in text_lower:
                return doc
        return None

    async def get_all_keywords(self) -> list:
        """Return all saved keywords"""
        cursor = self.keywords_col.find({}, {"_id": 0})
        return await cursor.to_list(length=None)

    async def delete_keyword(self, keyword: str) -> bool:
        """Delete a keyword, returns True if found and deleted"""
        result = await self.keywords_col.delete_one({"keyword": keyword.lower().strip()})
        return result.deleted_count > 0

    async def close(self):
        if self.client:
            self.client.close()


# Singleton instance
db = Database()
