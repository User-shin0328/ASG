-- Fictional data only. Run only in a new, dedicated ASG validation database.
-- No real names, email addresses, bank accounts or corporate records.
CREATE SCHEMA asg_access;
CREATE TABLE asg_access.asg_operations (
    tenant TEXT NOT NULL, ticket_id TEXT PRIMARY KEY, category TEXT NOT NULL,
    status TEXT NOT NULL, description TEXT NOT NULL
);
CREATE TABLE asg_access.asg_directory (
    tenant TEXT NOT NULL, employee_id TEXT PRIMARY KEY, name TEXT NOT NULL,
    department TEXT NOT NULL, work_email TEXT NOT NULL
);
CREATE TABLE asg_access.asg_payroll (
    tenant TEXT NOT NULL, employee_id TEXT PRIMARY KEY, department TEXT NOT NULL,
    salary INTEGER NOT NULL, bank_account TEXT NOT NULL
);
INSERT INTO asg_access.asg_operations
SELECT tenant, tenant || '-T-' || lpad(n::text,4,'0'),
       CASE WHEN n % 2 = 0 THEN 'access' ELSE 'network' END,
       CASE WHEN n % 3 = 0 THEN 'closed' ELSE 'open' END,
       'FICTIONAL validation support record ' || n
FROM (VALUES ('north'),('south')) AS tenants(tenant)
CROSS JOIN generate_series(1,1200) AS numbers(n);
INSERT INTO asg_access.asg_directory
SELECT tenant, tenant || '-E-' || lpad(n::text,3,'0'),
       '가상 직원 ' || tenant || ' ' || lpad(n::text,3,'0'),
       CASE WHEN n % 2 = 0 THEN '운영팀' ELSE '지원팀' END,
       'fictional-' || tenant || '-' || n || '@example.test'
FROM (VALUES ('north'),('south')) AS tenants(tenant)
CROSS JOIN generate_series(1,100) AS numbers(n);
INSERT INTO asg_access.asg_payroll
SELECT 'north', 'north-E-' || lpad(n::text,3,'0'), '운영팀',
       3000000 + n * 10000, 'MOCK-ACCOUNT-' || lpad(n::text,3,'0')
FROM generate_series(1,100) AS numbers(n);
