from __future__ import annotations

import logging
from typing import Optional

from app.models import NextQuestion
from app.services.gemini_service import GeminiService
from app.services.graph_service import GraphService

logger = logging.getLogger(__name__)


class QuestionEngine:
    """Thin orchestration layer that combines graph analysis with Gemini context enrichment.

    # We use this orchestration pattern to keep the heavy graph logic separate from the 
    # LLM text generation logic. This engine simply glues them together: it asks the graph 
    # *what* to ask, and asks Gemini *how* to motivate the user to answer it.
    GraphService determines *which* question to ask next based on the highest-
    impact unknown variable.  GeminiService enriches the question context with
    a natural-language motivational sentence — but only when the potential
    unlock count is high enough to warrant the extra API call.
    """

    # Minimum schemes_unlocked_estimate that triggers a Gemini context call
    _GEMINI_THRESHOLD: int = 3

    def __init__(self, graph_service: GraphService, gemini_service: GeminiService) -> None:
        """Store service dependencies.

        Args:
            graph_service:  Handles Neo4j graph queries.
            gemini_service: Handles Gemini AI text generation.
        """
        self.graph = graph_service
        self.gemini = gemini_service

    def get_next_question(self, profile_id: str) -> Optional[NextQuestion]:
        """Return the highest-impact follow-up question for a citizen profile.

        Steps:
        1. Delegate to GraphService to find the most impactful unanswered
           requirement category.
        2. If no question is needed (profile is complete), return None.
        3. If the estimated unlock count exceeds the threshold, call
           GeminiService to replace the default context with a more
           engaging, natural-language sentence.

        Args:
            profile_id: The CitizenProfile UUID.

        Returns:
            An enriched NextQuestion, or None if the profile is complete.
        """
        question = self.graph.get_next_question(profile_id)

        if question is None:
            logger.info("QuestionEngine: profile %s is complete — no further questions.", profile_id)
            return None

        if question.schemes_unlocked_estimate > self._GEMINI_THRESHOLD:
            try:
                ai_context = self.gemini.generate_question_context(
                    question_category=question.category,
                    schemes_count=question.schemes_unlocked_estimate,
                )
                question.context = ai_context
                logger.debug(
                    "QuestionEngine: Gemini context applied for category=%s (unlocks=%d)",
                    question.category,
                    question.schemes_unlocked_estimate,
                )
            except Exception as exc:  # noqa: BLE001
                # Gemini enrichment is best-effort; keep the graph-generated context on failure
                logger.warning(
                    "QuestionEngine: Gemini context generation failed, using default. error=%s", exc
                )

        return question
