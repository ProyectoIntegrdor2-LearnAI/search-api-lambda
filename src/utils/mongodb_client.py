"""Cliente de MongoDB para consultar el catálogo de cursos."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)


class MongoCatalogClient:
    def __init__(self) -> None:
        uri = os.getenv("ATLAS_URI")
        if not uri:
            raise ValueError("ATLAS_URI es obligatorio")

        self._database_name = os.getenv("DATABASE_NAME", "learnia_db")
        self._collection_name = os.getenv("COLLECTION_NAME", "courses")
        self._search_index = os.getenv("ATLAS_SEARCH_INDEX", "default")

        self._client = MongoClient(
            uri,
            connectTimeoutMS=int(os.getenv("MONGO_CONNECT_TIMEOUT_MS", "10000")),
            serverSelectionTimeoutMS=int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS", "10000")),
        )
        self._collection: Collection = self._client[self._database_name][self._collection_name]

    def search_courses(
        self,
        query_embedding: List[float],
        limit: int,
        filters: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        pipeline: List[Dict[str, Any]] = [
            {
                "$vectorSearch": {
                    "index": self._search_index,
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": limit * 20,
                    "limit": limit,
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "title": 1,
                    "description": 1,
                    "url": 1,
                    "platform": 1,
                    "rating": 1,
                    "duration": 1,
                    "price": 1,
                    "language": 1,
                    "category": 1,
                    "level": 1,
                    "students_count": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

        try:
            candidates = list(self._collection.aggregate(pipeline))
        except PyMongoError as exc:
            logger.error(json.dumps({"event": "mongodb_vector_search_failed", "error": str(exc)}))
            raise

        filtered = [course for course in candidates if self._matches_filters(course, filters)]
        return [self._serialize_course(course) for course in filtered[:limit]]

    def get_course_by_id(self, course_id: str) -> Optional[Dict[str, Any]]:
        if ObjectId.is_valid(course_id):
            query: Dict[str, Any] = {"_id": ObjectId(course_id)}
        else:
            query = {"legacy_id": course_id}

        try:
            document = self._collection.find_one(query)
        except PyMongoError as exc:
            logger.error(json.dumps({"event": "mongodb_course_fetch_failed", "error": str(exc)}))
            raise

        if not document:
            return None
        return self._serialize_course(document, include_metadata=True)

    def get_categories(self) -> List[Dict[str, Any]]:
        pipeline = [
            {
                "$group": {
                    "_id": {"$ifNull": ["$category", "General"]},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"count": -1}},
        ]
        try:
            data = list(self._collection.aggregate(pipeline))
        except PyMongoError as exc:
            logger.error(json.dumps({"event": "mongodb_categories_failed", "error": str(exc)}))
            raise

        return [{"name": item["_id"], "count": item["count"]} for item in data]

    def get_trending_courses(self, limit: int) -> List[Dict[str, Any]]:
        try:
            cursor = self._collection.find(
                {},
                {
                    "_id": 1,
                    "title": 1,
                    "description": 1,
                    "url": 1,
                    "platform": 1,
                    "rating": 1,
                    "duration": 1,
                    "price": 1,
                    "language": 1,
                    "category": 1,
                    "level": 1,
                    "students_count": 1,
                },
            ).sort(
                [("students_count", -1), ("rating", -1)]
            ).limit(limit)
        except PyMongoError as exc:
            logger.error(json.dumps({"event": "mongodb_trending_failed", "error": str(exc)}))
            raise

        return [self._serialize_course(doc) for doc in cursor]

    def _matches_filters(self, course: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        if not filters:
            return True

        level = filters.get("level")
        if level and course.get("level") and course["level"].lower() != level.lower():
            return False

        category = filters.get("category")
        if category and course.get("category") and course["category"].lower() != category.lower():
            return False

        language = filters.get("language")
        if language and course.get("language") and course["language"].lower() != language.lower():
            return False

        max_price = filters.get("max_price")
        if max_price is not None:
            try:
                course_price = float(course.get("price") or 0.0)
                if course_price > float(max_price):
                    return False
            except (TypeError, ValueError):
                pass

        return True

    def _serialize_course(self, doc: Dict[str, Any], include_metadata: bool = False) -> Dict[str, Any]:
        course = {
            "course_id": str(doc.get("_id")),
            "title": doc.get("title", ""),
            "description": doc.get("description", ""),
            "url": doc.get("url", ""),
            "platform": doc.get("platform", ""),
            "rating": doc.get("rating"),
            "duration": doc.get("duration"),
            "price": doc.get("price"),
            "language": doc.get("language"),
            "category": doc.get("category"),
            "level": doc.get("level"),
            "students_count": doc.get("students_count"),
        }
        if include_metadata:
            course["embedding_model"] = doc.get("embedding_model")
            course["embedding_dim"] = doc.get("embedding_dim")
            course["processed_at"] = doc.get("processed_at")
        return course


_mongo_client: MongoCatalogClient | None = None


def get_mongo_client() -> MongoCatalogClient:
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoCatalogClient()
    return _mongo_client
