from fastapi import APIRouter, Depends, HTTPException
from app.services.graph_service import GraphService
from app.config import get_settings
from app.neo4j_client import Neo4jClient
from app.models import EligibilityMap, EligibilityPath

router = APIRouter(prefix="/eligibility", tags=["Eligibility"])

def get_graph_service():
    settings = get_settings()
    client = Neo4jClient(settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    return GraphService(client)

@router.get("/map/{profile_id}", response_model=EligibilityMap)
def get_eligibility_map(profile_id: str, graph: GraphService = Depends(get_graph_service)):
    # We use this to calculate exactly where the citizen stands for every active scheme.
    # It traverses the graph to see what they have and what they're missing, 
    # letting us group schemes into confirmed, one_step, and locked buckets.
    return graph.get_eligibility_map(profile_id)

@router.get("/path/{profile_id}/{scheme_id}")
def get_eligibility_path(profile_id: str, scheme_id: str, graph: GraphService = Depends(get_graph_service)):
    # We use this to give the citizen a detailed breakdown of a single scheme.
    # Rather than running a new query, we filter the full eligibility map 
    # to find the specific path they're interested in.
    emap = graph.get_eligibility_map(profile_id)
    for scheme_list in [emap.confirmed_schemes, emap.one_step_schemes, emap.locked_schemes]:
        for scheme in scheme_list:
            if scheme.scheme_id == scheme_id:
                return scheme
    
    # We raise an error here because if the scheme isn't in any of the buckets,
    # it means it either doesn't exist or isn't active in our database.
    raise HTTPException(status_code=404, detail="Scheme path not found for this profile")
