from __future__ import annotations

import sqlite3
import re
import threading
import queue
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class BufferedCursor:
    """Detach result rows from a shared connection before releasing its lock."""
    def __init__(self,cursor):
        self.description=cursor.description
        self.rowcount=cursor.rowcount
        self.lastrowid=getattr(cursor,'lastrowid',None)
        self._rows=cursor.fetchall() if cursor.description else []
        self._position=0

    def fetchone(self):
        if self._position>=len(self._rows):return None
        row=self._rows[self._position]
        self._position+=1
        return row

    def fetchall(self):
        rows=self._rows[self._position:]
        self._position=len(self._rows)
        return rows

    def fetchmany(self,size=1):
        rows=self._rows[self._position:self._position+size]
        self._position+=len(rows)
        return rows

    def __iter__(self):
        while (row:=self.fetchone()) is not None:yield row


class Database:
    """Small SQLite test adapter and PostgreSQL runtime connection."""

    def __init__(self, database: str):
        self.database = database
        self.is_postgres = database.startswith(("postgresql://", "postgres://")) or bool(
            re.search(r'(?:^|\s)(?:host|hostaddr|dbname|user|service)\s*=', database))
        self._lock = threading.RLock()
        self._key_guard=threading.Lock()
        self._keys={}
        self._advisory_idle=queue.LifoQueue()
        self._advisory_slots=threading.BoundedSemaphore(16)
        self._advisory_session=threading.local()
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
                cursor=self.connection.execute(statement, params)
                try:
                    return BufferedCursor(cursor)
                finally:
                    cursor.close()
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
        """Per-key mutex; PG session locks use a bounded, dedicated connection pool."""
        with self._key_guard:
            entry=self._keys.setdefault(key,[threading.RLock(),0])
            entry[1]+=1
        acquired=False
        try:
            acquired=entry[0].acquire(timeout=10)
            if not acquired:raise TimeoutError('Operation lock deadline exceeded')
            if not self.is_postgres:
                yield
                return
            with self._advisory_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT pg_advisory_lock(hashtextextended(%s,0))',(key,))
                try:
                    yield
                finally:
                    if not connection.closed and not connection.broken:
                        with connection.cursor() as cursor:
                            cursor.execute('SELECT pg_advisory_unlock(hashtextextended(%s,0))',(key,))
        finally:
            if acquired:entry[0].release()
            with self._key_guard:
                entry[1]-=1
                if not entry[1]:self._keys.pop(key,None)

    @contextmanager
    def _advisory_connection(self):
        existing=getattr(self._advisory_session,'connection',None)
        if existing is not None:
            yield existing
            return
        if not self._advisory_slots.acquire(timeout=10):raise TimeoutError('Lock connection pool is full')
        connection=None
        try:
            try:connection=self._advisory_idle.get_nowait()
            except queue.Empty:connection=self._connect_postgres()
            if connection.closed or connection.broken:
                connection.close()
                connection=self._connect_postgres()
            with connection.cursor() as cursor:cursor.execute("SET statement_timeout='10000ms'")
            self._advisory_session.connection=connection
            yield connection
        finally:
            self._advisory_session.connection=None
            if connection is not None:
                try:
                    if connection.closed or connection.broken:connection.close()
                    else:
                        with connection.cursor() as cursor:cursor.execute('SELECT pg_advisory_unlock_all()')
                        self._advisory_idle.put(connection)
                except Exception:connection.close()
            self._advisory_slots.release()

    def close(self) -> None:
        with self._lock:
            self.connection.close()
            while True:
                try:self._advisory_idle.get_nowait().close()
                except queue.Empty:break
