from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from app.models import (
    CitizenProfileUpdate,
    EligibilityMap,
    EligibilityPath,
    NextQuestion,
    ParsedProfile,
    SchemeDetail,
)
from app.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Question templates keyed by requirement category
# ---------------------------------------------------------------------------

_QUESTION_MAP: Dict[str, Dict[str, Any]] = {
    "document": {
        "question_text": "Which of the following documents do you currently have?",
        "question_type": "multi_select",
        "options": [
            {"id": "DOC-AADHAAR",       "label": "Aadhaar Card"},
            {"id": "DOC-PAN",           "label": "PAN Card"},
            {"id": "DOC-RATION",        "label": "Ration Card"},
            {"id": "DOC-BANK-AC",       "label": "Bank Account / Passbook"},
            {"id": "DOC-LAND-RECORD",   "label": "Land Record / Patta"},
            {"id": "DOC-VENDOR-CERT",   "label": "Vendor / Shop Certificate"},
            {"id": "DOC-NREGA-JOBCARD", "label": "NREGA Job Card"},
        ],
    },
    "land": {
        "question_text": "What is your land ownership status?",
        "question_type": "single_choice",
        "options": [
            {"id": "own",   "label": "I own agricultural land"},
            {"id": "lease", "label": "I lease / rent land"},
            {"id": "none",  "label": "I do not have land"},
            {"id": "na",    "label": "Not applicable"},
        ],
    },
    "income": {
        "question_text": "What is your approximate annual household income?",
        "question_type": "single_choice",
        "options": [
            {"id": "0-50000",      "label": "Up to ₹50,000"},
            {"id": "50001-100000", "label": "₹50,001 – ₹1,00,000"},
            {"id": "100001-200000","label": "₹1,00,001 – ₹2,00,000"},
            {"id": "200001-500000","label": "₹2,00,001 – ₹5,00,000"},
            {"id": "500001+",      "label": "Above ₹5,00,000"},
        ],
    },
    "bank_account": {
        "question_text": "Do you have a bank account linked to Aadhaar?",
        "question_type": "boolean",
        "options": None,
    },
}


