"""Repositorio para favoritos de cursos en PostgreSQL."""

from __future__ import annotations

import logging
import os
import uuid
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

import psycopg2
from psycopg2 import pool
from psycopg2 import sql

logger = logging.getLogger(__name__)


class FavoritesRepository:
    def __init__(self) -> None:
        host = os.getenv("POSTGRES_HOST")
        password = os.getenv("POSTGRES_PASSWORD")
        if not host or not password:
            raise ValueError("POSTGRES_HOST y POSTGRES_PASSWORD son obligatorios")

        self._db = os.getenv("POSTGRES_DB", "postgres")
        self._user = os.getenv("POSTGRES_USER", "postgres")
        self._port = int(os.getenv("POSTGRES_PORT", "5432"))
        self._ssl_enabled = os.getenv("DB_SSL", "false").lower() == "true"
        table = os.getenv("FAVORITES_TABLE", "user_favorites")
        if not table.replace("_", "").isalnum():
            raise ValueError("FAVORITES_TABLE contiene caracteres inválidos")
        self._table = table

        min_conn = int(os.getenv("POSTGRES_POOL_MIN", "1"))
        max_conn = int(os.getenv("POSTGRES_POOL_MAX", "5"))

        conn_kwargs = {
            "host": host,
            "port": self._port,
            "dbname": self._db,
            "user": self._user,
            "password": password,
            "connect_timeout": 10,
        }
        if self._ssl_enabled:
            conn_kwargs["sslmode"] = "require"

        self._pool = pool.SimpleConnectionPool(min_conn, max_conn, **conn_kwargs)

    @contextmanager
    def connection(self):
        conn = self._pool.getconn()
        try:
            yield conn
        finally:
            self._pool.putconn(conn)

    def is_favorite(self, user_id: str, course_id: str) -> bool:
        query = sql.SQL("SELECT 1 FROM {} WHERE user_id = %s AND mongodb_course_id = %s LIMIT 1").format(
            sql.Identifier(self._table)
        )
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(query, (user_id, course_id))
            return cur.fetchone() is not None

    def set_favorite(self, user_id: str, course_id: str, *, should_favorite: bool) -> bool:
        with self.connection() as conn:
            with conn.cursor() as cur:
                if should_favorite:
                    statement = sql.SQL(
                        """
                        INSERT INTO {} (favorite_id, user_id, mongodb_course_id, created_at)
                        VALUES (%s, %s, %s, NOW())
                        ON CONFLICT (user_id, mongodb_course_id) DO NOTHING
                        """
                    ).format(sql.Identifier(self._table))
                    cur.execute(statement, (str(uuid.uuid4()), user_id, course_id))
                    conn.commit()
                    return True
                statement = sql.SQL("DELETE FROM {} WHERE user_id = %s AND mongodb_course_id = %s").format(
                    sql.Identifier(self._table)
                )
                cur.execute(statement, (user_id, course_id))
                conn.commit()
                return False

    def list_favorites(self, user_id: str) -> List[Dict[str, Any]]:
        query = sql.SQL(
            "SELECT mongodb_course_id, created_at FROM {} WHERE user_id = %s ORDER BY created_at DESC"
        ).format(sql.Identifier(self._table))
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(query, (user_id,))
            rows = cur.fetchall()
        return [
            {"course_id": row[0], "created_at": row[1]}
            for row in rows
        ]


_favorites_repo: Optional[FavoritesRepository] = None


def get_favorites_repository() -> FavoritesRepository:
    global _favorites_repo
    if _favorites_repo is None:
        _favorites_repo = FavoritesRepository()
    return _favorites_repo
