"""
MongoDB connection setup for resolve_AI.
Reads MONGO_URI from environment variables (or falls back to localhost).
"""

import os
from pymongo import MongoClient
from pymongo.database import Database

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        mongo_uri = os.getenv(
            "MONGO_URI", "mongodb://admin:admin@localhost:27017")
        _client = MongoClient(mongo_uri)
    return _client


def get_db(db_name: str = "resolve_ai") -> Database:
    return get_client()[db_name]
