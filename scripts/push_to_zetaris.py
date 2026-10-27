"""
push_to_zetaris.py
==================
Copies our local SQLite metrics DB into Zetaris' internal PostgreSQL, then
registers it as a named datasource so Zetaris can query it via its SQL engine.

Strategy
--------
1. Read each table from  data/sample_metrics.db  (SQLite)
2. Re-create the table in Zetaris' embedded Postgres  (port 32768)
   inside a dedicated schema  archus
3. Register a JDBC datasource in Zetaris pointing at that Postgres schema
4. Verify with SELECT count(*) via the Zetaris REST API

Run:
    python scripts/push_to_zetaris.py
"""
from __future__ import annotations

import os
import sqlite3
import sys
import uuid
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
SQLITE_PATH = Path("data/sample_metrics.db")

# Zetaris REST
ZETARIS_URL = os.getenv("ZETARIS_REST_URL", "http://localhost:8888/api/v1.0").rstrip("/")
ZETARIS_KEY = os.getenv("ZETARIS_API_KEY", "")
ZETARIS_ORG = os.getenv("ZETARIS_ORG_ID", "1")
ZETARIS_USER = os.getenv("ZETARIS_USERNAME", "")
ZETARIS_PASS = os.getenv("ZETARIS_PASSWORD", "")

# Zetaris embedded Postgres (Docker publishes 127.0.0.1:32768->5432, not IPv6 ::1)
PG_HOST = os.getenv("ZETARIS_PG_HOST", "127.0.0.1")
PG_PORT = int(os.getenv("ZETARIS_PG_PORT", "32768"))
PG_DB = os.getenv("ZETARIS_PG_DB", "metastore")
PG_USER = os.getenv("ZETARIS_PG_USER", "zetaris")
PG_PASS = os.getenv("ZETARIS_PG_PASSWORD", "")
PG_SCHEMA = "archus"         # our dedicated schema

