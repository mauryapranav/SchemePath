# SchemePath — Graph-Native Eligibility Navigator for Government Welfare

**"Don't just check if you qualify. Discover your path to qualifying."**

*HackHazards '26 · Neo4j Track · AI Domain*

---

## About the Project

### The Problem Nobody Talks About

Every year, an estimated **₹50,000 crore in government welfare benefits goes unclaimed** across India — not because citizens are ineligible, but because they don't know they qualify, don't know what documents to gather first, or give up midway when told they're missing one requirement without being shown how to fix it.

The digital divide compounds this. Farmers, street vendors, and rural households — the intended beneficiaries of flagship schemes like PM-KISAN, MGNREGA, and Ayushman Bharat — are precisely the people least likely to navigate fragmented government portals, understand bureaucratic eligibility criteria, or know that one document unlocks a chain of three more schemes.

### Why Existing Tools Fall Short

Platforms like myScheme.gov.in are impressive for what they are: **filter engines**. You answer 20 questions, they return a list of matching schemes. But they treat eligibility as a boolean — you either qualify or you don't. If you're missing one requirement, the scheme disappears from your results with no guidance.

This is a fundamentally broken model. A farmer without a bank account doesn't fail to qualify for PM-KISAN — they're **one Jan Dhan account away** from qualifying. A street vendor without a Certificate of Vending isn't locked out of PM SVANidhi — the ULB can issue one in 15 days. The question was never *"Do you qualify?"* but *"What does your path to qualifying look like?"*

### The Insight: Eligibility is a Graph Problem

Government scheme eligibility has a structure that filter engines cannot capture:

