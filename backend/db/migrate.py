"""
Forward-only SQL migration runner.

Applies numbered .sql scripts from db/migrations/ in order, tracking
which have already run in a __schema_versions table.  Inspired by DbUp.

Usage:
    uv run python -m db.migrate            # apply pending migrations
    uv run python -m db.migrate --status   # list applied / pending

Environment:
    DATABASE_URL   – SQLAlchemy-style connection string (required)
"""

import os
import re
import sys
import time
import logging
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-5.5s [migrate] %(message)s",
)
log = logging.getLogger("migrate")

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SCRIPT_RE = re.compile(r"^(\d{3})_.+\.sql$")


def _discover_scripts() -> list[tuple[int, Path]]:
    """Return sorted list of (sequence_number, path) for every .sql file."""
    scripts = []
    for f in sorted(MIGRATIONS_DIR.iterdir()):
        m = _SCRIPT_RE.match(f.name)
        if m:
            scripts.append((int(m.group(1)), f))
    return scripts


def _ensure_versions_table(conn) -> None:
    conn.execute(
        text("""
        CREATE TABLE IF NOT EXISTS __schema_versions (
            id SERIAL PRIMARY KEY,
            script_name VARCHAR NOT NULL UNIQUE,
            applied_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    )
    conn.commit()


def _applied_scripts(conn) -> set[str]:
    rows = conn.execute(
        text("SELECT script_name FROM __schema_versions ORDER BY id")
    ).fetchall()
    return {r[0] for r in rows}


def _apply(conn, script_path: Path) -> None:
    sql = script_path.read_text()
    conn.execute(text(sql))
    conn.execute(
        text("INSERT INTO __schema_versions (script_name) VALUES (:name)"),
        {"name": script_path.name},
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def migrate(engine) -> int:
    """Apply all pending migrations. Returns count of scripts applied."""
    # Skip SQL migrations for in-memory/SQLite test databases — the test
    # fixtures set up the schema via SQLModel.metadata.create_all() instead.
    if engine.dialect.name == "sqlite":
        log.info("SQLite detected — skipping SQL migrations (test mode).")
        return 0

    scripts = _discover_scripts()
    if not scripts:
        log.warning("No migration scripts found in %s", MIGRATIONS_DIR)
        return 0

    applied = 0
    with engine.connect() as conn:
        _ensure_versions_table(conn)
        already = _applied_scripts(conn)

        for seq, path in scripts:
            if path.name in already:
                continue
            log.info("Applying %s ...", path.name)
            t0 = time.monotonic()
            try:
                _apply(conn, path)
            except Exception as e:
                log.error("Failed to apply %s: %s", path.name, e)
                conn.rollback()
                raise
            elapsed = time.monotonic() - t0
            log.info("  done (%.1fs)", elapsed)
            applied += 1

    if applied == 0:
        log.info("Database is up to date.")
    else:
        log.info("Applied %d migration(s).", applied)
    return applied


def status(engine) -> None:
    """Print which scripts have been applied and which are pending."""
    scripts = _discover_scripts()
    with engine.connect() as conn:
        _ensure_versions_table(conn)
        already = _applied_scripts(conn)

    for _, path in scripts:
        marker = "applied" if path.name in already else "PENDING"
        print(f"  [{marker:>7s}]  {path.name}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        log.error("DATABASE_URL environment variable is not set.")
        sys.exit(1)

    engine = create_engine(db_url, echo=False)

    if "--status" in sys.argv:
        status(engine)
    else:
        migrate(engine)


if __name__ == "__main__":
    main()
