"""WebSocket and REST chat endpoints."""
from __future__ import annotations

import json
import logging
from typing import Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agents.agent import SchemePathAgent
from app.models import CitizenProfileCreate, ParsedProfile
from app.neo4j_client import Neo4jClient
from app.services.graph_service import GraphService
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])

# One agent instance per worker
agent = SchemePathAgent()


def _ensure_profile_exists(session_id: str, initial_message: str):
    """Create a basic profile if it doesn't exist."""
    settings = get_settings()
    client = Neo4jClient(settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    try:
        service = GraphService(client)
        # We just create a minimal profile with the session_id
        # The agent will update it via tools later
        from app.models import ParsedProfile
        profile = ParsedProfile(goal=initial_message, confidence_score=0.1)
        
        # Override the random UUID generation in GraphService to use our session_id
        # This is a bit of a hack but avoids changing graph_service.py
        create_query = """
        MERGE (c:CitizenProfile {id: $id})
        ON CREATE SET
            c.goal = $goal,
            c.confidence_score = $confidence_score,
            c.created_at = datetime(),
            c.updated_at = datetime()
        """
        client.run_query(create_query, {
            "id": session_id,
            "goal": profile.goal,
            "confidence_score": profile.confidence_score
        })
    finally:
        client.close()


def _get_graph_data(session_id: str) -> Dict[str, Any]:
    """Generate graph data for React Flow."""
    settings = get_settings()
    client = Neo4jClient(settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    try:
        service = GraphService(client)
        full_map = service.get_eligibility_map(session_id)
        
        nodes = []
        edges = []
        
        # User node
        nodes.append({"id": "you", "label": "YOU", "type": "user", "status": "have"})
        
        # We need a simplified graph for the drawer
        # Just schemes and their missing requirements
        doc_nodes = set()
        
        for category, status in [
            (full_map.confirmed_schemes, "confirmed"),
            (full_map.one_step_schemes, "one_step"),
            (full_map.locked_schemes, "locked")
        ]:
            for s in category:
                nodes.append({
                    "id": s.scheme_id,
                    "label": s.scheme_name,
                    "type": "scheme",
                    "status": status
                })
                
                # Edges from YOU to scheme (direct if confirmed)
                if status == "confirmed":
                    edges.append({
                        "source": "you", "target": s.scheme_id,
                        "label": "Eligible", "satisfied": True
                    })
                else:
                    # Add missing requirements
                    for req in s.missing_requirements:
                        req_id = req["id"]
                        if req_id not in doc_nodes:
                            nodes.append({
                                "id": req_id,
                                "label": req["name"],
                                "type": "document",
                                "status": "missing"
                            })
                            doc_nodes.add(req_id)
                            # Edge from YOU to requirement (missing)
                            edges.append({
                                "source": "you", "target": req_id,
                                "label": "Missing", "satisfied": False
                            })
                        
                        # Edge from requirement to scheme
                        edges.append({
                            "source": req_id, "target": s.scheme_id,
                            "label": "Requires", "satisfied": False
                        })
                        
        return {"nodes": nodes, "edges": edges}
    finally:
        client.close()


@router.websocket("/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    logger.info("WebSocket connected: session=%s", session_id)
    
    first_message = True
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            msg_type = message.get("type")
            content = ""
            
            if msg_type == "user_message":
                content = message.get("content", "")
                if first_message:
                    _ensure_profile_exists(session_id, content)
                    first_message = False
            elif msg_type == "document_response":
                doc_id = message.get("document_id")
                status = message.get("status")
                content = f"I {status.replace('_', ' ')} the document {doc_id}."
            elif msg_type == "request_graph":
                graph_data = _get_graph_data(session_id)
                await websocket.send_json({
                    "type": "graph_data",
                    "nodes": graph_data["nodes"],
                    "edges": graph_data["edges"]
                })
                continue
            else:
                logger.warning("Unknown message type: %s", msg_type)
                continue
                
            # Process with agent
            async for response in agent.chat(session_id, content):
                # Intercept graph render request
                if response.get("type") == "request_graph_render":
                    graph_data = _get_graph_data(session_id)
                    await websocket.send_json({
                        "type": "graph_data",
                        "nodes": graph_data["nodes"],
                        "edges": graph_data["edges"]
                    })
                else:
                    await websocket.send_json(response)
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: session=%s", session_id)
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass


@router.post("/{session_id}")
async def chat_rest(session_id: str, request: Dict[str, Any]):
    """REST fallback for environments without WebSocket support."""
    content = request.get("message", "")
    _ensure_profile_exists(session_id, content)
    
    responses = []
    async for response in agent.chat(session_id, content):
        if response.get("type") == "request_graph_render":
            graph_data = _get_graph_data(session_id)
            responses.append({
                "type": "graph_data",
                "nodes": graph_data["nodes"],
                "edges": graph_data["edges"]
            })
        else:
            responses.append(response)
            
    return {"responses": responses}


@router.get("/{session_id}/history")
async def get_history(session_id: str):
    """Retrieve conversation history (simplified)."""
    # In a real app we'd fetch this from DB, but here we just read memory
    history = agent._get_history(session_id)
    return {
        "messages": [
            {"role": content.role, "parts": len(content.parts)} 
            for content in history if content.role in ["user", "model"]
        ]
    }
