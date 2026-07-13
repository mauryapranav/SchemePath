import sys
from app.neo4j_client import Neo4jClient
from app.services.graph_service import GraphService
from app.models import ParsedProfile
from app.config import get_settings

def main():
    settings = get_settings()
    client = Neo4jClient(settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    try:
        client.verify_connectivity()
        gs = GraphService(client)
        # Create a complete profile
        profile = ParsedProfile(
            age=30, gender="Male", caste="General", state="MH",
            location_type="Urban", family_income_annual=50000,
            occupation="Farmer", goal="Subsidy", confidence_score=0.9,
            mentioned_documents=["DOC-AADHAAR", "DOC-BANK-AC", "DOC-LAND-RECORD", "DOC-RATION", "DOC-VENDOR-CERT", "DOC-NREGA-JOBCARD"], 
            missing_information=[]
        )
        pid = gs.create_profile(profile)
        
        # Test completion
        comp = gs.get_eligibility_map(pid)
        print("Completion:", comp.profile_completion)
        print("Confirmed:", len(comp.confirmed_schemes))
        print("One step:", len(comp.one_step_schemes))
        print("Locked:", len(comp.locked_schemes))

    finally:
        client.close()

if __name__ == "__main__":
    main()
