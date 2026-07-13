"""Adapter registry — aggregates multiple SchemeDataSource implementations.

The registry tries the primary adapter (Neo4j) first, then falls back to
secondary sources. This is the entry point for all scheme data queries.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.adapters.base import DocumentGuide, SchemeDataSource, SchemeDetailResult, SchemeResult

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """Aggregates multiple data source adapters with priority-based lookup."""

    def __init__(self) -> None:
        self._adapters: List[tuple[str, SchemeDataSource]] = []

    def register(self, name: str, adapter: SchemeDataSource) -> None:
        self._adapters.append((name, adapter))
        logger.info("Registered adapter: %s (%s)", name, type(adapter).__name__)

    def list_adapters(self) -> List[str]:
        return [name for name, _ in self._adapters]

    def search_schemes(
        self, intent_tags: List[str], state: Optional[str] = None
    ) -> List[SchemeResult]:
        all_results: List[SchemeResult] = []
        seen_ids: set[str] = set()
        for name, adapter in self._adapters:
            try:
                results = adapter.search_schemes(intent_tags, state)
                for r in results:
                    if r.id not in seen_ids:
                        all_results.append(r)
                        seen_ids.add(r.id)
            except Exception as exc:
                logger.warning("Adapter %s search failed: %s", name, exc)
        return all_results

    def get_scheme_details(self, scheme_id: str) -> Optional[SchemeDetailResult]:
        for name, adapter in self._adapters:
            try:
                result = adapter.get_scheme_details(scheme_id)
                if result:
                    return result
            except Exception as exc:
                logger.warning("Adapter %s detail failed: %s", name, exc)
        return None

    def get_eligibility_rules(self, scheme_id: str) -> List[Dict[str, Any]]:
        for name, adapter in self._adapters:
            try:
                result = adapter.get_eligibility_rules(scheme_id)
                if result:
                    return result
            except Exception as exc:
                logger.warning("Adapter %s rules failed: %s", name, exc)
        return []

    def get_document_guide(
        self, document_id: str, state: Optional[str] = None
    ) -> Optional[DocumentGuide]:
        for name, adapter in self._adapters:
            try:
                result = adapter.get_document_guide(document_id, state)
                if result:
                    return result
            except Exception as exc:
                logger.warning("Adapter %s guide failed: %s", name, exc)
        return None


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_registry: Optional[AdapterRegistry] = None


def get_registry() -> AdapterRegistry:
    """Return (and lazily initialize) the global adapter registry."""
    global _registry
    if _registry is None:
        from app.adapters.neo4j_adapter import Neo4jSeedAdapter
        from app.adapters.web_enrichment import WebSearchEnrichmentAdapter
        from app.adapters.myscheme_stub import MySchemeAPIAdapter

        _registry = AdapterRegistry()
        _registry.register("neo4j_seed", Neo4jSeedAdapter())
        _registry.register("web_enrichment", WebSearchEnrichmentAdapter())
        _registry.register("myscheme_api", MySchemeAPIAdapter())
        logger.info(
            "Adapter registry initialized with %d sources: %s",
            len(_registry._adapters), _registry.list_adapters(),
        )
    return _registry
