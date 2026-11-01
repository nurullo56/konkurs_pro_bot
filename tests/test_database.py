"""
test_database.py — Database wrapper testlari.

Testlar qamrovi:
  - connect() chaqirilmagan holatda RuntimeError
  - connect() dan keyin execute/fetchrow/fetch ishlashi
  - close() dan keyin qayta ishlatish RuntimeError
  - transaction() context manager
  - _safe_dsn() parolni yashirishi
"""
from __future__ import annotations

import pytest

from database.db import Database, _safe_dsn


class TestEnsureConnected:
    async def test_execute_without_connect_raises(self):
        db = Database(db_type="sqlite", path=":memory:")
        with pytest.raises(RuntimeError, match="not initialized"):
            await db.execute("INSERT INTO users (user_id) VALUES (?)", 1)

    async def test_fetchrow_without_connect_raises(self):
        db = Database(db_type="sqlite", path=":memory:")
        with pytest.raises(RuntimeError, match="not initialized"):
            await db.fetchrow("SELECT 1")

    async def test_fetch_without_connect_raises(self):
        db = Database(db_type="sqlite", path=":memory:")
        with pytest.raises(RuntimeError, match="not initialized"):
            await db.fetch("SELECT 1")

    async def test_execute_many_empty_list_no_error_without_connect(self):
        """Bo'sh list bilan xato bermasligi kerak."""
        db = Database(db_type="sqlite", path=":memory:")
        await db.execute_many("INSERT INTO users (user_id) VALUES (?)", [])

    async def test_transaction_without_connect_raises(self):
        db = Database(db_type="sqlite", path=":memory:")
        with pytest.raises(RuntimeError, match="not initialized"):
            async with db.transaction():
                pass

    async def test_close_then_execute_raises(self, db: Database):
        await db.close()
        with pytest.raises(RuntimeError, match="not initialized"):
            await db.execute("INSERT INTO users (user_id) VALUES (?)", 1)


class TestTransaction:
    async def test_transaction_commits_on_success(self, db: Database):
        async with db.transaction():
            await db.sqlite_conn.execute(
                "INSERT INTO users (user_id, full_name, registered) VALUES (?, ?, 1)",
                (555, "Tx User"),
            )
        row = await db.fetchrow("SELECT user_id FROM users WHERE user_id = ?", 555)
        assert row is not None

    async def test_transaction_rollbacks_on_error(self, db: Database):
        with pytest.raises(ValueError):
            async with db.transaction():
                await db.sqlite_conn.execute(
                    "INSERT INTO users (user_id, full_name, registered) VALUES (?, ?, 1)",
                    (666, "Rollback User"),
                )
                raise ValueError("Test error")
        row = await db.fetchrow("SELECT user_id FROM users WHERE user_id = ?", 666)
        assert row is None


class TestSafeDsn:
    def test_dsn_with_password_masked(self):
        result = _safe_dsn("postgresql://user:secret123@localhost:5432/db")
        assert "secret123" not in result
        assert "***" in result

    def test_dsn_without_password(self):
        dsn = "postgresql://user@localhost/db"
        assert _safe_dsn(dsn) == dsn

    def test_invalid_dsn_returns_safe_placeholder(self):
        assert _safe_dsn(None) == "<dsn>"  # type: ignore
