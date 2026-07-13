from fastapi import APIRouter, Depends
from app.models import CitizenProfileCreate, CitizenProfileUpdate, ParsedProfile
from app.services.gemini_service import GeminiService
from app.services.graph_service import GraphService
from app.config import get_settings
from app.neo4j_client import Neo4jClient

router = APIRouter(prefix="/profile", tags=["Profile"])

def get_gemini_service():
    settings = get_settings()
    return GeminiService(api_key=settings.GEMINI_API_KEY)

def get_graph_service():
    settings = get_settings()
    client = Neo4jClient(settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    return GraphService(client)

@router.post("/create")
def create_profile(
    profile: CitizenProfileCreate,
    gemini: GeminiService = Depends(get_gemini_service),
    graph: GraphService = Depends(get_graph_service)
):
    # We use this to extract structured data from whatever the citizen typed.
    # It converts messy natural language into a clean JSON structure we can process.
    parsed = gemini.parse_citizen_input(profile.raw_input)
    
    # We take that structured data and save it into our graph database as a new node.
    # This acts as the starting point for their eligibility journey.
    profile_id = graph.create_profile(parsed)
    return {"id": profile_id, "parsed": parsed}

@router.patch("/{profile_id}")
def update_profile(
    profile_id: str,
    update: CitizenProfileUpdate,
    graph: GraphService = Depends(get_graph_service)
):
    # We use this to progressively build the citizen's profile as they answer questions.
    # Each answer adds more detail to their node, unlocking new scheme paths.
    graph.update_profile(profile_id, update)
    return {"status": "success", "profile_id": profile_id}
