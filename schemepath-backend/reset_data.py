#!/usr/bin/env python3
"""
reset_data.py — Wipe ALL Neo4j data then re-seed from scratch.

Usage:
    python reset_data.py          # prompts for confirmation
    python reset_data.py --yes    # non-interactive (CI / scripting)

⚠  This permanently deletes every node and relationship in the database.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# ── Allow running from the schemepath-backend/ directory ──────────────────────
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from app.config import get_settings
from neo4j import GraphDatabase
from neo4j.exceptions import AuthError, ServiceUnavailable

# Import seed logic so we share the same connection code
import seed_data as _seed

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("reset")

BANNER = """
╔══════════════════════════════════════════════════════════╗
║          ⚠   DESTRUCTIVE OPERATION WARNING   ⚠          ║
║                                                          ║
║  This will permanently delete ALL nodes, relationships,  ║
║  and data in your Neo4j database, then re-seed it.       ║
║                                                          ║
║  This action CANNOT be undone.                           ║
╚══════════════════════════════════════════════════════════╝
"""


def confirm_interactive() -> bool:
    """Prompt the user to type 'yes' to confirm."""
    print(BANNER)
    answer = input("  → Type 'yes' to confirm, anything else to abort: ").strip().lower()
    return answer == "yes"


def wipe_database(driver) -> int:
    """Delete all nodes and relationships. Returns deleted node count."""
    with driver.session() as session:
        result = session.run("MATCH (n) DETACH DELETE n RETURN count(n) AS deleted")
        record = result.single()
        return record["deleted"] if record else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="⚠  Wipe all Neo4j data and re-seed from scratch."
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip interactive confirmation (use in CI / scripts).",
    )
    args = parser.parse_args()

    # ── Confirmation ──────────────────────────────────────────────────────────
    if args.yes:
        log.warning("--yes flag provided. Skipping confirmation prompt.")
        confirmed = True
    else:
        confirmed = confirm_interactive()

    if not confirmed:
        log.info("Aborted. No data was deleted.")
        return 0

    # ── Load config & connect ─────────────────────────────────────────────────
    try:
        settings = get_settings()
    except Exception as exc:
        log.error("Configuration error: %s", exc)
        return 1

    log.info("Connecting to Neo4j at %s …", settings.NEO4J_URI)
    driver = _seed.get_driver(settings)

    try:
        if not _seed.verify_connection(driver):
            return 1

        # ── Node count before wipe ────────────────────────────────────────────
        with driver.session() as session:
            before = session.run("MATCH (n) RETURN count(n) AS n").single()["n"]
        log.info("Database currently has %d node(s).", before)

        # ── Wipe ──────────────────────────────────────────────────────────────
        log.info("Deleting all data …")
        deleted = wipe_database(driver)
        log.info("✅ Deleted %d node(s) (all relationships removed too).", deleted)

        # ── Verify empty ──────────────────────────────────────────────────────
        with driver.session() as session:
            after = session.run("MATCH (n) RETURN count(n) AS n").single()["n"]
        if after != 0:
            log.warning("⚠  %d node(s) still remain after wipe. Proceeding anyway.", after)

    finally:
        driver.close()

    # ── Re-seed ───────────────────────────────────────────────────────────────
    log.info("Re-seeding database …")
    exit_code = _seed.main(force=True)

    if exit_code == 0:
        log.info("🎉 Reset complete. Database is fresh and seeded.")
    else:
        log.error("❌ Seeding failed after wipe. Check errors above.")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
