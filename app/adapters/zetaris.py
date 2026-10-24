"""
Zetaris Adapter: Executes verified SQL queries via Zetaris REST API.
Includes query validation via SQLGuard, UUID request tracing, and structured error handling.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List
import requests

from ..config import settings
from ..sqlguard import validate_and_sanitize_sql


class ZetarisConnectionError(Exception):
    pass


class ZetarisAdapter:
    def __init__(self):
        self.rest_url = settings.zetaris_rest_url.rstrip("/")
        self.org_id = settings.zetaris_org_id
        self.api_key = settings.zetaris_api_key
        self.timeout = settings.sql_timeout_seconds

    def execute_sql(self, sql_query: str, limit: int = 200) -> List[Dict[str, Any]]:
        """
        Executes a single validated SELECT query on Zetaris via its REST SQL runner.
        """
        sanitized_sql = validate_and_sanitize_sql(sql_query, default_limit=limit)

        url = f"{self.rest_url}/sql-editor/sqls/run"
        query_id = str(uuid.uuid4())
        request_id = str(uuid.uuid4())

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-Org-ID": str(self.org_id),
            "X-Request-ID": request_id,
            "Content-Type": "application/json",
        }

        payload = {
            "queryId": query_id,
            "sql": sanitized_sql,
            "source": "SqlEditor",
            "limit": limit,
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            res_json = resp.json()
            
            # Zetaris typically returns {"data": [[col1_val, col2_val]], "columns": ["col1", "col2"]}
            data = res_json.get("data", [])
            columns = res_json.get("headers") or res_json.get("columns", [])

            if columns and isinstance(data, list) and data and isinstance(data[0], list):
                # Map headers/columns to dicts
                return [dict(zip(columns, row)) for row in data]
            elif isinstance(data, list) and data and isinstance(data[0], dict):
                return data
            else:
                return [{"value": item} for item in data]

        except requests.exceptions.RequestException as exc:
            raise ZetarisConnectionError(f"Zetaris API query failed: {exc}") from exc
