from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class Database:
    """Small SQLite test adapter and PostgreSQL runtime connection."""

    def __init__(self, database: str):
        self.database = database
        self.is_postgres = database.startswith(("postgresql://", "postgres://", "host="))
        self._lock = threading.RLock()
        if self.is_postgres:
            import psycopg
            self._psycopg = psycopg
            self.connection = self._connect_postgres()
        else:
            if database != ":memory:":
                Path(database).parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(database, check_same_thread=False, isolation_level=None)
            self.connection.row_factory = sqlite3.Row
            self.connection.execute("PRAGMA foreign_keys=ON")

    def _connect_postgres(self):
        from psycopg.rows import dict_row

        return self._psycopg.connect(self.database, autocommit=True, row_factory=dict_row)

    def _reconnect_if_broken(self) -> None:
        if self.is_postgres and (self.connection.closed or self.connection.broken):
            try:
                self.connection.close()
            finally:
                self.connection = self._connect_postgres()

    def execute(self, statement: str, params: tuple[Any, ...] | list[Any] = ()):
        if self.is_postgres:
            statement = statement.replace("BEGIN IMMEDIATE", "BEGIN").replace("?", "%s")
        with self._lock:
            if self.is_postgres:
                self._reconnect_if_broken()
            try:
                return self.connection.execute(statement, params)
            except Exception as exc:
                if self.is_postgres and isinstance(exc, (self._psycopg.OperationalError, self._psycopg.InterfaceError)):
                    if self.connection.broken or self.connection.closed:
                        self.connection.close()
                # Never replay a failed statement: a write may have committed
                # before the transport failed. A later request can reconnect and
                # reconcile its stored state by idempotency key or tool receipt.
                raise

    def executescript(self, script: str) -> None:
        with self._lock:
            if self.is_postgres:
                self.connection.execute(script)
            else:
                self.connection.executescript(script)

    @contextmanager
    def advisory_lock(self, key: str):
        """Serialize a PostgreSQL operation across Gateway processes by stable key."""
        if not self.is_postgres:
            yield
            return
        self.execute("SELECT pg_advisory_lock(hashtextextended(?, 0))", (key,))
        try:
            yield
        finally:
            self.execute("SELECT pg_advisory_unlock(hashtextextended(?, 0))", (key,))

    def close(self) -> None:
        with self._lock:
            self.connection.close()
