import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME   = os.getenv("DB_NAME", "telegram_bot")


class Database:
    def __init__(self):
        self.client:   Optional[AsyncIOMotorClient] = None
        self.db        = None
        self.movies    = None          # collection

    async def connect(self):
        self.client = AsyncIOMotorClient(MONGO_URI)
        self.db     = self.client[DB_NAME]
        self.movies = self.db["movies"]
        await self.movies.create_index("keyword", unique=True)
        logger.info(f"Connected to MongoDB: {DB_NAME}")

    # ── Write ──────────────────────────────────────────────────────────────────

    async def upsert_movie(
        self,
        keyword:      str,
        photo_file_id: str,
        caption:      str,
        btn_text:     str,
        btn_url:      str,
    ):
        """Insert or update a movie entry."""
        doc = {
            "keyword":       keyword.lower().strip(),
            "photo_file_id": photo_file_id,
            "caption":       caption,
            "btn_text":      btn_text,
            "btn_url":       btn_url,
        }
        await self.movies.update_one(
            {"keyword": doc["keyword"]},
            {"$set": doc},
            upsert=True,
        )

    # ── Read ───────────────────────────────────────────────────────────────────

    async def find_movie(self, text: str) -> Optional[dict]:
        """Exact keyword match."""
        return await self.movies.find_one({"keyword": text.lower().strip()})

    async def find_movie_partial(self, text: str) -> Optional[dict]:
        """Return first movie whose keyword appears anywhere in text."""
        text_lower = text.lower().strip()
        async for doc in self.movies.find({}):
            if doc["keyword"] in text_lower:
                return doc
        return None

    async def get_all_movies(self) -> list:
        cursor = self.movies.find({}, {"_id": 0})
        return await cursor.to_list(length=None)

    # ── Delete ─────────────────────────────────────────────────────────────────

    async def delete_movie(self, keyword: str) -> bool:
        result = await self.movies.delete_one({"keyword": keyword.lower().strip()})
        return result.deleted_count > 0

    async def close(self):
        if self.client:
            self.client.close()


# Singleton
db = Database()
