from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Generic API response models
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    # We use this primarily for infrastructure monitoring (like Render's health checks)
    # to ensure the web service and the database are both operational.
    status: str
    neo4j_connected: bool


class ErrorResponse(BaseModel):
    detail: str


# ---------------------------------------------------------------------------
# Citizen Profile models
# ---------------------------------------------------------------------------

class CitizenProfileCreate(BaseModel):
    """Payload to kick off a new citizen profile from free-form text."""
    # We use this model when a citizen first types their story in the UI.
    # It acts as the raw input before Gemini turns it into structured data.
    raw_input: str


class CitizenProfileUpdate(BaseModel):
    """Partial update to a citizen profile — all fields optional."""

    age: Optional[int] = None
    gender: Optional[Literal["male", "female", "other"]] = None
    caste: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    location_type: Optional[Literal["rural", "urban", "semi-urban"]] = None
    family_income_annual: Optional[Any] = None
    occupation: Optional[str] = None
    goal: Optional[str] = None
    goal_tags: Optional[List[str]] = None
    has_documents: Optional[List[str]] = None
    has_land: Optional[Any] = None
    has_bank_account: Optional[Any] = None
    land_acres: Optional[float] = None


class ParsedProfile(BaseModel):
    """Structured profile extracted by Gemini from raw citizen input."""
    # We use this to establish a strong typing contract between Gemini's 
    # unstructured text generation and our backend graph creation logic.
    age: Optional[int] = None
    gender: Optional[str] = None
    caste: Optional[str] = None
    state: Optional[str] = None
    location_type: Optional[str] = None
    family_income_annual: Optional[int] = None
    occupation: Optional[str] = None
    goal: Optional[str] = None
    goal_tags: List[str] = Field(default_factory=list)
    mentioned_documents: List[str] = Field(default_factory=list)
    confidence_score: float


# ---------------------------------------------------------------------------
# Question engine models
# ---------------------------------------------------------------------------

class NextQuestion(BaseModel):
    """A single follow-up question to narrow scheme eligibility."""
    # We use this to tell the frontend exactly how to render the next interactive step,
    # ensuring the UI doesn't need to know anything about the graph structure.
    question_id: str
    question_text: str
    question_type: Literal["single_choice", "multi_select", "boolean", "number", "text"]
    options: Optional[List[Dict[str, Any]]] = None
    context: str
    schemes_unlocked_estimate: int
    category: str


# ---------------------------------------------------------------------------
# Eligibility / scheme path models
# ---------------------------------------------------------------------------

class EligibilityPath(BaseModel):
    """Eligibility status and navigation path for a single scheme."""

    scheme_id: str
    scheme_name: str
    scheme_description: str
    benefit_amount: Optional[str]
    scheme_tags: List[str] = Field(default_factory=list)
    status: Literal["confirmed", "one_step", "locked", "unknown"]
    total_steps: int
    completed_steps: int
    missing_requirements: List[Dict[str, Any]]
    next_steps: List[Dict[str, Any]]
    estimated_time_days: Optional[int]
    estimated_cost: Optional[str]
    path_visualization: List[str]


class EligibilityMap(BaseModel):
    """Full eligibility map for a citizen profile across all schemes."""

    profile_id: str
    goal_relevant_schemes: List[EligibilityPath]
    other_schemes: List[EligibilityPath]
    confirmed_schemes: List[EligibilityPath]
    one_step_schemes: List[EligibilityPath]
    locked_schemes: List[EligibilityPath]
    total_schemes_analyzed: int
    profile_completion: float
    user_goal_tags: List[str]
    user_goal: Optional[str]


# ---------------------------------------------------------------------------
# Scheme detail model
# ---------------------------------------------------------------------------

class SchemeDetail(BaseModel):
    """Complete metadata for a government scheme node in the graph."""

    id: str
    name: str
    description: str
    ministry: str
    benefit_amount: Optional[str]
    benefit_type: Optional[str]
    application_url: Optional[str]
    official_link: Optional[str]
    requirements: List[Dict[str, Any]]
    prerequisite_schemes: List[str]
    mutually_exclusive_with: List[str]
