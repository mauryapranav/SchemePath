from __future__ import annotations

import json
import logging
import re
from typing import Any

from google import genai

from app.config import get_settings
from app.models import ParsedProfile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Known document IDs (used to normalise mentions in raw input)
# ---------------------------------------------------------------------------
_KNOWN_DOC_IDS: list[str] = [
    "DOC-AADHAAR",
    "DOC-PAN",
    "DOC-RATION",
    "DOC-BANK-AC",
    "DOC-LAND-RECORD",
    "DOC-VENDOR-CERT",
    "DOC-NREGA-JOBCARD",
]

# ---------------------------------------------------------------------------
# Module-level helpers (kept for backward-compat with question_engine.py)
# ---------------------------------------------------------------------------

def _get_client() -> genai.Client:
    """Initialise and return a Gemini client."""
    settings = get_settings()
    return genai.Client(api_key=settings.GEMINI_API_KEY)


async def generate_text(prompt: str, **kwargs: Any) -> str:
    """Send *prompt* to Gemini and return the text response.

    Args:
        prompt: The user / system prompt to send.
        **kwargs: Extra keyword arguments forwarded to ``generate_content``.

    Returns:
        The generated text string.

    Raises:
        RuntimeError: If Gemini returns an empty or blocked response.
    """
    client = _get_client()
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        **kwargs,
    )

    try:
        text = response.text
    except ValueError as exc:
        raise RuntimeError(f"Gemini response was blocked or empty: {exc}") from exc

    logger.debug("Gemini response (%d chars)", len(text))
    return text


# ---------------------------------------------------------------------------
# GeminiService class
# ---------------------------------------------------------------------------

# We use strict JSON formatting constraints in this prompt to ensure the LLM
# acts like a reliable data pipeline rather than a conversational chatbot.
# Providing exact keys and Enums prevents parsing crashes in our Pydantic models.
_PARSE_PROMPT_TEMPLATE = """You are a government scheme eligibility assistant for India.

Parse the following citizen's description and extract structured information.

Citizen input:
\"\"\"{raw_input}\"\"\"

Return ONLY valid JSON (no markdown, no extra text) with these exact keys:
{{
  "age": <integer or null>,
  "gender": <"male" | "female" | "other" | null>,
  "caste": <string or null>,
  "state": <string or null>,
  "location_type": <"rural" | "urban" | "semi-urban" | null>,
  "family_income_annual": <integer (INR per year) or null>,
  "occupation": <string or null>,
  "goal": <string describing what the citizen wants help with, or null>,
  "goal_tags": <list of strings representing goal categories, or []>,
  "mentioned_documents": <list of document IDs from {doc_ids} that were explicitly mentioned, or []>,
  "confidence_score": <float between 0.0 and 1.0 representing how complete the extracted data is>
}}

Rules:
- Extract only information explicitly stated. Do NOT guess.
- Additionally, analyze the user's goal and extract 1 to 3 goal_tags from this controlled vocabulary: ["health", "medical", "insurance", "agriculture", "farming", "business", "loan", "employment", "job", "education", "housing", "pension", "disability", "woman", "child", "student", "startup", "credit"]. Only return tags genuinely relevant to the user's stated need. If the user says "I have a health issue," return ["health", "medical", "insurance"]. If they say "I want to start farming," return ["agriculture", "farming"]. If no clear goal is stated, return []. Return these in the JSON as "goal_tags": ["health", "medical"].
- For mentioned_documents, map only documents the citizen explicitly mentioned to the nearest ID from: {doc_ids}
- confidence_score: 1.0 = all fields filled, 0.0 = nothing extracted.
- Return ONLY the JSON object. No markdown, no explanation."""

_CONTEXT_PROMPT_TEMPLATE = """Generate exactly one short, encouraging sentence (under 15 words) explaining
why knowing a citizen's {category} helps find government schemes.
The sentence should mention that it helps unlock approximately {count} schemes.
Example style: "Knowing this helps us find 7 schemes you might be missing out on."
Return ONLY the sentence, nothing else."""


class GeminiService:
    """Class-based Gemini client for SchemePath AI features."""

    def __init__(self, api_key: str) -> None:
        """Configure the Gemini client and set the default model.

        Args:
            api_key: Google Gemini API key.
        """
        self._client: genai.Client = genai.Client(api_key=api_key)
        self._model: str = "gemini-1.5-flash"
        logger.info("GeminiService initialised (model=%s)", self._model)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _generate(self, prompt: str) -> str:
        """Call Gemini synchronously and return raw text.

        Never raises — returns an empty string on any failure.
        """
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
            )
            return response.text or ""
        except Exception as exc:  # noqa: BLE001
            logger.error("Gemini API call failed: %s", exc)
            return ""

    @staticmethod
    def _strip_markdown(text: str) -> str:
        """Remove ```json ... ``` fences and surrounding whitespace."""
        # Strip fenced code blocks (```json ... ``` or ``` ... ```)
        text = re.sub(r"```(?:json)?\s*", "", text)
        text = re.sub(r"```", "", text)
        return text.strip()

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def parse_citizen_input(self, raw_input: str) -> ParsedProfile:
        """Parse free-form citizen text into a structured ParsedProfile.

        Args:
            raw_input: Natural-language description provided by the citizen.

        Returns:
            A ParsedProfile instance. Falls back to a minimal profile with
            ``confidence_score=0.3`` if parsing fails at any step.
        """
        # We use a zero-confidence fallback profile to guarantee the user's journey 
        # continues smoothly even if the LLM service is down or completely hallucinates.
        fallback = ParsedProfile(goal=raw_input, confidence_score=0.3)

        if not raw_input or not raw_input.strip():
            logger.warning("parse_citizen_input received empty input; returning fallback.")
            return fallback

        doc_ids_str = ", ".join(f'"{d}"' for d in _KNOWN_DOC_IDS)
        prompt = _PARSE_PROMPT_TEMPLATE.format(
            raw_input=raw_input.strip(),
            doc_ids=doc_ids_str,
        )

        raw_text = self._generate(prompt)
        if not raw_text:
            logger.error("Gemini returned empty response for parse_citizen_input.")
            return fallback

        try:
            clean = self._strip_markdown(raw_text)
            data: dict = json.loads(clean)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("Failed to parse Gemini JSON response: %s | raw=%s", exc, raw_text[:200])
            return fallback

        try:
            profile = ParsedProfile(**data)
            logger.debug(
                "ParsedProfile built (confidence=%.2f, fields_set=%s)",
                profile.confidence_score,
                profile.model_fields_set,
            )
            return profile
        except Exception as exc:  # noqa: BLE001
            logger.error("ParsedProfile validation failed: %s | data=%s", exc, data)
            return fallback

    def generate_question_context(self, question_category: str, schemes_count: int) -> str:
        """Generate a short motivational sentence for a question prompt.

        Args:
            question_category: The category of the question (e.g. "income", "caste").
            schemes_count: Estimated number of schemes the answer may unlock.

        Returns:
            A single encouraging sentence under 15 words. Falls back to a
            generic sentence if Gemini fails.
        """
        fallback = f"This helps us find {schemes_count} schemes tailored for you."

        prompt = _CONTEXT_PROMPT_TEMPLATE.format(
            category=question_category,
            count=schemes_count,
        )

        text = self._generate(prompt)
        if not text:
            logger.warning("Gemini returned empty context; using fallback sentence.")
            return fallback

        # Trim to first sentence in case the model returned more than one
        sentence = text.strip().split("\n")[0].strip()
        logger.debug("Generated question context: %s", sentence)
        return sentence
