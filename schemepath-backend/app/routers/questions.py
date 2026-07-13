from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Any, Dict
from app.services.graph_service import GraphService
from app.services.gemini_service import GeminiService
from app.services.question_engine import QuestionEngine
from app.models import CitizenProfileUpdate
from app.config import get_settings
from app.neo4j_client import Neo4jClient

router = APIRouter(prefix="/questions", tags=["Questions"])

def get_question_engine():
    settings = get_settings()
    client = Neo4jClient(settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    graph = GraphService(client)
    gemini = GeminiService(api_key=settings.GEMINI_API_KEY)
    return QuestionEngine(graph, gemini)

def get_graph_service():
    settings = get_settings()
    client = Neo4jClient(settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    return GraphService(client)

class AnswerPayload(BaseModel):
    question_id: str
    answer: Any

@router.get("/next/{profile_id}")
def get_next_question(profile_id: str, engine: QuestionEngine = Depends(get_question_engine)):
    # We use this to figure out the single most important question to ask the user next.
    # It analyzes the graph to find which missing requirement blocks the most schemes,
    # so we can ask about that and save the user's time.
    next_q = engine.get_next_question(profile_id)
    if not next_q:
        # We return a message here because returning null could break clients expecting an object.
        # It's a graceful way to say "you're done answering questions".
        return {"message": "Profile complete! View your eligibility map."}
    return next_q

@router.post("/answer/{profile_id}")
def answer_question(
    profile_id: str,
    payload: AnswerPayload,
    graph: GraphService = Depends(get_graph_service),
    engine: QuestionEngine = Depends(get_question_engine)
):
    # Map the category from question_id to the right field
    # e.g. Q-DOCUMENT-1234 -> document
    parts = payload.question_id.split("-")
    if len(parts) > 1:
        category = parts[1].lower()
        update_dict = {}
        if category == "document":
            update_dict["has_documents"] = payload.answer
        elif category == "land":
            update_dict["has_land"] = payload.answer
        elif category == "income":
            update_dict["family_income_annual"] = payload.answer
        elif category == "bank":
            update_dict["has_bank_account"] = payload.answer
        elif category == "bank_account":
            update_dict["has_bank_account"] = payload.answer
            
        if update_dict:
            update = CitizenProfileUpdate(**update_dict)
            graph.update_profile(profile_id, update)
            
            # If the user answered that they have these things, we should automatically create the underlying asset 
            # so the graph eligibility query picks it up immediately.
            if category == "bank_account" and payload.answer is True:
                # User has a bank account, link DOC-BANK-AC
                graph.update_profile(profile_id, CitizenProfileUpdate(has_documents=["DOC-BANK-AC"]))
            elif category == "income" and isinstance(payload.answer, str):
                # We can map the bracket directly as a property for later or use it to fulfill income
                pass
            elif category == "land" and payload.answer == "own":
                # User owns land, ideally they have a record
                pass

    next_q = engine.get_next_question(profile_id)
    if not next_q:
        return {"message": "Profile complete! View your eligibility map."}
    return next_q
