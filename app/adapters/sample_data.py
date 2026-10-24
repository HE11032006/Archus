"""
Sample Data Adapter: Local SQLite database providing realistic metrics for SAMPLE_MODE.
Allows complete testing without credentials or active Zetaris instances.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List
from ..config import settings
from ..sqlguard import validate_and_sanitize_sql


class SampleDataAdapter:
    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or (settings.data_dir / "sample_metrics.db")
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Repos
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS repos (
                repo_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                language TEXT NOT NULL,
                license TEXT,
                commit_count INTEGER
            )
            """)

            # 2. Modules
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS modules (
                repo_id TEXT,
                module_path TEXT,
                loc INTEGER,
                function_count INTEGER,
                class_count INTEGER,
                complexity_avg REAL,
                complexity_max REAL,
                coupling_score REAL,
                cohesion_score REAL,
                PRIMARY KEY (repo_id, module_path)
            )
            """)

            # 3. Antipatterns
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS antipatterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id TEXT,
                module_path TEXT,
                pattern TEXT,
                file TEXT,
                severity TEXT,
                value REAL
            )
            """)

            # 4. Dependencies
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS dependencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id TEXT,
                name TEXT,
                version TEXT,
                latest_version TEXT,
                is_outdated INTEGER
            )
            """)

            # 5. Hotspots (Anonymized: no author info)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS hotspots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id TEXT,
                module_path TEXT,
                file TEXT,
                change_count INTEGER,
                fix_count INTEGER
            )
            """)

            # 6. Tests
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tests (
                repo_id TEXT,
                module_path TEXT,
                test_file_count INTEGER,
                test_loc INTEGER,
                coverage_estimate REAL,
                coverage_is_estimate INTEGER DEFAULT 1,
                PRIMARY KEY (repo_id, module_path)
            )
            """)

            # 7. Architecture
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS architecture (
                repo_id TEXT PRIMARY KEY,
                style TEXT,
                evidence TEXT
            )
            """)

            # 8. Performance
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance (
                repo_id TEXT,
                module_path TEXT,
                endpoint_count INTEGER,
                external_calls INTEGER,
                n_plus_one_suspects INTEGER,
                has_cache INTEGER,
                PRIMARY KEY (repo_id, module_path)
            )
            """)

            # 9. Rules (standard thresholds)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS rules (
                rule_id TEXT PRIMARY KEY,
                metric TEXT,
                operator TEXT,
                threshold REAL,
                severity TEXT,
                source TEXT
            )
            """)

            # Check if seeding is needed
            cursor.execute("SELECT count(*) FROM repos")
            if cursor.fetchone()[0] == 0:
                self._seed_sample_data(cursor)
            conn.commit()

    def _seed_sample_data(self, cursor: sqlite3.Cursor) -> None:
        # Repos
        cursor.execute("""
        INSERT INTO repos (repo_id, name, language, license, commit_count)
        VALUES 
            ('django_app', 'Django Sample Web App', 'Python', 'MIT', 142),
            ('legacy_service', 'Legacy Monolithic Service', 'Python', 'Proprietary', 890),
            ('sparse_repo', 'Undocumented Sparse Repo', 'Python', 'Unknown', 4)
        """)

        # Modules
        # django_app: auth (moderate debt, good tests -> Refactor)
        # legacy_service: billing (extreme debt, low cohesion, high coupling, zero tests -> Migrate)
        # sparse_repo: mystery_module (empty metrics -> Insufficient Evidence / Abstain)
        cursor.execute("""
        INSERT INTO modules (repo_id, module_path, loc, function_count, class_count, complexity_avg, complexity_max, coupling_score, cohesion_score)
        VALUES 
            ('django_app', 'accounts', 1450, 42, 6, 4.2, 14.0, 3.8, 0.72),
            ('django_app', 'blog', 980, 28, 4, 2.5, 7.0, 1.9, 0.85),
            ('legacy_service', 'billing', 8400, 194, 28, 12.8, 48.0, 9.4, 0.21),
            ('legacy_service', 'notifications', 1200, 31, 5, 3.1, 8.0, 2.6, 0.78),
            ('sparse_repo', 'mystery', 80, 2, 0, 1.0, 1.0, 0.5, 0.50)
        """)

        # Antipatterns
        cursor.execute("""
        INSERT INTO antipatterns (repo_id, module_path, pattern, file, severity, value)
        VALUES
            ('django_app', 'accounts', 'long_method', 'accounts/views.py', 'medium', 65.0),
            ('django_app', 'accounts', 'long_params', 'accounts/forms.py', 'low', 7.0),
            ('legacy_service', 'billing', 'god_class', 'billing/engine.py', 'high', 1400.0),
            ('legacy_service', 'billing', 'long_method', 'billing/engine.py', 'high', 180.0),
            ('legacy_service', 'billing', 'high_coupling', 'billing/processor.py', 'high', 18.0)
        """)

        # Dependencies
        cursor.execute("""
        INSERT INTO dependencies (repo_id, name, version, latest_version, is_outdated)
        VALUES
            ('django_app', 'django', '4.2.10', '5.1.0', 1),
            ('django_app', 'psycopg2-binary', '2.9.9', '2.9.9', 0),
            ('legacy_service', 'django', '1.11.29', '5.1.0', 1),
            ('legacy_service', 'celery', '3.1.25', '5.3.6', 1),
            ('legacy_service', 'requests', '2.18.4', '2.32.0', 1)
        """)

        # Hotspots (Git changes/fixes without personal identities)
        cursor.execute("""
        INSERT INTO hotspots (repo_id, module_path, file, change_count, fix_count)
        VALUES
            ('django_app', 'accounts', 'accounts/views.py', 24, 7),
            ('legacy_service', 'billing', 'billing/engine.py', 114, 52),
            ('legacy_service', 'billing', 'billing/processor.py', 89, 38)
        """)

        # Tests
        cursor.execute("""
        INSERT INTO tests (repo_id, module_path, test_file_count, test_loc, coverage_estimate, coverage_is_estimate)
        VALUES
            ('django_app', 'accounts', 3, 310, 68.5, 1),
            ('django_app', 'blog', 2, 180, 82.0, 1),
            ('legacy_service', 'billing', 0, 0, 0.0, 1),
            ('legacy_service', 'notifications', 1, 95, 45.0, 1),
            ('sparse_repo', 'mystery', 0, 0, 0.0, 1)
        """)

        # Rules / Thresholds
        cursor.execute("""
        INSERT INTO rules (rule_id, metric, operator, threshold, severity, source)
        VALUES
            ('R1', 'complexity_max', '>', 25.0, 'high', 'patterns.py standard threshold'),
            ('R2', 'god_class_loc', '>', 800.0, 'high', 'patterns.py God Class limit'),
            ('R3', 'coupling_score', '>', 7.0, 'high', 'coupling_score ceiling'),
            ('R4', 'coverage_estimate', '<', 30.0, 'medium', 'testing minimal requirement'),
            ('R5', 'outdated_dependencies_ratio', '>', 0.5, 'high', 'security maintenance threshold')
        """)

    def execute_sql(self, sql_query: str) -> List[Dict[str, Any]]:
        sanitized = validate_and_sanitize_sql(sql_query)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sanitized)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