- Schemes have **requirements** (documents, residence, income thresholds)
- Requirements are **fulfilled by** assets (documents you own, land you hold, schemes you're already enrolled in)
- Assets have **acquisition paths** (process steps with cost and time estimates)
- Schemes have **prerequisite chains** (PM-KISAN registration unlocks Kisan Credit Card under the bank saturation drive)

This is a **directed graph** — and the question every citizen really needs answered isn't a boolean lookup, it's a **shortest-path traversal**: *"Given the assets I currently have, what is the minimum set of steps to reach eligibility for this scheme?"*

### The Solution: SchemePath

SchemePath models the entire Indian government welfare system as a property graph in Neo4j. Schemes, Requirements, Documents, ProcessSteps, and IncomeBrackets are nodes. `REQUIRES`, `FULFILLED_BY`, `PRODUCES`, and `PREREQUISITE` are edges. A single Cypher query — leveraging Neo4j's native graph traversal — computes your complete eligibility map in one shot, classifying every active scheme as **Confirmed** (apply now), **One Step Away** (one missing requirement), or **Locked** (needs a documented path).

Citizens don't fill forms. They describe themselves in plain language. Gemini parses the natural language input into a structured profile, and the graph does the rest.

---

## Tech Stack

| Layer | Technology | Role |
|---|---|---|
| **Graph DB** | Neo4j AuraDB (Free Tier) | Scheme/requirement/document graph, eligibility traversal |
| **Backend** | FastAPI + Python 3.11 | REST API, service orchestration, lifespan management |
| **AI/NLP** | Google Gemini 1.5 Flash | Natural language profile parsing, adaptive question context |
| **Frontend** | Next.js 14 App Router | Server + client components, route-based navigation |
| **Graph UI** | React Flow | Interactive path visualization (YOU → Documents → Scheme) |
| **Deployment** | Render (backend) + Vercel (frontend) | Zero-config cloud deployment |

---

## Key Features

- **Natural language input** — Describe yourself in plain language: *"I want to start farming in Bihar"*. Gemini extracts age, gender, state, caste, income, occupation, goal, and mentioned documents into a structured profile.

- **Adaptive questioning** — The question engine queries the graph to find the highest-impact unknown variable (the requirement category blocking the most schemes), then asks only that. Citizens typically reach their eligibility map in **3–4 questions maximum**, not 20.

- **Visual eligibility map** — Three live-updated sections: ✅ **Confirmed** (apply today), ⚡ **One Step Away** (one missing thing), 🔒 **Locked** (longer path). Each section shows benefit amounts, estimated processing time, and missing requirements.

- **Interactive path visualization** — React Flow renders a live graph: YOU (green) → required Documents (blue if owned, red if missing) → target Scheme (gold star). Green solid edges are satisfied. Red dashed edges are the next suggested steps. Animated edges highlight the critical path.

- **Prerequisite chains** — The graph models cross-scheme dependencies. PM-KISAN registration is a `PREREQUISITE` for Kisan Credit Card with `auto_unlocks: true`. Enrolling in one scheme automatically propagates progress toward dependent schemes.

- **Privacy-by-architecture** — No Aadhaar numbers are collected. No login required. Sessions are anonymous UUIDs. The graph stores only derived attributes (age, state, income bracket) — never raw PII. Auto-deletion is documented in the architecture (24-hour session TTL).

---

## What Makes It Novel

Most scheme discovery tools are **rule-based matchers** — a database of conditions evaluated against user inputs. SchemePath takes a fundamentally different approach:

**The Cypher shortest-path query IS the eligibility engine.** There is no rule-based logic layer. Neo4j's native graph traversal computes eligibility, identifies missing requirements, classifies scheme status, and ranks questions by impact — all from a single connected data model.

This means:
- Adding a new scheme is a **data operation** (add nodes and edges), not a code change
- Prerequisite chains, mutual exclusions, and document dependencies are **first-class graph relationships**, not special-cased application logic
- The eligibility computation scales with the graph, not with hand-written if-else trees

To our knowledge, **this is the first tool to use graph-native traversal — not rule-based matching — to compute government scheme eligibility** in the Indian context.

---

## Challenges We Ran Into

**Balancing data richness with privacy compliance.** The graph needs enough citizen data to compute eligibility meaningfully, but collecting real demographics in a hackathon context requires careful design. We resolved this by storing only bucketed values (income brackets, not exact figures) and building the session model around anonymous UUIDs rather than identity.

**Designing a schema that handles prerequisite schemes.** A scheme can be a *requirement* for another scheme — which means a `Scheme` node must also be able to appear on the "fulfilled by" side of a `Requirement` edge. This required careful modelling of `REQ-PMKISAN-BENEFICIARY` as a `Requirement` node fulfilled by the `PM-KISAN-2026` *scheme node itself*, creating a clean cross-scheme dependency chain without schema violations.

**Making Cypher queries performant with optional relationships.** The core eligibility query uses multiple `OPTIONAL MATCH` arms, `collect(DISTINCT ...)`, and a `CASE` expression to classify scheme status — all in a single pass. Tuning this to avoid Cartesian products while handling schemes with zero requirements (the `unknown` status) required several iterations of the query plan.

**Keeping the question engine smart without over-engineering it.** The "highest-impact question" logic needed to be a graph query, not an ML model (no training data, hackathon time constraint). The final solution — `GROUP BY req.category, COUNT(DISTINCT blocking_scheme) ORDER BY DESC LIMIT 1` — is elegantly simple and genuinely useful.

---

## Accomplishments We're Proud Of

- **A complete, accurate graph model** of five real central government schemes with full requirement chains, document prerequisite dependencies, process steps (NREGA job card acquisition), and cross-scheme prerequisite relationships.

- **A working graph-native eligibility engine** — the Cypher `MATCH`/`OPTIONAL MATCH` query classifies every scheme in the database as confirmed/one_step/locked in a single traversal, with no application-layer logic involved.

- **Privacy-by-architecture** — we designed the entire system so that meaningful eligibility computation is possible without ever asking for an Aadhaar number, phone number, or any uniquely identifying information. The anonymisation is structural, not a policy.

- **Prerequisite chain propagation** — PM-KISAN correctly shows as a prerequisite for KCC, and the graph traversal surfaces this automatically without any hardcoded cross-scheme rules.

---

## What's Next

- **DPDP Act 2023 compliance framework** — Implement consent management, data minimisation audit trail, and purpose limitation documentation to align with India's new digital personal data law.

- **UIDAI DigiLocker / Aadhaar Vault integration** — In production, allow citizens to cryptographically verify document ownership via DigiLocker API, enabling the graph to automatically mark requirements as fulfilled without manual input.

- **State-wise scheme expansion** — The current graph covers five central schemes. Real impact requires integrating state welfare portals (Tamil Nadu, Maharashtra, UP) — a data ingestion challenge, not an architectural one, thanks to the graph model.

- **Multilingual NLP** — Gemini supports Hindi, Tamil, and Telugu. Extending `parse_citizen_input` to handle regional language inputs is a prompt-engineering task that could 10× the addressable population.

- **NGO / CSC partnership API** — Expose a white-label API for Common Service Centres and NGOs doing last-mile welfare delivery, so field workers can run eligibility checks offline-first with sync.

---

*Built in 48 hours for HackHazards '26 · Neo4j Track · AI Domain*
*The graph doesn't just find your schemes. It shows you the path.*