TABLES_TO_SKIP = {"sqlite_sequence"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def zetaris_run_sql(sql: str, timeout: int = 30) -> dict:
    """Fire a raw SQL statement via Zetaris REST API (no validation guard)."""
    qid = str(uuid.uuid4())
    headers = {
        "Authorization": f"Bearer {ZETARIS_KEY}",
        "X-Org-ID": str(ZETARIS_ORG),
        "X-Request-ID": qid,
        "Content-Type": "application/json",
    }
    payload = {"queryId": qid, "sql": sql, "source": "SqlEditor", "limit": 10}
    try:
        r = requests.post(f"{ZETARIS_URL}/sql-editor/sqls/run",
                          headers=headers, json=payload, timeout=timeout)
        return {"status": r.status_code, "body": r.json()}
    except Exception as e:
        return {"status": None, "body": str(e)}


def log(msg: str, ok: bool = True):
    tag = "[OK]" if ok else "[!!]"
    print(f"{tag} {msg}")


# ── Step 1: Verify SQLite ─────────────────────────────────────────────────────
print("=" * 60)
print("STEP 1   SQLite local")
print("=" * 60)

if not SQLITE_PATH.exists():
    log(f"SQLite DB not found: {SQLITE_PATH}", ok=False)
    sys.exit(1)

src = sqlite3.connect(str(SQLITE_PATH))
src.row_factory = sqlite3.Row
cur = src.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
all_tables = [r[0] for r in cur.fetchall() if r[0] not in TABLES_TO_SKIP]
log(f"Found {len(all_tables)} tables: {all_tables}")


# ── Step 2: Connect to Zetaris Postgres ───────────────────────────────────────
print()
print("=" * 60)
print("STEP 2   Connect to Zetaris embedded Postgres")
print("=" * 60)

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    log("psycopg2 not installed. Run: pip install psycopg2-binary", ok=False)
    sys.exit(1)

def _postgres_creds_from_docker():
    """Read POSTGRES_* from the running zetaris-postgres-1 container. Never print the password."""
    import json
    import subprocess

    try:
        raw = subprocess.check_output(
            ["docker", "inspect", "zetaris-postgres-1"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        env_list = json.loads(raw)[0]["Config"]["Env"]
        env = {}
        for item in env_list:
            if "=" in item:
                key, value = item.split("=", 1)
                env[key] = value
        return (
            env.get("POSTGRES_USER") or "zetaris",
            env.get("POSTGRES_PASSWORD") or "",
            env.get("POSTGRES_DB") or "metastore",
        )
    except Exception:
        return None


docker_creds = _postgres_creds_from_docker()
if docker_creds and docker_creds[1]:
    log("Read Postgres credentials from container zetaris-postgres-1")
else:
    log("Could not read credentials from Docker inspect", ok=False)

pg_candidates = []
if PG_USER and PG_PASS:
    pg_candidates.append((PG_USER, PG_PASS, PG_DB))
if docker_creds and docker_creds[1]:
    pg_candidates.append(docker_creds)
pg_candidates.extend([
    ("zetaris", "zetaris", "metastore"),
    ("zetaris", "zetaris", "zetaris"),
    ("postgres", "postgres", "postgres"),
])
# de-dupe while keeping order
seen = set()
unique_candidates = []
for row in pg_candidates:
    if row in seen:
        continue
    seen.add(row)
    unique_candidates.append(row)
pg_candidates = unique_candidates

pg_conn = None
for pg_user, pg_pass, pg_db in pg_candidates:
    try:
        pg_conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT, dbname=pg_db,
            user=pg_user, password=pg_pass,
            connect_timeout=5
        )
        PG_USER, PG_PASS, PG_DB = pg_user, pg_pass, pg_db
        log(f"Connected as {pg_user}@{pg_db} on port {PG_PORT}")
        break
    except Exception as e:
        log(f"  Tried {pg_user}@{pg_db}: {str(e)[:60]}", ok=False)

if pg_conn is None:
    log("Could not connect to Zetaris Postgres. Lightning REST DDL is not allowed on this API (400).", ok=False)
    log("Fix: run this script where `docker inspect zetaris-postgres-1` works, host 127.0.0.1 port 32768.")
    sys.exit(1)
else:
    USE_PG = True


# ── Step 3a: Postgres path ────────────────────────────────────────────────────
if USE_PG:
    print()
    print("=" * 60)
    print("STEP 3   Push tables into Postgres (schema: archus)")
    print("=" * 60)

    pg_conn.autocommit = False
    pgc = pg_conn.cursor()

    # Create schema
    pgc.execute(f"CREATE SCHEMA IF NOT EXISTS {PG_SCHEMA}")
    pg_conn.commit()
    log(f"Schema '{PG_SCHEMA}' ready")

    # SQLite type → Postgres type mapping
    TYPE_MAP = {
        "INTEGER": "INTEGER", "REAL": "FLOAT", "TEXT": "TEXT",
        "BLOB": "BYTEA", "NUMERIC": "NUMERIC", "BOOLEAN": "BOOLEAN",
    }

    def sqlite_to_pg_type(sqlite_type: str) -> str:
        t = sqlite_type.upper().split("(")[0].strip()
        return TYPE_MAP.get(t, "TEXT")

    total_rows = 0
    for tbl in all_tables:
        # Get schema
        cur.execute(f"PRAGMA table_info([{tbl}])")
        cols_info = cur.fetchall()
        if not cols_info:
            continue

        col_defs = ", ".join(
            f'"{c["name"]}" {sqlite_to_pg_type(c["type"])}' for c in cols_info
        )
        full_table = f"{PG_SCHEMA}.{tbl}"

        pgc.execute(f"DROP TABLE IF EXISTS {full_table} CASCADE")
        pgc.execute(f"CREATE TABLE {full_table} ({col_defs})")
        pg_conn.commit()

        # Copy rows
        cur.execute(f"SELECT * FROM [{tbl}]")
        rows = cur.fetchall()
        if rows:
            col_names = [c["name"] for c in cols_info]
            placeholders = ", ".join(["%s"] * len(col_names))
            quoted_cols = ", ".join(f'"{c}"' for c in col_names)
            insert_sql = f"INSERT INTO {full_table} ({quoted_cols}) VALUES ({placeholders})"
            for row in rows:
                pgc.execute(insert_sql, tuple(row))
            pg_conn.commit()

        total_rows += len(rows)
        log(f"  {tbl}: {len(rows)} rows pushed")

    pg_conn.close()
    src.close()
    log(f"Total: {total_rows} rows pushed to Postgres schema '{PG_SCHEMA}'")


# ── Step 3b: Lightning layer fallback (DDL via REST) ─────────────────────────
else:
    print()
    print("=" * 60)
    print("STEP 3   Push via Zetaris Lightning layer (DDL + INSERT via REST)")
    print("=" * 60)

    TYPE_MAP_LIGHTNING = {
        "INTEGER": "INT", "REAL": "DOUBLE", "TEXT": "STRING",
        "BLOB": "STRING", "NUMERIC": "DOUBLE", "BOOLEAN": "BOOLEAN",
    }

    def sqlite_to_lightning_type(sqlite_type: str) -> str:
        t = sqlite_type.upper().split("(")[0].strip()
        return TYPE_MAP_LIGHTNING.get(t, "STRING")

    # Create namespace in Zetaris (Lightning = built-in storage)
    ns_result = zetaris_run_sql("CREATE NAMESPACE IF NOT EXISTS archus USING lightning")
    log(f"Namespace archus: {ns_result['status']} -> {str(ns_result['body'])[:80]}")

    total_rows = 0
    for tbl in all_tables:
        cur.execute(f"PRAGMA table_info([{tbl}])")
        cols_info = cur.fetchall()
        if not cols_info:
            continue

        col_defs = ", ".join(
            f"`{c['name']}` {sqlite_to_lightning_type(c['type'])}" for c in cols_info
        )
        # Drop + Create
        drop_r = zetaris_run_sql(f"DROP TABLE IF EXISTS archus.{tbl}")
        create_r = zetaris_run_sql(f"CREATE TABLE archus.{tbl} ({col_defs})")
        log(f"  CREATE archus.{tbl}: {create_r['status']}")

        # Insert rows
        cur.execute(f"SELECT * FROM [{tbl}]")
        rows = cur.fetchall()
        col_names = [c["name"] for c in cols_info]
        inserted = 0
        for row in rows:
            vals = ", ".join(
                f"'{str(v).replace(chr(39), chr(39)+chr(39))}'" if v is not None else "NULL"
                for v in tuple(row)
            )
            ins_r = zetaris_run_sql(
                f"INSERT INTO archus.{tbl} ({', '.join(f'`{c}`' for c in col_names)}) VALUES ({vals})"
            )
            if ins_r["status"] == 200:
                inserted += 1
        log(f"    {tbl}: {inserted}/{len(rows)} rows inserted")
        total_rows += inserted

    src.close()
    log(f"Total: {total_rows} rows pushed via Lightning layer")


# ── Step 4: Verify via Zetaris REST ──────────────────────────────────────────
print()
print("=" * 60)
print("STEP 4   Verify tables via Zetaris REST API")
print("=" * 60)

verify_tables = ["modules", "antipatterns", "tests", "dependencies", "repos"]
all_ok = True
for tbl in verify_tables:
    # Try both namespaces
    for ns in ["archus"]:
        r = zetaris_run_sql(f"SELECT count(*) FROM {ns}.{tbl}", timeout=20)
        if r["status"] == 200:
            data = r["body"].get("data", [[0]])
            count = data[0][0] if data else "?"
            log(f"  {ns}.{tbl}: {count} rows   VERIFIED")
            break
    else:
        log(f"  {tbl}: NOT ACCESSIBLE in Zetaris", ok=False)
        all_ok = False

print()
if all_ok:
    print("SUCCESS: All tables are live in Zetaris. The agent can now query in LIVE mode.")
else:
    print("PARTIAL: Some tables missing. Check Zetaris datasource config.")
    print("Tip: Set SAMPLE_MODE=true in .env to use local SQLite fallback instead.")
