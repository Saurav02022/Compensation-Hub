"""The SQL validator, exercised on parsed queries without a database."""

import pytest

from compensation_hub.ask_compensation.sql_validation import (
    MAX_CTES,
    MAX_JOINS,
    MAX_NESTING,
    MAX_ROWS,
    ForbiddenSqlError,
    InvalidSqlError,
    UnknownReferenceError,
    validate_sql,
)


def units(sql: str, percent: frozenset[str] = frozenset()) -> list[tuple[str, str]]:
    return [(column.name, column.unit) for column in validate_sql(sql, percent).columns]


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT full_name FROM employees LIMIT 5",
        "SELECT COUNT(*) AS n FROM employees WHERE salary_usd > 100000 AND country = 'India'",
        "SELECT COUNT(*) AS n FROM employees WHERE country = 'India' OR department = 'Sales'",
        "SELECT COUNT(*) AS n FROM employees WHERE NOT (country IN ('India', 'Germany'))",
        "SELECT full_name FROM employees WHERE full_name ILIKE '%patel%' LIMIT 10",
        "SELECT full_name FROM employees WHERE employee_code LIKE 'EMP0001%' LIMIT 10",
        "SELECT COUNT(*) AS n FROM employees WHERE salary_usd BETWEEN 50000 AND 60000",
        "SELECT COUNT(*) AS n FROM employees WHERE salary_usd IS NULL",
        "SELECT department, SUM(salary_usd) AS payroll FROM employees GROUP BY department "
        "HAVING COUNT(*) > 500 ORDER BY payroll DESC",
        "SELECT DISTINCT salary_currency FROM employees",
        "SELECT COUNT(DISTINCT job_title) AS titles FROM employees",
        "SELECT CASE WHEN salary_usd > 100000 THEN 'high' ELSE 'other' END AS band, "
        "COUNT(*) AS n FROM employees GROUP BY 1",
        "SELECT MAX(salary_usd) - MIN(salary_usd) AS gap FROM employees",
        "WITH d AS (SELECT department, AVG(salary_usd) AS average FROM employees "
        "GROUP BY department) SELECT e.full_name, e.salary_usd FROM employees AS e "
        "JOIN d ON d.department = e.department WHERE e.salary_usd > d.average LIMIT 10",
        "SELECT full_name FROM employees AS e WHERE salary_usd > (SELECT AVG(salary_usd) "
        "FROM employees AS x WHERE x.department = e.department) LIMIT 10",
        "SELECT country, full_name, RANK() OVER (PARTITION BY country ORDER BY salary_usd DESC) "
        "AS rank_in_country FROM employees LIMIT 20",
        "SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary_usd) AS median FROM employees",
        "SELECT PERCENTILE_DISC(0.9) WITHIN GROUP (ORDER BY salary_usd) AS p90 FROM employees",
        "SELECT SUM(salary_usd) FILTER (WHERE department = 'Engineering') AS eng FROM employees",
        "SELECT country FROM employees WHERE department = 'Sales' UNION "
        "SELECT country FROM employees WHERE department = 'Legal'",
        "SELECT COUNT(*) AS n FROM employees WHERE EXISTS "
        "(SELECT 1 FROM fx_rates WHERE currency_code = salary_currency)",
        "SELECT COUNT(*) AS n FROM employees WHERE salary_usd > 5000000 * "
        "(SELECT rate_to_usd FROM fx_rates WHERE currency_code = 'INR')",
        "select Full_Name from EMPLOYEES limit 3",
        'SELECT "full_name" FROM "employees" LIMIT 3',
    ],
)
def test_accepts_read_only_relational_queries(sql: str) -> None:
    validated = validate_sql(sql)

    assert validated.executable.startswith("WITH employees AS NOT MATERIALIZED (")
    assert "public.employees" in validated.executable
    assert validated.columns


