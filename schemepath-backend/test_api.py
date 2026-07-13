import sys
from fastapi.testclient import TestClient
from app.main import app

def main():
    with TestClient(app) as client:
        # First create a profile
        resp = client.post("/profile/create", json={"raw_input": "I am a 30 year old male from Maharashtra"})
        print(resp.status_code, resp.json())
        pid = resp.json().get("id")
        
        # Now get eligibility map
        resp2 = client.get(f"/eligibility/map/{pid}")
        print("Map status:", resp2.status_code)
        print("Map response:", resp2.json())

if __name__ == "__main__":
    main()
