"""Server-owned query catalog. SQL, table names and tenant scope never come from clients."""
from __future__ import annotations

CATALOG = {
    'operations': {'name':'운영 지원 이력', 'database':'사내 검증 DB', 'table':'asg_operations',
        'columns':{'ticket_id':'internal','category':'internal','status':'internal','description':'internal'},
        'filter_columns':['category','status'], 'tenants':['north','south'],
        'roles':['report-reader','report-writer','report-submitter']},
    'employee-directory': {'name':'임직원 업무 연락처', 'database':'사내 검증 DB', 'table':'asg_directory',
        'columns':{'employee_id':'internal','name':'internal','department':'internal','work_email':'sensitive'},
        'filter_columns':['department'], 'tenants':['north','south'],
        'roles':['report-writer','report-submitter']},
    'payroll': {'name':'급여·정산 정보', 'database':'사내 검증 DB', 'table':'asg_payroll',
        'columns':{'employee_id':'internal','department':'internal','salary':'restricted','bank_account':'restricted'},
        'filter_columns':['department'], 'tenants':['north'], 'roles':['report-submitter']},
}


def validate_query(arguments, principal):
    errors=[]
    if not isinstance(arguments,dict) or set(arguments)!={'dataset_id','columns','filters','row_limit','purpose'}:
        return ['INVALID_REQUEST_FIELDS']
    dataset=CATALOG.get(arguments['dataset_id']) if isinstance(arguments['dataset_id'],str) else None
    if not dataset:
        errors.append('DATASET_NOT_REGISTERED')
    elif principal['tenant'] not in dataset['tenants'] or principal['role'] not in dataset['roles']:
        errors.append('DATASET_OUT_OF_SCOPE')
    columns=arguments['columns']
    if not isinstance(columns,list) or not columns or len(columns)>12 or any(not isinstance(c,str) for c in columns):
        errors.append('INVALID_COLUMNS')
    elif len(set(columns))!=len(columns) or (dataset and any(c not in dataset['columns'] for c in columns)):
        errors.append('COLUMN_NOT_REGISTERED')
    if type(arguments['row_limit']) is not int or not 1<=arguments['row_limit']<=5000:
        errors.append('ROW_LIMIT_EXCEEDED')
    filters=arguments['filters']
    if not isinstance(filters,dict) or len(filters)>3:
        errors.append('INVALID_FILTERS')
    elif any(not isinstance(k,str) or (dataset and k not in dataset['filter_columns']) or not isinstance(v,str) or not 1<=len(v)<=100 for k,v in filters.items()):
        errors.append('INVALID_FILTERS')
    purpose=arguments['purpose']
    if not isinstance(purpose,str) or not 5<=len(purpose.strip())<=1000:
        errors.append('PURPOSE_REQUIRED')
    return list(dict.fromkeys(errors))


def initialize_demo_database(connection):
    """Fictional rows only. No production connection or real employee information."""
    connection.executescript('''
    CREATE TABLE IF NOT EXISTS asg_operations(tenant TEXT,ticket_id TEXT,category TEXT,status TEXT,description TEXT);
    CREATE TABLE IF NOT EXISTS asg_directory(tenant TEXT,employee_id TEXT,name TEXT,department TEXT,work_email TEXT);
    CREATE TABLE IF NOT EXISTS asg_payroll(tenant TEXT,employee_id TEXT,department TEXT,salary INTEGER,bank_account TEXT);
    ''')
    if connection.execute('SELECT count(*) FROM asg_operations').fetchone()[0]:
        return
    connection.execute('BEGIN IMMEDIATE')
    for tenant in ('north','south'):
        connection.executemany('INSERT INTO asg_operations VALUES(?,?,?,?,?)',[
            (tenant,f'{tenant}-T-{n:04}', 'network' if n%2 else 'access', 'open' if n%3 else 'closed',f'Fictional lab support request {n}') for n in range(1,121)])
        connection.executemany('INSERT INTO asg_directory VALUES(?,?,?,?,?)',[
            (tenant,f'{tenant}-E-{n:03}',f'검증 직원 {n:03}','지원팀' if n%2 else '운영팀',f'lab-{tenant}-{n}@example.test') for n in range(1,41)])
    connection.executemany('INSERT INTO asg_payroll VALUES(?,?,?,?,?)',[
        ('north',f'north-E-{n:03}','운영팀',3000000+n*10000,f'MOCK-ACCOUNT-{n:03}') for n in range(1,41)])
    connection.execute('COMMIT')


def execute_catalog_query(connection, arguments, tenant, role):
    errors=validate_query(arguments,{'tenant':tenant,'role':role})
    if errors:
        raise ValueError(','.join(errors))
    spec=CATALOG[arguments['dataset_id']]
    # Identifiers are selected only from the constant server catalog; values are bound parameters.
    fields=', '.join('"'+c+'"' for c in arguments['columns'])
    where=['tenant = ?']
    params=[tenant]
    for column,value in sorted(arguments['filters'].items()):
        where.append('"'+column+'" = ?')
        params.append(value)
    params.append(arguments['row_limit'])
    rows=connection.execute(f'SELECT {fields} FROM "{spec["table"]}" WHERE '+ ' AND '.join(where)+' LIMIT ?',params).fetchall()
    return {'dataset_id':arguments['dataset_id'],'columns':arguments['columns'],'rows':[dict(row) for row in rows],
            'row_count':len(rows),'requested_row_limit':arguments['row_limit'],'data_mode':'fictional_sqlite_lab'}
