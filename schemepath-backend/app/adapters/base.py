"""Abstract base class for scheme data sources — the Adapter Pattern.

Every data source (Neo4j, CSV, web enrichment, myScheme API) implements this
interface so the agent layer never cares where scheme data comes from.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes returned by adapters
# ---------------------------------------------------------------------------

@dataclass
class ProcurementStep:
    """One step in a document procurement guide."""
    step_number: int
    action: str
    location: str
    estimated_days: int
    cost: str
    prerequisites: List[str] = field(default_factory=list)


@dataclass
class DocumentGuide:
    """Full procurement guide for obtaining a specific document."""
    document_id: str
    document_name: str
    steps: List[ProcurementStep] = field(default_factory=list)
    total_estimated_days: int = 0
    total_estimated_cost: str = "Free"


@dataclass
class SchemeResult:
    """Lightweight scheme summary returned from search."""
    id: str
    name: str
    description: str
    benefit_amount: Optional[str] = None
    benefit_type: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    application_url: Optional[str] = None
    relevance_score: float = 0.0


@dataclass
class SchemeDetailResult:
    """Full scheme details with requirements."""
    id: str
    name: str
    description: str
    ministry: str = ""
    benefit_amount: Optional[str] = None
    benefit_type: Optional[str] = None
    application_url: Optional[str] = None
    official_link: Optional[str] = None
    requirements: List[Dict[str, Any]] = field(default_factory=list)
    prerequisite_schemes: List[str] = field(default_factory=list)
    estimated_time_days: Optional[int] = None
    estimated_cost: Optional[str] = None


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class SchemeDataSource(ABC):
    """Abstract interface for all scheme data providers."""

    @abstractmethod
    def search_schemes(
        self, intent_tags: List[str], state: Optional[str] = None
    ) -> List[SchemeResult]:
        """Find schemes matching the given intent tags and optional state."""
        ...

    @abstractmethod
    def get_scheme_details(self, scheme_id: str) -> Optional[SchemeDetailResult]:
        """Get full details for a specific scheme."""
        ...

    @abstractmethod
    def get_eligibility_rules(self, scheme_id: str) -> List[Dict[str, Any]]:
        """Get all requirements/rules for a scheme."""
        ...

    @abstractmethod
    def get_document_guide(
        self, document_id: str, state: Optional[str] = None
    ) -> Optional[DocumentGuide]:
        """Get step-by-step guide for obtaining a document."""
        ...
