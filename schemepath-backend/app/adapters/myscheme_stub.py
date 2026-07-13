"""myScheme.gov.in API adapter — placeholder for future integration.

Demonstrates architectural readiness to connect to the official government
scheme discovery API when it becomes publicly available.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.adapters.base import DocumentGuide, SchemeDataSource, SchemeDetailResult, SchemeResult

logger = logging.getLogger(__name__)

_MYSCHEME_API_BASE = "https://www.myscheme.gov.in/api/v1"


class MySchemeAPIAdapter(SchemeDataSource):
    """Placeholder adapter for myScheme.gov.in API integration."""

    def search_schemes(
        self, intent_tags: List[str], state: Optional[str] = None
    ) -> List[SchemeResult]:
        logger.info(
            "MySchemeAPIAdapter: API integration pending — "
            "falling back to curated graph data."
        )
        return []

    def get_scheme_details(self, scheme_id: str) -> Optional[SchemeDetailResult]:
        return None

    def get_eligibility_rules(self, scheme_id: str) -> List[Dict[str, Any]]:
        return []

    def get_document_guide(
        self, document_id: str, state: Optional[str] = None
    ) -> Optional[DocumentGuide]:
        return None
