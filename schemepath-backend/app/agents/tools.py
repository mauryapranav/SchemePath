"""Agent tools for SchemePath Gemini function calling."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

from google.genai import types

from app.adapters.registry import get_registry
from app.config import get_settings
from app.models import CitizenProfileUpdate, ParsedProfile
from app.neo4j_client import Neo4jClient
from app.services.graph_service import GraphService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def analyze_intent(message: str) -> str:
    """Analyze a user message to extract goals and demographics."""
    logger.info("Tool called: analyze_intent")
    # For a real implementation we'd use GeminiService.parse_citizen_input
    # but since this is called BY Gemini itself, we can skip the extra LLM call
    # and just tell the model to extract it internally.
    return json.dumps({
        "status": "success",
        "instruction": "Based on the user's message, infer their goal, location, and demographic details internally before calling search_schemes."
    })


def search_schemes(intent_tags: str, state: str = "") -> str:
    """Search for government schemes matching user's intent."""
    logger.info("Tool called: search_schemes(tags=%s, state=%s)", intent_tags, state)
    tags_list = [t.strip() for t in intent_tags.split(",") if t.strip()]
    registry = get_registry()
    results = registry.search_schemes(tags_list, state or None)
    
    # Return top 5
    top = sorted(results, key=lambda x: x.relevance_score, reverse=True)[:5]
    
    return json.dumps({
        "status": "success",
        "schemes": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "benefit_amount": s.benefit_amount,
                "relevance_score": s.relevance_score
            } for s in top
        ]
    })


def check_eligibility(session_id: str, scheme_id: str) -> str:
    """Check user's eligibility for a specific scheme."""
    logger.info("Tool called: check_eligibility(session=%s, scheme=%s)", session_id, scheme_id)
    settings = get_settings()
    client = Neo4jClient(settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    try:
        service = GraphService(client)
        full_map = service.get_eligibility_map(session_id)
        
        # Find the specific scheme
        for category in [full_map.confirmed_schemes, full_map.one_step_schemes, full_map.locked_schemes]:
            for s in category:
                if s.scheme_id == scheme_id:
                    return json.dumps({
                        "status": "success",
                        "eligibility_status": s.status,
                        "benefit_amount": s.benefit_amount,
                        "missing_requirements": [r["name"] for r in s.missing_requirements],
                        "next_steps": [n["action"] for n in s.next_steps]
                    })
        return json.dumps({"status": "not_found", "message": "Scheme not found in eligibility map."})
    finally:
        client.close()


def get_document_guide(document_id: str, state: str = "") -> str:
    """Get step-by-step procurement guide for a document."""
    logger.info("Tool called: get_document_guide(doc=%s)", document_id)
    registry = get_registry()
    guide = registry.get_document_guide(document_id, state or None)
    if not guide:
        return json.dumps({"status": "not_found", "message": f"No guide found for {document_id}"})
    
    return json.dumps({
        "status": "success",
        "document_name": guide.document_name,
        "total_days": guide.total_estimated_days,
        "total_cost": guide.total_estimated_cost,
        "steps": [
            {
                "number": step.step_number,
                "action": step.action,
                "location": step.location,
                "days": step.estimated_days,
                "cost": step.cost,
                "prerequisites": step.prerequisites
            } for step in guide.steps
        ]
    })


def update_user_profile(session_id: str, field: str, value: str) -> str:
    """Update a field on the user's profile."""
    logger.info("Tool called: update_user_profile(field=%s, value=%s)", field, value)
    settings = get_settings()
    client = Neo4jClient(settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    try:
        service = GraphService(client)
        update_data = {}
        
        if field == "add_document":
            update_data["has_documents"] = [value]
        elif field == "age":
            update_data["age"] = int(value)
        elif hasattr(CitizenProfileUpdate, field):
            update_data[field] = value
        else:
            return json.dumps({"status": "error", "message": f"Invalid field {field}"})
            
        update = CitizenProfileUpdate(**update_data)
        service.update_profile(session_id, update)
        return json.dumps({"status": "success", "updated_field": field, "value": value})
    finally:
        client.close()


def enrich_scheme(scheme_name: str, scheme_id: str) -> str:
    """Enrich a scheme with latest live information from the web."""
    logger.info("Tool called: enrich_scheme(name=%s, id=%s)", scheme_name, scheme_id)
    registry = get_registry()
    
    # Find the web enrichment adapter explicitly
    web_adapter = None
    for name, adapter in registry._adapters:
        if name == "web_enrichment":
            web_adapter = adapter
            break
            
    if not web_adapter:
        return json.dumps({"status": "error", "message": "Web enrichment adapter not available"})
        
    try:
        # We know it has the enrich_scheme method
        data = web_adapter.enrich_scheme(scheme_name, scheme_id)
        if data:
            return json.dumps({"status": "success", "data": data})
        else:
            return json.dumps({"status": "not_found", "message": "No enrichment data found"})
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


def get_eligibility_graph(session_id: str) -> str:
    """Generate full eligibility graph for visualization."""
    logger.info("Tool called: get_eligibility_graph")
    # Tell the model we generated it, the actual generation will happen in the router
    return json.dumps({
        "status": "success",
        "message": "Graph data requested. Send a 'graph_data' structured message to the frontend."
    })


# ---------------------------------------------------------------------------
# Tool Declarations for Gemini
# ---------------------------------------------------------------------------

search_schemes_decl = types.FunctionDeclaration(
    name="search_schemes",
    description="Search for government schemes matching user's intent. ALWAYS call this when a user describes their situation.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "intent_tags": types.Schema(type=types.Type.STRING, description="Comma-separated tags (e.g. 'housing, rural, farming')"),
            "state": types.Schema(type=types.Type.STRING, description="Indian state name if known"),
        },
        required=["intent_tags"],
    ),
)

