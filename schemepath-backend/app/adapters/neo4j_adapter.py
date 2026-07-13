"""Neo4j adapter — primary data source for curated scheme data.

Wraps all Neo4j Cypher queries behind the SchemeDataSource interface so the
agent layer never touches raw database logic.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.adapters.base import (
    DocumentGuide,
    ProcurementStep,
    SchemeDataSource,
    SchemeDetailResult,
    SchemeResult,
)
from app.config import get_settings
from app.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


def _get_client() -> Neo4jClient:
    s = get_settings()
    return Neo4jClient(s.NEO4J_URI, s.NEO4J_USER, s.NEO4J_PASSWORD)


class Neo4jSeedAdapter(SchemeDataSource):
    """Reads scheme, requirement, and document data from the Neo4j graph."""

    # ------------------------------------------------------------------
    # search_schemes — tag-based intent matching
    # ------------------------------------------------------------------

    def search_schemes(
        self, intent_tags: List[str], state: Optional[str] = None
    ) -> List[SchemeResult]:
        if not intent_tags:
            query = """
            MATCH (s:Scheme {active: true})
            RETURN s.id AS id, s.name AS name, s.description AS description,
                   s.benefit_amount AS benefit_amount, s.benefit_type AS benefit_type,
                   s.tags AS tags, s.application_url AS application_url
            ORDER BY s.name
            """
            params: Dict[str, Any] = {}
        else:
            query = """
            MATCH (s:Scheme {active: true})
            WHERE ANY(tag IN s.tags WHERE tag IN $tags)
            WITH s, size([tag IN s.tags WHERE tag IN $tags]) AS overlap
            RETURN s.id AS id, s.name AS name, s.description AS description,
                   s.benefit_amount AS benefit_amount, s.benefit_type AS benefit_type,
                   s.tags AS tags, s.application_url AS application_url,
                   overlap
            ORDER BY overlap DESC, s.name
            """
            params = {"tags": intent_tags}

        client = _get_client()
        try:
            rows = client.run_query(query, params)
            results = []
            for r in rows:
                results.append(SchemeResult(
                    id=r["id"],
                    name=r["name"],
                    description=r.get("description") or "",
                    benefit_amount=r.get("benefit_amount"),
                    benefit_type=r.get("benefit_type"),
                    tags=r.get("tags") or [],
                    application_url=r.get("application_url"),
                    relevance_score=float(r.get("overlap", 0)),
                ))
            return results
        finally:
            client.close()

    # ------------------------------------------------------------------
    # get_scheme_details
    # ------------------------------------------------------------------

    def get_scheme_details(self, scheme_id: str) -> Optional[SchemeDetailResult]:
        query = """
        MATCH (s:Scheme {id: $scheme_id})
        OPTIONAL MATCH (s)-[req:REQUIRES]->(r:Requirement)
        OPTIONAL MATCH (s)-[:PREREQUISITE]->(pre:Scheme)
        RETURN s.id AS id, s.name AS name, s.description AS description,
               s.ministry AS ministry, s.benefit_amount AS benefit_amount,
               s.benefit_type AS benefit_type, s.application_url AS application_url,
               s.official_link AS official_link,
               s.estimated_time_days AS estimated_time_days,
               s.estimated_cost AS estimated_cost,
               collect(DISTINCT {
                   id: r.id, name: r.name, description: r.description,
                   category: r.category, mandatory: req.mandatory
               }) AS requirements,
               collect(DISTINCT pre.id) AS prerequisite_schemes
        """
        client = _get_client()
        try:
            rows = client.run_query(query, {"scheme_id": scheme_id})
            if not rows:
                return None
            row = rows[0]
            reqs = [r for r in (row.get("requirements") or []) if r.get("id")]
            prereqs = [p for p in (row.get("prerequisite_schemes") or []) if p]
            return SchemeDetailResult(
                id=row["id"], name=row["name"],
                description=row.get("description") or "",
                ministry=row.get("ministry") or "",
                benefit_amount=row.get("benefit_amount"),
                benefit_type=row.get("benefit_type"),
                application_url=row.get("application_url"),
                official_link=row.get("official_link"),
                requirements=reqs, prerequisite_schemes=prereqs,
                estimated_time_days=row.get("estimated_time_days"),
                estimated_cost=row.get("estimated_cost"),
            )
        finally:
            client.close()

    # ------------------------------------------------------------------
    # get_eligibility_rules
    # ------------------------------------------------------------------

    def get_eligibility_rules(self, scheme_id: str) -> List[Dict[str, Any]]:
        query = """
        MATCH (s:Scheme {id: $scheme_id})-[req:REQUIRES]->(r:Requirement)
        OPTIONAL MATCH (r)<-[:FULFILLED_BY]-(f)
        RETURN r.id AS id, r.name AS name, r.description AS description,
               r.category AS category, req.mandatory AS mandatory,
               labels(f)[0] AS fulfilled_by_type, f.id AS fulfilled_by_id
        ORDER BY req.order
        """
        client = _get_client()
        try:
            rows = client.run_query(query, {"scheme_id": scheme_id})
            return rows
        finally:
            client.close()

    # ------------------------------------------------------------------
    # get_document_guide
    # ------------------------------------------------------------------

    def get_document_guide(
        self, document_id: str, state: Optional[str] = None
    ) -> Optional[DocumentGuide]:
        query = """
        MATCH (d:Document {id: $document_id})
        OPTIONAL MATCH (ps:ProcessStep)-[:PRODUCES]->(d)
        OPTIONAL MATCH (ps)-[:REQUIRES_DOC]->(req_doc:Document)
        RETURN d.name AS doc_name,
               ps.id AS step_id, ps.name AS step_name,
               ps.description AS step_desc, ps.location AS location,
               ps.estimated_days AS est_days, ps.cost_inr AS cost_inr,
               ps.cost_label AS cost_label,
               collect(DISTINCT req_doc.name) AS required_docs
        """
        client = _get_client()
        try:
            rows = client.run_query(query, {"document_id": document_id})
            if not rows:
                return None
            doc_name = rows[0].get("doc_name") or document_id
            steps = []
            total_days = 0
            for i, r in enumerate(rows):
                if not r.get("step_id"):
                    continue
                est = r.get("est_days") or 0
                total_days += est
                cost = r.get("cost_label") or (f"₹{r.get('cost_inr', 0)}" if r.get("cost_inr") else "Free")
                steps.append(ProcurementStep(
                    step_number=i + 1,
                    action=r.get("step_desc") or r.get("step_name") or "",
                    location=r.get("location") or "Local government office",
                    estimated_days=est,
                    cost=cost,
                    prerequisites=r.get("required_docs") or [],
                ))
            return DocumentGuide(
                document_id=document_id,
                document_name=doc_name,
                steps=steps,
                total_estimated_days=total_days,
                total_estimated_cost=steps[0].cost if steps else "Free",
            )
        finally:
            client.close()
