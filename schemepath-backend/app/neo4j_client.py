from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Dict, Generator, List

from neo4j import AsyncGraphDatabase, AsyncDriver          # async module-level singleton
from neo4j import GraphDatabase, Driver, Session            # sync Neo4jClient class
from neo4j.exceptions import AuthError, Neo4jError, ServiceUnavailable

from app.config import get_settings

logger = logging.getLogger(__name__)

# Module-level driver instance (initialised during app lifespan)
_driver: AsyncDriver | None = None


def init_driver() -> AsyncDriver:
    """Initialise the Neo4j async driver and store it as a module singleton."""
    # We use a single shared driver instance (connection pool) across the whole app 
    # because creating a new driver for every request is incredibly slow and will 
    # quickly exhaust database connection limits.
    global _driver
    settings = get_settings()
    _driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )
    logger.info("Neo4j driver initialised (URI=%s, user=%s)", settings.NEO4J_URI, settings.NEO4J_USER)
    return _driver


async def close_driver() -> None:
    """Close the driver and release all connections."""
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None
        logger.info("Neo4j driver closed.")


def get_driver() -> AsyncDriver:
    """Return the active driver.  Raises RuntimeError if not initialised."""
    if _driver is None:
        raise RuntimeError(
            "Neo4j driver has not been initialised. "
            "Ensure init_driver() is called during application startup."
        )
    return _driver


async def verify_connectivity() -> bool:
    """Ping Neo4j and return True if the server is reachable.

    Returns False (instead of raising) so callers can handle gracefully.
    """
    try:
        driver = get_driver()
        await driver.verify_connectivity()
        logger.info("Neo4j connectivity verified successfully.")
        return True
    except (ServiceUnavailable, AuthError) as exc:
        logger.error("Neo4j connectivity check failed: %s", exc)
        return False
    except RuntimeError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error during Neo4j connectivity check: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Neo4jClient — synchronous class-based interface
# ---------------------------------------------------------------------------

class Neo4jClient:
    """Synchronous Neo4j client wrapping a GraphDatabase.driver instance.

    Use this class when you need a reusable, injectable client rather than
    the module-level async singleton above.
    """

    def __init__(self, uri: str, user: str, password: str) -> None:
        """Initialise the driver.

        Args:
            uri: Bolt/Neo4j connection URI (e.g. ``neo4j+s://...``).
            user: Neo4j username.
            password: Neo4j password.
        """
        self.driver: Driver = GraphDatabase.driver(uri, auth=(user, password))
        logger.info("Neo4jClient initialised (URI=%s, user=%s)", uri, user)

    # ------------------------------------------------------------------
    # Connectivity
    # ------------------------------------------------------------------

    def verify_connectivity(self) -> bool:
        """Ping the server and return True if reachable."""
        try:
            self.driver.verify_connectivity()
            logger.info("Neo4jClient connectivity verified.")
            return True
        except (ServiceUnavailable, AuthError) as exc:
            logger.error("Neo4jClient connectivity check failed: %s", exc)
            return False
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error during Neo4jClient connectivity check: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the driver and release all connections."""
        try:
            self.driver.close()
            logger.info("Neo4jClient driver closed.")
        except Exception as exc:  # noqa: BLE001
            logger.error("Error while closing Neo4jClient driver: %s", exc)

    # ------------------------------------------------------------------
    # Session context manager
    # ------------------------------------------------------------------

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Yield a Neo4j session, guaranteeing closure in a finally block."""
        # We use a context manager here to protect the application from connection leaks.
        # Even if a query crashes or times out, the `finally` block ensures the session
        # is safely returned to the connection pool.
        s: Session = self.driver.session()
        try:
            yield s
        finally:
            s.close()

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def run_query(self, query: str, parameters: dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return all records as plain dicts.

        Args:
            query: Cypher query string.
            parameters: Optional mapping of query parameters.

        Returns:
            List of record dicts (one per row). Empty list on error.
        """
        parameters = parameters or {}
        try:
            with self.session() as s:
                result = s.run(query, parameters)
                records = [record.data() for record in result]
            logger.debug("Neo4jClient query returned %d record(s).", len(records))
            return records
        except Neo4jError as exc:
            logger.error("Neo4j query error: %s | query=%s", exc, query)
            return []
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error running Neo4j query: %s", exc)
            return []
