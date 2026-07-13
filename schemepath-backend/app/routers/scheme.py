from fastapi import APIRouter, Depends, HTTPException
from app.services.graph_service import GraphService
from app.config import get_settings
from app.neo4j_client import Neo4jClient
from app.models import SchemeDetail

router = APIRouter(prefix="/scheme", tags=["Schemes"])

def get_graph_service():
    settings = get_settings()
    client = Neo4jClient(settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    return GraphService(client)

@router.get("/{scheme_id}", response_model=SchemeDetail)
def get_scheme_detail(scheme_id: str, graph: GraphService = Depends(get_graph_service)):
    # We use this to return the full details of a specific scheme.
    # The frontend uses this to render the scheme detail page.
    scheme = graph.get_scheme_detail(scheme_id)
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    return scheme
