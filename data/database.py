from __future__ import annotations

import sqlite3
from typing import Optional

from config import DATABASE_PATH


class Database:
    def __init__(self, name: str = DATABASE_PATH):
        self.name = name

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.name)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _normalize_user_id(value: object) -> int | None:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _ensure_columns(conn: sqlite3.Connection, table_name: str, required_columns: dict[str, str]) -> None:
        existing_columns = {
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        for column_name, definition in required_columns.items():
            if column_name not in existing_columns:
                conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")

    @staticmethod
    def _get_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
        return {
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        }

    async def create_db(self) -> None:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    topic TEXT NOT NULL,
                    style TEXT NOT NULL,
                    tags_name TEXT,
                    tags_content TEXT,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self._ensure_columns(
                conn,
                "posts",
                {
                    "tags_name": "TEXT",
                    "tags_content": "TEXT",
                },
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tags_pools (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    tags_name TEXT NOT NULL,
                    tags_content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self._ensure_columns(
                conn,
                "tags_pools",
                {
                    "tags_name": "TEXT",
                    "tags_content": "TEXT",
                },
            )
            tags_pool_columns = self._get_columns(conn, "tags_pools")
            if {"name", "tags"}.issubset(tags_pool_columns):
                conn.execute(
                    """
                    UPDATE tags_pools
                    SET tags_name = COALESCE(tags_name, name),
                        tags_content = COALESCE(tags_content, tags)
                    WHERE (tags_name IS NULL OR tags_name = '')
                       OR (tags_content IS NULL OR tags_content = '')
                    """
                )
            conn.commit()

    async def save_post(
        self,
        user_id: int,
        topic: str,
        style: str,
        content: str,
        tags_name: Optional[str] = None,
        tags_content: Optional[str] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO posts (user_id, topic, style, tags_name, tags_content, content)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, topic, style, tags_name, tags_content, content),
            )
            conn.commit()

    async def add_tag_pool(self, user_id: int, tags_name: str, tags_content: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tags_pools (user_id, tags_name, tags_content)
                VALUES (?, ?, ?)
                """,
                (user_id, tags_name, tags_content),
            )
            conn.commit()

    async def show_user_data(self, user_id: int) -> list[sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, tags_name, tags_content
                FROM tags_pools
                WHERE user_id = ?
                ORDER BY id DESC
                """,
                (user_id,),
            ).fetchall()
        return rows

    async def show_by_increment(self, pool_id: int) -> Optional[sqlite3.Row]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, user_id, tags_name, tags_content
                FROM tags_pools
                WHERE id = ?
                """,
                (pool_id,),
            ).fetchone()
        return row

    async def get_user_pool(self, pool_id: int, user_id: int) -> Optional[sqlite3.Row]:
        pool = await self.show_by_increment(pool_id)
        if not pool:
            return None

        pool_user_id = self._normalize_user_id(pool["user_id"])
        if pool_user_id != self._normalize_user_id(user_id):
            return None

        return pool

    async def delete_pack_by_id(self, pool_id: int, user_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                DELETE FROM tags_pools
                WHERE id = ? AND user_id = ?
                """,
                (pool_id, user_id),
            )
            conn.commit()
        return cursor.rowcount > 0

    async def replace_pack(self, pool_id: int, user_id: int, tags_content: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE tags_pools
                SET tags_content = ?
                WHERE id = ? AND user_id = ?
                """,
                (tags_content, pool_id, user_id),
            )
            conn.commit()
        return cursor.rowcount > 0
