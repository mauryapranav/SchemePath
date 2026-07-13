# SchemePath — Deployment Guide

> **HackHazards '26 · Neo4j Track**
> Stack: FastAPI (Render) · Next.js 14 (Vercel) · Neo4j AuraDB · Google Gemini

---

## Prerequisites

| Tool | Purpose | Install |
|---|---|---|
| `git` | version control | [git-scm.com](https://git-scm.com) |
| `python 3.11+` | local backend dev | [python.org](https://python.org) |
| `node 18+` | local frontend dev | [nodejs.org](https://nodejs.org) |
| `cypher-shell` (optional) | run seed script from CLI | [neo4j.com/download](https://neo4j.com/download) |

---

## Step 1 — Neo4j AuraDB (Free Tier)

1. Go to [console.neo4j.io](https://console.neo4j.io) → **New Instance** → select **AuraDB Free**.
2. Choose region closest to your Render deployment (e.g. Singapore).
3. Download the generated credentials file — it contains:
   ```
   NEO4J_URI      = neo4j+s://xxxxxxxx.databases.neo4j.io
   NEO4J_USERNAME = neo4j
   NEO4J_PASSWORD = <generated-password>
   ```
4. Wait for the instance to reach **Running** state (≈ 2 min).

> [!IMPORTANT]
> Save these credentials — you won't be able to retrieve the password again.

---

## Step 2 — Seed the Graph Database

### Option A — Neo4j Browser (easiest)

1. Open your AuraDB instance → click **Open with Neo4j Browser**.
2. Log in with your credentials.
3. Open `schemepath-backend/seed.cypher` in a text editor.
4. Paste the entire contents into the Neo4j Browser query box.
5. Press **Run** (▶).
6. Verify with:
   ```cypher
   MATCH (s:Scheme) RETURN s.id, s.name, s.active ORDER BY s.id;
   ```
   You should see **5 rows**.

### Option B — cypher-shell (CLI)

```bash
cypher-shell \
  -a neo4j+s://<your-instance>.databases.neo4j.io \
  -u neo4j \
  -p "<your-password>" \
  --file schemepath-backend/seed.cypher
```

---

## Step 3 — Google Gemini API Key

1. Go to [aistudio.google.com](https://aistudio.google.com) → **Get API key** → **Create API key**.
2. Copy the key — you'll need it as `GEMINI_API_KEY`.

> [!NOTE]
> The free tier is sufficient for hackathon demo (60 requests/minute).

---

## Step 4 — Deploy Backend to Render

### Option A — render.yaml (recommended)

1. Push `schemepath-backend/` to a GitHub repository (can be a monorepo).
2. Go to [dashboard.render.com](https://dashboard.render.com) → **New** → **Web Service**.
3. Connect your GitHub repo.
4. Render will detect `render.yaml` and auto-configure the service.
5. In **Environment Variables**, add:

   | Key | Value |
   |---|---|
   | `NEO4J_URI` | `neo4j+s://xxxxxxxx.databases.neo4j.io` |
   | `NEO4J_USER` | `neo4j` |
   | `NEO4J_PASSWORD` | `<your-aura-password>` |
   | `GEMINI_API_KEY` | `<your-gemini-key>` |

6. Click **Deploy** — build takes ~2 min.

### Option B — Docker deploy

```bash
cd schemepath-backend
docker build -t schemepath-api .
docker run -p 8000:8000 \
  -e NEO4J_URI="neo4j+s://..." \
  -e NEO4J_USER="neo4j" \
  -e NEO4J_PASSWORD="..." \
  -e GEMINI_API_KEY="..." \
  schemepath-api
```

### Verify backend

```bash
curl https://schemepath-api.onrender.com/health
# Expected: {"status":"ok","neo4j_connected":true}
```

> [!WARNING]
> Render free tier spins down after 15 min of inactivity. First request after sleep takes ~30 s.
> Consider upgrading to **Starter ($7/month)** for always-on before the demo.

---

## Step 5 — Deploy Frontend to Vercel

1. Push `schemepath-frontend/` to GitHub (same or separate repo).
2. Go to [vercel.com/new](https://vercel.com/new) → **Import Git Repository**.
3. Select the repo / set **Root Directory** to `schemepath-frontend`.
4. Vercel auto-detects Next.js — no framework config needed.
5. Under **Environment Variables**, add:

   | Key | Value |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | `https://schemepath-api.onrender.com` |

6. Click **Deploy** — build takes ~1 min.
7. Your app will be live at `https://schemepath-frontend.vercel.app` (or custom domain).

> [!TIP]
> The `vercel.json` includes an `/api/*` rewrite proxy. You can alternatively set
> `NEXT_PUBLIC_API_URL=/api` to route all API calls through Vercel's edge network
> (eliminates CORS entirely).

---

## Step 6 — End-to-End Verification

```bash
# 1. Health check
curl https://schemepath-api.onrender.com/health

# 2. Create a profile
curl -X POST https://schemepath-api.onrender.com/profile/create \
  -H "Content-Type: application/json" \
  -d '{"raw_input": "I am a farmer in Bihar with 2 acres of land and an Aadhaar card"}'
# Note the returned profile `id`

# 3. Get next question
curl https://schemepath-api.onrender.com/questions/next/<profile-id>

# 4. Get eligibility map
curl https://schemepath-api.onrender.com/eligibility/map/<profile-id>

# 5. Open frontend
open https://schemepath-frontend.vercel.app
# Type a description → answer questions → view your eligibility map
```

---

## Local Development

### Backend

```bash
cd schemepath-backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt

copy .env.example .env          # Windows
# cp .env.example .env          # macOS/Linux
# → fill in NEO4J_* and GEMINI_API_KEY

uvicorn app.main:app --reload
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Frontend

```bash
cd schemepath-frontend
npm install

copy .env.local.example .env.local    # Windows
# cp .env.local.example .env.local    # macOS/Linux
# NEXT_PUBLIC_API_URL=http://localhost:8000

npm run dev
# App: http://localhost:3000
```

---

## Architecture Overview

```
Browser (Vercel)
    │  HTTP / HTTPS
    ▼
Next.js 14 App Router
    │  axios → NEXT_PUBLIC_API_URL
    ▼
FastAPI (Render)
    │  neo4j driver (async + sync)       │  google-genai SDK
    ▼                                     ▼
Neo4j AuraDB                         Gemini 1.5 Flash
(Graph of Schemes,                   (Profile parsing +
 Requirements, Documents)             Question context)
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `health` returns `neo4j_connected: false` | Wrong credentials or AuraDB paused | Re-check env vars; unpause AuraDB |
| `ValidationError` on `/profile/create` | Missing env var at startup | Check Render logs; ensure all 4 vars are set |
| Gemini returns empty or blocked response | API key invalid or quota exceeded | Check [aistudio.google.com](https://aistudio.google.com) quota |
| Frontend CORS errors | `NEXT_PUBLIC_API_URL` missing or wrong | Re-deploy Vercel with correct env var |
| Render cold start timeout | Free tier spin-down | Wait 30 s or upgrade to Starter plan |
| `cypher-shell` seed fails | AuraDB firewall | Use Neo4j Browser instead |

---

*Built by the SchemePath team for HackHazards '26 — Neo4j Track.*