def test_joins_between_approved_relations_are_allowed() -> None:
    sql = (
        "SELECT e.full_name, f.rate_to_usd FROM employees AS e "
        "JOIN fx_rates AS f ON f.currency_code = e.salary_currency LIMIT 5"
    )

    assert units(sql) == [("full_name", "text"), ("rate_to_usd", "rate")]


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1; DELETE FROM employees",
        "SELECT 1; SELECT 2",
        "INSERT INTO employees (full_name) VALUES ('x')",
        "UPDATE compensation SET annual_salary = 0",
        "DELETE FROM employees",
        "MERGE INTO employees USING fx_rates ON true WHEN MATCHED THEN DELETE",
        "CREATE TABLE x (a int)",
        "ALTER TABLE employees ADD COLUMN gender text",
        "DROP TABLE employees",
        "TRUNCATE employees",
        "COPY employees TO '/tmp/out.csv'",
        "COPY (SELECT 1) TO PROGRAM 'id'",
        "CALL refresh()",
        "DO $$ BEGIN PERFORM 1; END $$",
        "SET search_path TO public",
        "SET ROLE postgres",
        "BEGIN",
        "COMMIT",
        "ROLLBACK",
        "GRANT SELECT ON employees TO public",
        "REVOKE SELECT ON employees FROM public",
        "VACUUM employees",
        "ANALYZE employees",
        "EXPLAIN SELECT 1",
        "SELECT * INTO copied FROM employees",
        "SELECT full_name FROM employees FOR UPDATE",
        "SELECT * FROM pg_catalog.pg_user",
        "SELECT * FROM pg_user",
        "SELECT * FROM pg_shadow",
        "SELECT * FROM information_schema.tables",
        "SELECT * FROM public.compensation",
        'SELECT * FROM "public"."employees"',
        'SELECT * FROM "PG_USER"',
        "SELECT pg_sleep(10)",
        "SELECT pg_read_file('/etc/passwd')",
        "SELECT pg_advisory_lock(1)",
        "SELECT set_config('statement_timeout', '0', false)",
        "SELECT current_setting('data_directory')",
        "SELECT 1 /* hidden */ ; DROP TABLE employees",
        "SELECT 1 -- comment\n; DROP TABLE employees",
        "WITH d AS (DELETE FROM employees RETURNING *) SELECT * FROM d",
        "WITH d AS (UPDATE compensation SET annual_salary = 0 RETURNING *) SELECT 1 FROM d",
        "SELECT query_to_xml('DELETE FROM employees', true, true, '')",
        "SELECT dblink_exec('dbname=x', 'DROP TABLE employees')",
        "SELECT version()",
        "SELECT current_user",
        "SELECT current_database()",
        "SELECT inet_server_addr()",
        "SELECT * FROM compensation",
        "SELECT * FROM alembic_version",
        "SELECT * FROM information_schema.columns",
        "select * from PG_CATALOG.pg_roles",
    ],
)
def test_rejects_anything_that_is_not_a_read_of_the_surface(sql: str) -> None:
    with pytest.raises(ForbiddenSqlError):
        validate_sql(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT lo_import('/etc/passwd')",
        "SELECT nextval('employees_id_seq')",
        "SELECT now()",
        "SELECT LENGTH(full_name) AS n FROM employees LIMIT 1",
        "SELECT CONCAT(full_name, country) AS label FROM employees LIMIT 1",
        "SELECT full_name || ' ' || country AS label FROM employees LIMIT 1",
        "SELECT generate_series(1, 10)",
        "SELECT * FROM generate_series(1, 10)",
        "SELECT query_to_xml('select 1', true, true, '')",
        "SELECT md5(full_name) FROM employees LIMIT 1",
        "SELECT string_agg(full_name, ',') FROM employees",
        "SELECT CAST(salary_usd AS DOUBLE PRECISION) FROM employees LIMIT 1",
        "SELECT salary_usd::float FROM employees LIMIT 1",
        "WITH RECURSIVE r AS (SELECT 1 AS n UNION ALL SELECT n + 1 FROM r) SELECT n FROM r",
        "SELECT full_name FROM employees, LATERAL (SELECT 1) AS x LIMIT 1",
        "SELECT salary_usd % 2 FROM employees LIMIT 1",
        'SELECT full_name AS "100%" FROM employees LIMIT 1',
        "WITH employees AS (SELECT 1 AS a) SELECT a FROM employees",
        "SELECT $1",
    ],
)
def test_rejects_functions_and_constructs_outside_the_allowlist(sql: str) -> None:
    with pytest.raises(InvalidSqlError):
        validate_sql(sql)


