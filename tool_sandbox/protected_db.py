"""Read-only PostgreSQL target; credentials belong only to the tool service."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
import os
from pathlib import Path
import re
from uuid import UUID

from security_agent.catalog import CATALOG, execute_catalog_query, validate_query
from security_agent.db_target import target_config


def _pg_config():
    from psycopg.conninfo import conninfo_to_dict
    dsn_file = os.environ.get('PROTECTED_DB_DSN_FILE', '')
    if not dsn_file:
        raise ValueError('Protected DB connection file is required')
    options = conninfo_to_dict(Path(dsn_file).read_text(encoding='utf-8').strip())
    if any(not options.get(key) for key in ('host', 'dbname', 'user')):
        raise ValueError('Explicit host, database and read-only user are required')
    local_lab = os.environ.get('PROTECTED_DB_LOCAL_TEST') == '1'
    if local_lab:
        if options['host'] not in {'127.0.0.1', '::1', 'localhost'}:
            raise ValueError('Unencrypted tests are limited to loopback')
    elif options.get('sslmode') != 'verify-full':
        raise ValueError('Protected PostgreSQL requires sslmode=verify-full')
    schema = os.environ.get('PROTECTED_DB_SCHEMA', 'asg_access')
    if not re.fullmatch(r'[a-z_][a-z0-9_]{0,62}', schema):
        raise ValueError('Invalid protected DB schema')
    options.update(connect_timeout=2, application_name='asg-protected-readonly')
    return options, schema


@contextmanager
def readonly_connection():
    import psycopg
    from psycopg.rows import dict_row
    options, schema = _pg_config()
    with psycopg.connect(**options, autocommit=True, row_factory=dict_row) as connection:
        with connection.transaction():
            connection.execute('SET TRANSACTION READ ONLY')
            connection.execute("SET LOCAL statement_timeout = '2000ms'")
            connection.execute("SET LOCAL lock_timeout = '500ms'")
            connection.execute('SET LOCAL search_path = pg_catalog')
            role = connection.execute('SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user').fetchone()
            if not role or role['rolsuper'] or role['rolbypassrls']:
                raise ValueError('A non-superuser without BYPASSRLS is required')
            yield connection, schema


def _json_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (Decimal, UUID)):
        return str(value)
    return value


def execute_query(sqlite_connection, arguments, tenant, role, expected_target):
    config = target_config()
    if expected_target != config['id']:
        raise ValueError('Protected DB target differs from the approved target')
    if config['backend'] == 'sqlite':
        return execute_catalog_query(sqlite_connection, arguments, tenant, role)
    errors = validate_query(arguments, {'tenant': tenant, 'role': role})
    if errors:
        raise ValueError(','.join(errors))
    from psycopg import sql
    spec = CATALOG[arguments['dataset_id']]
    with readonly_connection() as (connection, schema):
        fields = sql.SQL(', ').join(sql.Identifier(c) for c in arguments['columns'])
        clauses = [sql.SQL('{} = %s').format(sql.Identifier('tenant'))]
        parameters = [tenant]
        for column, value in sorted(arguments['filters'].items()):
            clauses.append(sql.SQL('{} = %s').format(sql.Identifier(column)))
            parameters.append(value)
        parameters.append(arguments['row_limit'])
        statement = sql.SQL('SELECT {} FROM {} WHERE {} LIMIT %s').format(
            fields, sql.Identifier(schema, spec['table']), sql.SQL(' AND ').join(clauses))
        rows = connection.execute(statement, parameters).fetchall()
    return {'dataset_id': arguments['dataset_id'], 'columns': arguments['columns'],
            'rows': [{key: _json_value(value) for key, value in row.items()} for row in rows],
            'row_count': len(rows), 'requested_row_limit': arguments['row_limit'],
            'data_mode': 'postgresql', 'target_id': config['id']}


def health(sqlite_connection):
    config = target_config()
    if config['backend'] == 'sqlite':
        sqlite_connection.execute('SELECT ticket_id FROM asg_operations LIMIT 1').fetchone()
        return {'status': 'ready', 'detail': '검증용 SQLite DB 읽기 연결 정상',
                'mode': 'fictional_sqlite_lab', 'target': config}
    from psycopg import sql
    with readonly_connection() as (connection, schema):
        # Verify schema and SELECT grants without reading business rows.
        for spec in CATALOG.values():
            fields = sql.SQL(', ').join(sql.Identifier(c) for c in ['tenant', *spec['columns']])
            connection.execute(sql.SQL('SELECT {} FROM {} LIMIT 0').format(
                fields, sql.Identifier(schema, spec['table']))).fetchall()
    return {'status': 'ready', 'detail': 'PostgreSQL 읽기 전용 연결·등록 대상 권한 정상',
            'mode': 'postgresql', 'target': config}
