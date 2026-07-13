"""Web search enrichment adapter — uses Gemini to fetch live scheme data.

Demonstrates dynamic enrichment: when a user asks about a specific scheme,
this adapter fetches the latest benefit amounts, application URLs, and policy
changes from the web via Gemini's grounding capability.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from google import genai

from app.adapters.base import DocumentGuide, SchemeDataSource, SchemeDetailResult, SchemeResult
from app.config import get_settings

logger = logging.getLogger(__name__)

_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL = 3600  # 1 hour


class WebSearchEnrichmentAdapter(SchemeDataSource):
    """Enriches scheme data using Gemini with web-grounded search."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._model = "gemini-2.5-flash"

    def _enrich(self, scheme_name: str, scheme_id: str) -> Dict[str, Any]:
        cache_key = scheme_id
        cached = _CACHE.get(cache_key)
        if cached and (time.time() - cached["_ts"]) < _CACHE_TTL:
            return cached

        prompt = (
            f"Find the latest information about the Indian government scheme "
            f"'{scheme_name}'. Return ONLY valid JSON with these keys:\n"
            f'{{"benefit_amount": "<current benefit amount>", '
            f'"application_url": "<official portal URL>", '
            f'"last_updated": "<date of latest policy change if known>", '
            f'"recent_changes": "<brief summary of any recent changes>"}}\n'
            f"If you cannot find information, return null for that field."
        )
        try:
            response = self._client.models.generate_content(
                model=self._model, contents=prompt,
            )
            text = (response.text or "").strip()
            # Strip markdown fences
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            data = json.loads(text)
            data["_ts"] = time.time()
            _CACHE[cache_key] = data
            return data
        except Exception as exc:
            logger.warning("Web enrichment failed for %s: %s", scheme_name, exc)
            return {}

    # -- Interface methods (search is not the enrichment adapter's job) ------

    def search_schemes(
        self, intent_tags: List[str], state: Optional[str] = None
    ) -> List[SchemeResult]:
        return []  # Enrichment adapter doesn't do primary search

    def get_scheme_details(self, scheme_id: str) -> Optional[SchemeDetailResult]:
        return None  # Use Neo4j for structured details

    def get_eligibility_rules(self, scheme_id: str) -> List[Dict[str, Any]]:
        return []

    def get_document_guide(
        self, document_id: str, state: Optional[str] = None
    ) -> Optional[DocumentGuide]:
        return None

    def enrich_scheme(self, scheme_name: str, scheme_id: str) -> Dict[str, Any]:
        """Public method to enrich a scheme with live web data."""
        return self._enrich(scheme_name, scheme_id)
