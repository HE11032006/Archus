"""
SQLGuard: Validates and sanitizes SQL queries before execution on Zetaris or SQLite.
Ensures read-only safety, table whitelisting, and bounds (LIMIT enforcement).
"""

from __future__ import annotations

import re
from typing import Set
import sqlglot
from sqlglot import exp

ALLOWED_TABLES: Set[str] = {
    "repos",
    "modules",
    "antipatterns",
    "dependencies",
    "hotspots",
    "tests",
    "architecture",
    "performance",
    "rules",
    "decision_records",
}


class SQLSecurityError(ValueError):
    """Raised when a SQL query violates safety constraints."""
    pass


def validate_and_sanitize_sql(
    sql_text: str,
    default_limit: int = 200,
    max_limit: int = 1000
) -> str:
    """
    Validates that the SQL text is a single read-only SELECT statement,
    targets only allowed tables, and enforces a safe LIMIT.
    """
    clean_sql = sql_text.strip()
    if not clean_sql:
        raise SQLSecurityError("Empty SQL query provided.")

    # Disallow chained statements separated by semicolons
    statements = [s.strip() for s in clean_sql.split(";") if s.strip()]
    if len(statements) > 1:
        raise SQLSecurityError("Multiple statements are forbidden. Only single queries are allowed.")
    single_stmt_sql = statements[0]

    # Parse with sqlglot
    try:
        parsed = sqlglot.parse_one(single_stmt_sql)
    except Exception as e:
        raise SQLSecurityError(f"SQL parsing failed: {e}")

    # Must be a Select expression
    if not isinstance(parsed, exp.Select):
        raise SQLSecurityError(f"Only SELECT queries are allowed. Received: {parsed.key.upper() if parsed else 'UNKNOWN'}")

    # Inspect all referenced tables
    tables = [table.name.lower() for table in parsed.find_all(exp.Table)]
    for table_name in tables:
        if table_name not in ALLOWED_TABLES:
            raise SQLSecurityError(
                f"Unauthorized table access: '{table_name}'. Allowed tables: {sorted(list(ALLOWED_TABLES))}"
            )

    # Check LIMIT
    limit_exp = parsed.args.get("limit")
    if limit_exp is None:
        # Append default limit
        parsed = parsed.limit(default_limit)
    else:
        try:
            current_limit = int(limit_exp.this.name)
            if current_limit > max_limit:
                parsed = parsed.limit(max_limit)
        except Exception:
            parsed = parsed.limit(default_limit)

    return parsed.sql()