def test_unknown_columns_and_relations_are_reported_by_name() -> None:
    with pytest.raises(UnknownReferenceError) as column:
        validate_sql("SELECT gender, COUNT(*) FROM employees GROUP BY gender")
    with pytest.raises(UnknownReferenceError) as relation:
        validate_sql("SELECT AVG(amount) FROM bonuses")
    with pytest.raises(UnknownReferenceError):
        validate_sql('SELECT full_name FROM "Employees" LIMIT 1')

    assert column.value.names == ["gender"]
    assert relation.value.names == ["bonuses"]


@pytest.mark.parametrize(
    ("sql", "message"),
    [
        ("SELECT SUM(salary_local) FROM employees", "salary_local"),
        ("SELECT AVG(salary_local) AS a FROM employees GROUP BY salary_currency", "salary_local"),
        ("SELECT salary_local * 2 AS doubled, salary_currency FROM employees", "salary_local"),
        (
            "SELECT RANK() OVER (ORDER BY salary_local) AS r, salary_currency FROM employees",
            "salary_local",
        ),
        ("SELECT full_name, salary_local FROM employees LIMIT 5", "salary_currency"),
        ("SELECT SUM(salary_usd * salary_usd) AS x FROM employees", "Multiplying two amounts"),
        ("SELECT COUNT(*) + SUM(salary_usd) AS x FROM employees", "Cannot add or subtract"),
        ("SELECT COUNT(*) / SUM(salary_usd) AS x FROM employees", "Dividing a count"),
        (
            "SELECT SUM(e.salary_usd / f.rate_to_usd) AS inr FROM employees AS e "
            "JOIN fx_rates AS f ON f.currency_code = 'INR'",
            "stay in USD",
        ),
        (
            "SELECT CASE WHEN country = 'India' THEN salary_usd ELSE COUNT(*) END AS x "
            "FROM employees GROUP BY country, salary_usd",
            "CASE",
        ),
        (
            "SELECT SUM(e.salary_usd * (f.rate_to_usd * 1)) AS x FROM employees AS e "
            "JOIN fx_rates AS f ON f.currency_code = 'EUR'",
            "stay in USD",
        ),
        (
            "SELECT SUM(e.salary_usd) * MAX(f.rate_to_usd) / MIN(f.rate_to_usd) AS x "
            "FROM employees AS e CROSS JOIN fx_rates AS f",
            "stay in USD",
        ),
        (
            "SELECT SUM((SELECT salary_local FROM employees LIMIT 1)) AS x FROM employees",
            "salary_local",
        ),
        (
            "WITH l AS (SELECT salary_local AS amount FROM employees) "
            "SELECT SUM(amount) AS x FROM l",
            "salary_local",
        ),
        ("SELECT currency_code, rate_to_usd * 100 AS scaled FROM fx_rates", None),
        ("SELECT full_name FROM employees", None),
    ],
)
def test_money_rules(sql: str, message: str | None) -> None:
    if message is None:
        validate_sql(sql)
        return
    with pytest.raises(InvalidSqlError, match=message):
        validate_sql(sql)


def test_units_are_inferred_through_ctes_subqueries_and_windows() -> None:
    sql = (
        "WITH d AS (SELECT department, AVG(salary_usd) AS avg_pay, COUNT(*) AS headcount "
        "FROM employees GROUP BY department) "
        "SELECT d.department, d.avg_pay, d.headcount, d.avg_pay / d.headcount AS per_head, "
        "(SELECT MAX(salary_usd) FROM employees) AS top, "
        "d.headcount * 100.0 / (SELECT COUNT(*) FROM employees) AS share, "
        "SUM(d.avg_pay) OVER () / d.avg_pay AS ratio FROM d"
    )

    assert units(sql, frozenset({"share"})) == [
        ("department", "text"),
        ("avg_pay", "money"),
        ("headcount", "count"),
        ("per_head", "money"),
        ("top", "money"),
        ("share", "percent"),
        ("ratio", "number"),
    ]


def test_employee_rows_keep_their_id_and_local_currency() -> None:
    sql = (
        "SELECT employee_id, full_name, salary_local, salary_currency, salary_usd "
        "FROM employees ORDER BY salary_usd DESC LIMIT 5"
    )

    assert units(sql) == [
        ("employee_id", "id"),
        ("full_name", "text"),
        ("salary_local", "money_local"),
        ("salary_currency", "text"),
        ("salary_usd", "money"),
    ]


