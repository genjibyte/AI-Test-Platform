"""SQLite connection + schema initialization (P1-T02).

Usage::

    python -m app.storage.db --init
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional, Union

from app.config import get_settings

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def get_connection(db_path: Optional[Union[str, Path]] = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else get_settings().db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Optional[Union[str, Path]] = None) -> None:
    conn = get_connection(db_path)
    try:
        with conn:
            conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    finally:
        conn.close()


def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="TestAgent SQLite tools")
    parser.add_argument("--init", action="store_true", help="create tables")
    args = parser.parse_args()
    if args.init:
        init_db()
        print(f"db initialized at {get_settings().db_path}")
    else:
        parser.print_help()


if __name__ == "__main__":
    _main()
