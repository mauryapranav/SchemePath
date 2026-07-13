"""CSV upload adapter — demonstrates bulk import readiness.

Accepts a CSV with scheme data and converts it to the adapter interface.
Ready for OpenNyAI dataset import: github.com/OpenNyAI/schemes_chatbot
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.adapters.base import DocumentGuide, SchemeDataSource, SchemeDetailResult, SchemeResult

logger = logging.getLogger(__name__)


class CSVUploadAdapter(SchemeDataSource):
    """Ingests scheme data from CSV files for bulk import."""

    def __init__(self) -> None:
        self._schemes: List[Dict[str, Any]] = []

    def load_from_csv(self, filepath: str) -> int:
        """Load schemes from a CSV file.

        Expected columns: scheme_name, state, eligibility_criteria,
        documents_required, benefit_amount, application_url, tags

        Compatible with OpenNyAI schemes dataset format.
        """
        path = Path(filepath)
        if not path.exists():
            logger.error("CSV file not found: %s", filepath)
            return 0

        loaded = 0
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self._schemes.append({
                    "id": f"CSV-{loaded + 1}",
                    "name": row.get("scheme_name", ""),
                    "description": row.get("eligibility_criteria", ""),
                    "benefit_amount": row.get("benefit_amount"),
                    "tags": [t.strip() for t in (row.get("tags") or "").split(",") if t.strip()],
                    "application_url": row.get("application_url"),
                    "state": row.get("state"),
                })
                loaded += 1

        logger.info("CSVUploadAdapter: loaded %d schemes from %s", loaded, filepath)
        return loaded

    def search_schemes(
        self, intent_tags: List[str], state: Optional[str] = None
    ) -> List[SchemeResult]:
        results = []
        for s in self._schemes:
            if not intent_tags or any(t in s.get("tags", []) for t in intent_tags):
                if state and s.get("state") and s["state"].lower() != state.lower():
                    continue
                results.append(SchemeResult(
                    id=s["id"], name=s["name"], description=s.get("description", ""),
                    benefit_amount=s.get("benefit_amount"), tags=s.get("tags", []),
                    application_url=s.get("application_url"),
                ))
        return results

    def get_scheme_details(self, scheme_id: str) -> Optional[SchemeDetailResult]:
        for s in self._schemes:
            if s["id"] == scheme_id:
                return SchemeDetailResult(
                    id=s["id"], name=s["name"],
                    description=s.get("description", ""),
                    benefit_amount=s.get("benefit_amount"),
                )
        return None

    def get_eligibility_rules(self, scheme_id: str) -> List[Dict[str, Any]]:
        return []

    def get_document_guide(
        self, document_id: str, state: Optional[str] = None
    ) -> Optional[DocumentGuide]:
        return None
