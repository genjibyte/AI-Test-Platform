"""SQLite-backed ledger store (docs/41 section 3).

One durable table, append-only in P1. Stores the full ``JudgedRecord`` as JSON plus
a few indexed columns for the by-target / by-author / dedup queries (docs/41 section
5). Mirrors the existing ``app/storage/db.py`` pattern; introduces no new tech.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Optional, Union

from app.ledger.models import JudgedRecord

_SCHEMA = """
CREATE TABLE IF NOT EXISTS judged_records (
    record_id        TEXT PRIMARY KEY,
    created_at       TEXT,
    repo_url         TEXT,
    target_class     TEXT,
    target_method    TEXT,
    author_type      TEXT,
    author_id        TEXT,
    test_fingerprint TEXT,
    gen_outcome      TEXT,
    passed           INTEGER,
    failure_type     TEXT,
    conclusion       TEXT,
    record_json      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jr_target ON judged_records(target_class, target_method);
CREATE INDEX IF NOT EXISTS idx_jr_author ON judged_records(author_id);
CREATE INDEX IF NOT EXISTS idx_jr_fingerprint ON judged_records(test_fingerprint);
"""


class LedgerStore:
    """Durable, cross-run ledger of judged candidate tests."""

    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def append(self, record: JudgedRecord) -> None:
        """Insert one record. record_id is the PK; duplicate ids are ignored."""
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO judged_records (record_id, created_at, "
                "repo_url, target_class, target_method, author_type, author_id, "
                "test_fingerprint, gen_outcome, passed, failure_type, conclusion, "
                "record_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    record.record_id,
                    record.created_at,
                    record.repo_url,
                    record.target_class,
                    record.target_method,
                    record.provenance.author_type,
                    record.provenance.author_id,
                    record.test_fingerprint,
                    record.gen_outcome,
                    None if record.passed is None else int(record.passed),
                    record.failure_type,
                    record.conclusion,
                    record.model_dump_json(),
                ),
            )

    def _rows(self, where: str = "", params: tuple = ()) -> List[JudgedRecord]:
        sql = "SELECT record_json FROM judged_records"
        if where:
            sql += f" WHERE {where}"
        sql += " ORDER BY created_at"
        with self._connect() as conn:
            return [
                JudgedRecord.model_validate_json(r["record_json"])
                for r in conn.execute(sql, params)
            ]

    def all(self) -> List[JudgedRecord]:
        return self._rows()

    def count(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM judged_records").fetchone()[0]

    def by_target(
        self, target_class: str, target_method: Optional[str] = None
    ) -> List[JudgedRecord]:
        if target_method is None:
            return self._rows("target_class = ?", (target_class,))
        return self._rows(
            "target_class = ? AND target_method = ?", (target_class, target_method)
        )

    def by_author(self, author_id: str) -> List[JudgedRecord]:
        return self._rows("author_id = ?", (author_id,))

    def by_fingerprint(self, test_fingerprint: str) -> List[JudgedRecord]:
        return self._rows("test_fingerprint = ?", (test_fingerprint,))