check_eligibility_decl = types.FunctionDeclaration(
    name="check_eligibility",
    description="Check user's eligibility status for a specific scheme.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "session_id": types.Schema(type=types.Type.STRING, description="Current session ID"),
            "scheme_id": types.Schema(type=types.Type.STRING, description="ID of the scheme (e.g. PMAY-G-2026)"),
        },
        required=["session_id", "scheme_id"],
    ),
)

get_document_guide_decl = types.FunctionDeclaration(
    name="get_document_guide",
    description="Get a step-by-step guide on how to obtain a specific document.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "document_id": types.Schema(type=types.Type.STRING, description="ID of the document (e.g. DOC-LAND-RECORD)"),
            "state": types.Schema(type=types.Type.STRING, description="Indian state name if known"),
        },
        required=["document_id"],
    ),
)

update_user_profile_decl = types.FunctionDeclaration(
    name="update_user_profile",
    description="Update user demographic info or mark a document as obtained.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "session_id": types.Schema(type=types.Type.STRING, description="Current session ID"),
            "field": types.Schema(type=types.Type.STRING, description="Field to update (e.g., 'add_document', 'state', 'age')"),
            "value": types.Schema(type=types.Type.STRING, description="Value to set (e.g., 'DOC-RATION', 'Karnataka')"),
        },
        required=["session_id", "field", "value"],
    ),
)

get_eligibility_graph_decl = types.FunctionDeclaration(
    name="get_eligibility_graph",
    description="Generate the full eligibility graph when the user asks to see everything.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "session_id": types.Schema(type=types.Type.STRING, description="Current session ID"),
        },
        required=["session_id"],
    ),
)

enrich_scheme_decl = types.FunctionDeclaration(
    name="enrich_scheme",
    description="Fetch live, real-time web data about a scheme (like latest benefit amounts or changes). Call this when user asks for the latest news or live details about a scheme.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "scheme_name": types.Schema(type=types.Type.STRING, description="Name of the scheme"),
            "scheme_id": types.Schema(type=types.Type.STRING, description="ID of the scheme"),
        },
        required=["scheme_name", "scheme_id"],
    ),
)

# Function dispatch map
TOOL_FUNCTIONS = {
    "search_schemes": search_schemes,
    "check_eligibility": check_eligibility,
    "get_document_guide": get_document_guide,
    "update_user_profile": update_user_profile,
    "get_eligibility_graph": get_eligibility_graph,
    "enrich_scheme": enrich_scheme,
}

TOOL_CONFIG = types.Tool(
    function_declarations=[
        search_schemes_decl,
        check_eligibility_decl,
        get_document_guide_decl,
        update_user_profile_decl,
        get_eligibility_graph_decl,
        enrich_scheme_decl,
    ]
)
