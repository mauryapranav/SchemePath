#!/usr/bin/env python3
"""
seed_data.py — Seed the Neo4j database with SchemePath schema and data.

Usage:
    python seed_data.py              # seed if empty
    python seed_data.py --force      # re-seed even if data exists

Reads connection settings from .env (same config as the main app).
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

# ── Allow running from the schemepath-backend/ directory ──────────────────────
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()                       # load .env before importing app.config

from app.config import get_settings
from neo4j import GraphDatabase
from neo4j.exceptions import AuthError, ServiceUnavailable

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("seed")

# ── Cypher file path ──────────────────────────────────────────────────────────
SEED_FILE = Path(__file__).parent / "seed.cypher"


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_statements(path: Path) -> list[str]:
    """Read a .cypher file and split it into individual statements.

    Handles:
    - Single-line comments  (// …)
    - Multi-line /* … */    comments
    - Empty / whitespace-only blocks
    """
    raw = path.read_text(encoding="utf-8")

    # Strip multi-line block comments
    raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.DOTALL)

    # Strip single-line comments  (keep newlines so split logic still works)
    raw = re.sub(r"(?<!:)//[^\n]*", "", raw)

    statements = [s.strip() for s in raw.split(";")]
    return [s for s in statements if s]


def get_driver(settings):
    return GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )


def verify_connection(driver) -> bool:
    try:
        driver.verify_connectivity()
        log.info("✅ Neo4j connection verified.")
        return True
    except (ServiceUnavailable, AuthError) as exc:
        log.error("❌ Cannot connect to Neo4j: %s", exc)
        return False


def count_schemes(driver) -> int:
    with driver.session() as session:
        result = session.run("MATCH (s:Scheme) RETURN count(s) AS n")
        return result.single()["n"]


def run_seed(driver, statements: list[str]) -> int:
    """Execute all Cypher statements. Returns number of statements executed."""
    executed = 0
    with driver.session() as session:
        for i, stmt in enumerate(statements, start=1):
            try:
                session.run(stmt)
                executed += 1
                if i % 10 == 0 or i == len(statements):
                    log.info("  … %d / %d statements executed", i, len(statements))
            except Exception as exc:          # noqa: BLE001
                log.warning("  ⚠  Statement %d failed (skipping): %s", i, exc)
                log.debug("  Failing statement:\n%s", stmt[:300])
    return executed


# ── Main ──────────────────────────────────────────────────────────────────────

def main(force: bool = False) -> int:
    """Return 0 on success, 1 on failure."""

    # ── Validate seed file ────────────────────────────────────────────────────
    if not SEED_FILE.exists():
        log.error("Seed file not found: %s", SEED_FILE)
        return 1

    # ── Load config ───────────────────────────────────────────────────────────
    try:
        settings = get_settings()
    except Exception as exc:
        log.error("Configuration error: %s", exc)
        log.error("Make sure .env is present with NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, GEMINI_API_KEY")
        return 1

    log.info("Connecting to Neo4j at %s …", settings.NEO4J_URI)
    driver = get_driver(settings)

    try:
        # ── Verify connectivity ───────────────────────────────────────────────
        if not verify_connection(driver):
            return 1

        # ── Check if already seeded ───────────────────────────────────────────
        scheme_count = count_schemes(driver)
        if scheme_count > 0 and not force:
            log.info(
                "Database already seeded (%d Scheme node(s) found). "
                "Use --force to re-seed.",
                scheme_count,
            )
            return 0

        if scheme_count > 0 and force:
            log.info("--force specified. Re-seeding over existing data …")

        # ── Load and run statements ───────────────────────────────────────────
        statements = load_statements(SEED_FILE)
        log.info("Loaded %d Cypher statements from %s", len(statements), SEED_FILE.name)
        log.info("Running seed script …")

        executed = run_seed(driver, statements)
        final_count = count_schemes(driver)

        log.info(
            "✅ Seeding complete. %d statements executed. "
            "Database now has %d Scheme node(s).",
            executed,
            final_count,
        )
        return 0

    finally:
        driver.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed SchemePath Neo4j database.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-seed even if data already exists (does not delete first).",
    )
    args = parser.parse_args()
    sys.exit(main(force=args.force))