def test_money_cannot_be_declared_a_percentage() -> None:
    with pytest.raises(InvalidSqlError, match="not a percentage"):
        validate_sql("SELECT SUM(salary_usd) AS total FROM employees", frozenset({"total"}))


def test_row_limits() -> None:
    uncapped = validate_sql("SELECT full_name FROM employees")
    own = validate_sql("SELECT full_name FROM employees LIMIT 7")

    assert uncapped.row_cap == MAX_ROWS
    assert uncapped.executable.endswith(f"LIMIT {MAX_ROWS + 1}")
    assert own.row_cap is None
    assert own.executable.endswith("LIMIT 7")
    at_cap = validate_sql(f"SELECT full_name FROM employees LIMIT {MAX_ROWS}")
    assert at_cap.row_cap == MAX_ROWS
    assert at_cap.executable.endswith(f"LIMIT {MAX_ROWS + 1}")
    with pytest.raises(InvalidSqlError, match="above the maximum"):
        validate_sql(f"SELECT full_name FROM employees LIMIT {MAX_ROWS + 1}")
    with pytest.raises(InvalidSqlError, match="whole number"):
        validate_sql("SELECT full_name FROM employees LIMIT (SELECT 5)")
    with pytest.raises(InvalidSqlError, match="above the maximum"):
        validate_sql("SELECT full_name FROM employees OFFSET 100000")


def test_complexity_bounds() -> None:
    nested = "SELECT COUNT(*) AS n FROM employees"
    for _ in range(MAX_NESTING + 1):
        nested = f"SELECT COUNT(*) AS n FROM ({nested}) AS inner_query"
    ctes = ", ".join(f"c{i} AS (SELECT 1 AS a)" for i in range(MAX_CTES + 1))
    joins = " ".join(
        f"JOIN employees AS e{i} ON e{i}.employee_id = e.employee_id" for i in range(MAX_JOINS + 1)
    )

    with pytest.raises(InvalidSqlError, match="nests more than"):
        validate_sql(nested)
    with pytest.raises(InvalidSqlError, match="CTEs"):
        validate_sql(f"WITH {ctes} SELECT a FROM c0")
    with pytest.raises(InvalidSqlError, match="joins more than"):
        validate_sql(f"SELECT e.full_name FROM employees AS e {joins} LIMIT 1")
    with pytest.raises(InvalidSqlError, match="longer than"):
        validate_sql("SELECT full_name FROM employees WHERE " + "country = 'x' OR " * 400 + "true")


def test_malformed_sql_is_rejected() -> None:
    for sql in ["", "SELEC full_name FROM employees", "SELECT FROM WHERE", "not sql at all ((("]:
        with pytest.raises(InvalidSqlError):
            validate_sql(sql)


def test_executed_sql_is_rebuilt_from_the_tree_with_literals_bound() -> None:
    validated = validate_sql(
        "select full_name from employees -- trailing note\n"
        "where full_name ilike '%o''brien%' and country = 'India' limit 5"
    )

    assert "--" not in validated.executable and "/*" not in validated.executable
    assert "'India'" not in validated.executable
    assert validated.parameters == {"p0": "%o'brien%", "p1": "India"}
    assert "%(p0)s" in validated.executable and "%(p1)s" in validated.executable
    assert "'India'" in validated.sql


def test_medians_are_rewritten_to_exact_numeric_form() -> None:
    validated = validate_sql(
        "SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary_usd) "
        "FILTER (WHERE country = 'India') AS m FROM employees"
    )

    assert "PERCENTILE_CONT" not in validated.sql
    assert validated.sql.count("PERCENTILE_DISC(0.5)") == 2
    assert validated.sql.count("FILTER(WHERE") == 2


def test_divisions_are_exact_and_safe_from_zero() -> None:
    validated = validate_sql("SELECT COUNT(*) / COUNT(salary_usd) AS ratio FROM employees")

    assert "CAST(COUNT(*) AS DECIMAL) / NULLIF(COUNT(employees.salary_usd), 0)" in validated.sql