class GraphService:
    """Service layer for all Neo4j graph operations."""

    def __init__(self, neo4j_client: Neo4jClient) -> None:
        """Initialise with an active Neo4jClient.

        Args:
            neo4j_client: A connected Neo4jClient instance.
        """
        self.db = neo4j_client

    # ------------------------------------------------------------------
    # Profile creation
    # ------------------------------------------------------------------

    def create_profile(self, parsed: ParsedProfile) -> str:
        """Persist a new CitizenProfile node and link known documents.

        Args:
            parsed: Structured profile returned by GeminiService.

        Returns:
            The UUID string of the newly created CitizenProfile node.
        """
        profile_id = str(uuid.uuid4())

        # 1. Create the base CitizenProfile node
        # We use this query to create a brand new citizen identity in the graph.
        # It takes all the demographics we managed to extract and stores them 
        # so we have a starting point for matching them against scheme requirements.
        create_query = """
        CREATE (c:CitizenProfile {
            id:                   $id,
            age:                  $age,
            gender:               $gender,
            caste:                $caste,
            state:                $state,
            location_type:        $location_type,
            family_income_annual: $family_income_annual,
            occupation:           $occupation,
            goal:                 $goal,
            goal_tags:            $goal_tags,
            confidence_score:     $confidence_score,
            created_at:           datetime(),
            updated_at:           datetime()
        })
        RETURN c.id AS profile_id
        """
        params: Dict[str, Any] = {
            "id":                   profile_id,
            "age":                  parsed.age,
            "gender":               parsed.gender,
            "caste":                parsed.caste,
            "state":                parsed.state,
            "location_type":        parsed.location_type,
            "family_income_annual": parsed.family_income_annual,
            "occupation":           parsed.occupation,
            "goal":                 parsed.goal,
            "goal_tags":            parsed.goal_tags,
            "confidence_score":     parsed.confidence_score,
        }

        result = self.db.run_query(create_query, params)
        if not result:
            logger.error("create_profile: CREATE returned no records for id=%s", profile_id)
            return profile_id

        # 2. Link documents if any were mentioned
        if parsed.mentioned_documents:
            # We use this query to instantly verify any documents the citizen told us they have.
            # By connecting their profile node to existing Document nodes, they immediately
            # bypass any questions about those specific documents later on.
            doc_query = """
            MATCH (c:CitizenProfile {id: $profile_id})
            UNWIND $doc_ids AS doc_id
            MATCH (d:Document {id: doc_id})
            MERGE (c)-[:HAS {verified: true}]->(d)
            """
            self.db.run_query(
                doc_query,
                {"profile_id": profile_id, "doc_ids": parsed.mentioned_documents},
            )

        logger.info("CitizenProfile created: id=%s", profile_id)
        return profile_id

    # ------------------------------------------------------------------
    # Profile update
    # ------------------------------------------------------------------

    def update_profile(self, profile_id: str, update: CitizenProfileUpdate) -> None:
        """Apply a partial update to an existing CitizenProfile.

        Only non-None fields are written. Document and land relationships
        are handled separately.

        Args:
            profile_id: The profile's UUID.
            update: Partial update model (None fields are skipped).
        """
        # ── Scalar field update ─────────────────────────────────────────
        scalar_fields = [
            "age", "gender", "caste", "state", "district",
            "location_type", "family_income_annual", "occupation", "goal",
            "goal_tags", "has_land", "land_acres",
        ]

        set_clauses: List[str] = ["c.updated_at = datetime()"]
        params: Dict[str, Any] = {"profile_id": profile_id}

        for field in scalar_fields:
            value = getattr(update, field, None)
            if value is not None:
                set_clauses.append(f"c.{field} = ${field}")
                params[field] = value

        if len(set_clauses) > 1:  # at least one real field besides updated_at
            set_str = ", ".join(set_clauses)
            scalar_query = f"""
            MATCH (c:CitizenProfile {{id: $profile_id}})
            SET {set_str}
            """
            self.db.run_query(scalar_query, params)
            logger.debug("update_profile scalars: id=%s fields=%s", profile_id, set_clauses)

        # ── Document relationships ──────────────────────────────────────
        if update.has_documents:
            # We use this query to dynamically attach new documents as the citizen answers
            # questions. MERGE ensures we don't accidentally create duplicate relationships
            # if they somehow specify the same document twice.
            doc_query = """
            MATCH (c:CitizenProfile {id: $profile_id})
            UNWIND $doc_ids AS doc_id
            MATCH (d:Document {id: doc_id})
            MERGE (c)-[r:HAS]->(d)
            ON CREATE SET r.verified = true, r.verified_at = datetime()
            ON MATCH  SET r.verified = true, r.verified_at = datetime()
            """
            self.db.run_query(
                doc_query,
                {"profile_id": profile_id, "doc_ids": update.has_documents},
            )
            logger.debug("update_profile docs: id=%s docs=%s", profile_id, update.has_documents)

        # ── Land record ─────────────────────────────────────────────────
        if update.has_land is True:
            land_query = """
            MATCH (c:CitizenProfile {id: $profile_id})
            MERGE (l:LandRecord {owner_id: $profile_id})
            ON CREATE SET l.id = $land_id, l.created_at = datetime()
            MERGE (c)-[:HAS]->(l)
            """
            self.db.run_query(
                land_query,
                {"profile_id": profile_id, "land_id": str(uuid.uuid4())},
            )
            logger.debug("update_profile land record merged: id=%s", profile_id)

    # ------------------------------------------------------------------
    # Core eligibility map
    # ------------------------------------------------------------------

    def get_eligibility_map(self, profile_id: str) -> EligibilityMap:
        eligibility_query = """
        MATCH (c:CitizenProfile {id: $profile_id})
        MATCH (s:Scheme {active: true})
        WITH c, s,
             CASE
               WHEN c.goal_tags IS NULL OR size(c.goal_tags) = 0 THEN false
               WHEN s.tags IS NULL THEN false
               ELSE ANY(tag IN s.tags WHERE tag IN c.goal_tags)
             END AS is_goal_relevant
        OPTIONAL MATCH (s)-[r:REQUIRES]->(req:Requirement)
        WITH c, s, is_goal_relevant, req,
             CASE
               WHEN req IS NULL THEN true
               WHEN req.category = 'prerequisite_scheme' THEN EXISTS {
                 MATCH (c)-[:ELIGIBLE_FOR]->(pre:Scheme)
                 WHERE (s)-[:PREREQUISITE]->(pre)
               }
               ELSE EXISTS {
                 MATCH (req)-[:FULFILLED_BY]->(f)
                 WHERE (c)-[:HAS]->(f)
               }
             END AS is_fulfilled
        WITH s, is_goal_relevant,
             count(CASE WHEN req IS NOT NULL THEN 1 END) AS total_reqs,
             count(CASE WHEN is_fulfilled = true AND req IS NOT NULL THEN 1 END) AS fulfilled_count,
             collect(CASE WHEN is_fulfilled = false AND req IS NOT NULL THEN {id: req.id, name: req.name, category: req.category, description: req.description} END) AS missing_list
        WITH s, is_goal_relevant, total_reqs, fulfilled_count,
             [m IN missing_list WHERE m IS NOT NULL] AS missing_reqs,
             CASE
               WHEN total_reqs = 0 THEN 'unknown'
               WHEN fulfilled_count = total_reqs THEN 'confirmed'
               WHEN fulfilled_count = total_reqs - 1 THEN 'one_step'
               ELSE 'locked'
             END AS status
        RETURN 
            s.id AS scheme_id, 
            s.name AS scheme_name, 
            s.description AS scheme_description, 
            s.benefit_amount AS benefit_amount, 
            s.tags AS scheme_tags, 
            status, 
            total_reqs, 
            fulfilled_count AS completed_steps, 
            missing_reqs AS missing_requirements, 
            is_goal_relevant
        ORDER BY is_goal_relevant DESC,
                 CASE status WHEN 'confirmed' THEN 1 WHEN 'one_step' THEN 2 WHEN 'locked' THEN 3 ELSE 4 END,
                 total_reqs ASC
        """

        completion_query = """
        MATCH (c:CitizenProfile {id: $profile_id})
        OPTIONAL MATCH (c)-[:HAS]->(d:Document)
        WITH c, count(DISTINCT d) AS doc_count
        RETURN
            (CASE WHEN c.age IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN c.gender IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN c.state IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN c.caste IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN c.family_income_annual IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN c.location_type IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN doc_count > 0 THEN 1 ELSE 0 END) AS filled_fields,
            7 AS total_fields,
            c.goal_tags AS user_goal_tags,
            c.goal AS user_goal
        """

        rows = self.db.run_query(eligibility_query, {"profile_id": profile_id})
        comp_rows = self.db.run_query(completion_query, {"profile_id": profile_id})

        profile_completion = 0.0
        user_goal_tags = []
        user_goal = None
        if comp_rows:
            comp = comp_rows[0]
            filled = comp.get("filled_fields") or 0
            total = comp.get("total_fields") or 7
            profile_completion = round(filled / total, 2)
            user_goal_tags = comp.get("user_goal_tags") or []
            user_goal = comp.get("user_goal")

        confirmed, one_step, locked = [], [], []
        goal_relevant_schemes, other_schemes = [], []

        for row in rows:
            missing: List[Dict[str, Any]] = row.get("missing_requirements") or []

            ep = EligibilityPath(
                scheme_id=row["scheme_id"],
                scheme_name=row["scheme_name"],
                scheme_description=row.get("scheme_description") or "",
                benefit_amount=row.get("benefit_amount"),
                scheme_tags=row.get("scheme_tags") or [],
                status=row["status"],
                total_steps=row.get("total_reqs") or 0,
                completed_steps=row.get("completed_steps") or 0,
                missing_requirements=missing,
                next_steps=[{"action": f"Provide {r['name']}"} for r in missing[:3]],
                estimated_time_days=None,
                estimated_cost=None,
                path_visualization=[],
            )

            if ep.status == "confirmed":
                confirmed.append(ep)
            elif ep.status == "one_step":
                one_step.append(ep)
            elif ep.status == "locked":
                locked.append(ep)

            # Categorize into goal vs other. If user has no tags, treat all as goal-relevant
            # to prevent UI from hiding them in an "other" section when they just started.
            if len(user_goal_tags) == 0:
                goal_relevant_schemes.append(ep)
            else:
                if row.get("is_goal_relevant"):
                    goal_relevant_schemes.append(ep)
                else:
                    other_schemes.append(ep)

        return EligibilityMap(
            profile_id=profile_id,
            goal_relevant_schemes=goal_relevant_schemes,
            other_schemes=other_schemes,
            confirmed_schemes=confirmed,
            one_step_schemes=one_step,
            locked_schemes=locked,
            total_schemes_analyzed=len(rows),
            profile_completion=profile_completion,
            user_goal_tags=user_goal_tags,
            user_goal=user_goal,
        )

    # ------------------------------------------------------------------
    # Next question
    # ------------------------------------------------------------------

    def get_next_question(self, profile_id: str) -> Optional[NextQuestion]:
        """Find the highest-impact unanswered question for this profile.

        Identifies the requirement category with the most schemes still
        blocked, then maps that category to a structured NextQuestion.

        Args:
            profile_id: The CitizenProfile UUID.

        Returns:
            A NextQuestion, or None if everything is already answered.
        """
        # We use this query to find the "highest impact" missing requirement.
        # It finds active schemes, looks at what requirements the citizen doesn't have yet,
        # groups them by category, and sorts by which category blocks the most schemes.
        # This guarantees we always ask the question that unlocks the most value.
        query = """
        MATCH (c:CitizenProfile {id: $profile_id})
        MATCH (s:Scheme {active: true})
        MATCH (s)-[:REQUIRES]->(req:Requirement)
        WHERE NOT (c)-[:HAS]->()<-[:FULFILLED_BY]-(req)
          AND req.category IN ['document', 'land', 'income', 'bank_account']
        WITH req, c, collect(DISTINCT s) AS all_schemes
        WITH req, c, all_schemes,
             [s IN all_schemes WHERE c.goal_tags IS NULL OR size(c.goal_tags) = 0 OR s.tags IS NULL OR ANY(tag IN s.tags WHERE tag IN c.goal_tags)] AS goal_schemes
        RETURN req.category AS category, req.id AS req_id, req.name AS req_name, req.description AS req_description, size(goal_schemes) AS goal_scheme_count, size(all_schemes) AS total_scheme_count
        ORDER BY goal_scheme_count DESC, total_scheme_count DESC
        LIMIT 1
        """

        rows = self.db.run_query(query, {"profile_id": profile_id})
        if not rows:
            logger.info("get_next_question: no unanswered requirements for id=%s", profile_id)
            return None

        row = rows[0]
        category: str = row["category"]
        goal_scheme_count: int = row["goal_scheme_count"]
        total_scheme_count: int = row["total_scheme_count"]

        template = _QUESTION_MAP.get(category)
        if not template:
            logger.warning("get_next_question: unknown category '%s'", category)
            return None

        question_id = f"Q-{category.upper().replace('_', '-')}-{profile_id[:8]}"

        if goal_scheme_count > 0:
            context = f"This unlocks {goal_scheme_count} schemes related to your goal."
        elif total_scheme_count > 0:
            context = f"This unlocks {total_scheme_count} other schemes you may qualify for."
        else:
            context = "This helps us complete your profile."

        return NextQuestion(
            question_id=question_id,
            question_text=template["question_text"],
            question_type=template["question_type"],
            options=template["options"],
            context=context,
            schemes_unlocked_estimate=goal_scheme_count or total_scheme_count,
            category=category,
        )

    # ------------------------------------------------------------------
    # Scheme detail
    # ------------------------------------------------------------------

    def get_scheme_detail(self, scheme_id: str) -> Optional[SchemeDetail]:
        """Fetch complete metadata for a single scheme node.

        Args:
            scheme_id: The Scheme node's id property.

        Returns:
            A SchemeDetail, or None if the scheme is not found.
        """
        # We use this query to pull every single piece of metadata about a scheme 
        # so the frontend can render the detail page.
        # We use OPTIONAL MATCH for requirements and prerequisites so the query still 
        # succeeds even if a scheme is totally unconditional (no requirements).
        query = """
        MATCH (s:Scheme {id: $scheme_id})
        OPTIONAL MATCH (s)-[:REQUIRES]->(req:Requirement)
        OPTIONAL MATCH (s)-[:PREREQUISITE]->(pre:Scheme)
        OPTIONAL MATCH (s)-[:EXCLUSIVE_WITH]->(excl:Scheme)
        RETURN
            s.id                  AS id,
            s.name                AS name,
            s.description         AS description,
            s.ministry            AS ministry,
            s.benefit_amount      AS benefit_amount,
            s.benefit_type        AS benefit_type,
            s.application_url     AS application_url,
            s.official_link       AS official_link,
            collect(DISTINCT {
                id:          req.id,
                name:        req.name,
                description: req.description,
                category:    req.category,
                mandatory:   req.mandatory
            })                    AS requirements,
            collect(DISTINCT pre.id)  AS prerequisite_schemes,
            collect(DISTINCT excl.id) AS mutually_exclusive_with
        """

        rows = self.db.run_query(query, {"scheme_id": scheme_id})
        if not rows:
            logger.warning("get_scheme_detail: scheme not found (id=%s)", scheme_id)
            return None

        row = rows[0]
        # Filter out null placeholder from empty OPTIONAL MATCH collects
        requirements = [r for r in (row.get("requirements") or []) if r.get("id")]
        prerequisites = [p for p in (row.get("prerequisite_schemes") or []) if p]
        exclusives = [e for e in (row.get("mutually_exclusive_with") or []) if e]

        try:
            return SchemeDetail(
                id=row["id"],
                name=row["name"],
                description=row.get("description") or "",
                ministry=row.get("ministry") or "",
                benefit_amount=row.get("benefit_amount"),
                benefit_type=row.get("benefit_type"),
                application_url=row.get("application_url"),
                official_link=row.get("official_link"),
                requirements=requirements,
                prerequisite_schemes=prerequisites,
                mutually_exclusive_with=exclusives,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("get_scheme_detail: model validation failed: %s | row=%s", exc, row)
            return None
