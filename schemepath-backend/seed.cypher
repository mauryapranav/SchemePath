// =============================================================================
// SchemePath — Neo4j Schema & Seed Data
// =============================================================================
// Run this file against your Neo4j instance:
//   neo4j-admin database import  (bulk)
//   or paste into Neo4j Browser / cypher-shell
// =============================================================================


// -----------------------------------------------------------------------------
// SECTION 1 — Constraints (idempotent: CREATE IF NOT EXISTS)
// -----------------------------------------------------------------------------

CREATE CONSTRAINT scheme_id_unique     IF NOT EXISTS
  FOR (s:Scheme)       REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT requirement_id_unique IF NOT EXISTS
  FOR (r:Requirement)  REQUIRE r.id IS UNIQUE;

CREATE CONSTRAINT document_id_unique   IF NOT EXISTS
  FOR (d:Document)     REQUIRE d.id IS UNIQUE;

CREATE CONSTRAINT process_step_id_unique IF NOT EXISTS
  FOR (p:ProcessStep)  REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT income_bracket_id_unique IF NOT EXISTS
  FOR (i:IncomeBracket) REQUIRE i.id IS UNIQUE;

CREATE CONSTRAINT land_record_owner_unique IF NOT EXISTS
  FOR (l:LandRecord)   REQUIRE l.owner_id IS UNIQUE;


// -----------------------------------------------------------------------------
// SECTION 2 — Indexes
// -----------------------------------------------------------------------------

CREATE INDEX scheme_name_idx           IF NOT EXISTS FOR (s:Scheme)       ON (s.name);
CREATE INDEX requirement_category_idx  IF NOT EXISTS FOR (r:Requirement)  ON (r.category);
CREATE INDEX document_category_idx     IF NOT EXISTS FOR (d:Document)     ON (d.category);
CREATE INDEX citizen_profile_state_idx IF NOT EXISTS FOR (c:CitizenProfile) ON (c.state);
CREATE INDEX scheme_tags IF NOT EXISTS FOR (s:Scheme) ON (s.tags);

// TTL-style index for CitizenProfile expiry
// DISABLED — Enable in production with Neo4j Enterprise TTL indexes,
//            or handle via a scheduled application-level cleanup job
//            that runs: MATCH (c:CitizenProfile) WHERE c.expires_at < datetime() DELETE c
// CREATE INDEX citizen_profile_ttl_idx IF NOT EXISTS FOR (c:CitizenProfile) ON (c.expires_at);


// =============================================================================
// SECTION 3 — Document nodes (fulfillment assets)
// =============================================================================

MERGE (aadhaar:Document {id: "DOC-AADHAAR"})
SET aadhaar += {
  name:        "Aadhaar Card",
  description: "12-digit unique identity number issued by UIDAI to every Indian resident.",
  category:    "identity",
  issuer:      "UIDAI",
  active:      true
};

MERGE (pan:Document {id: "DOC-PAN"})
SET pan += {
  name:        "PAN Card",
  description: "Permanent Account Number issued by Income Tax Department for tax identification.",
  category:    "identity",
  issuer:      "Income Tax Department",
  active:      true
};

MERGE (ration:Document {id: "DOC-RATION"})
SET ration += {
  name:        "Ration Card",
  description: "State-issued card used to purchase subsidised food grains under PDS. Accepted as address and income proof.",
  category:    "income_proof",
  issuer:      "State Food & Civil Supplies Department",
  active:      true
};

MERGE (bankAc:Document {id: "DOC-BANK-AC"})
SET bankAc += {
  name:        "Savings Bank Account / Passbook",
  description: "Active savings bank account (any nationalised or cooperative bank) for direct benefit transfer (DBT).",
  category:    "financial",
  issuer:      "Scheduled Bank / Post Office",
  active:      true
};

MERGE (landRec:Document {id: "DOC-LAND-RECORD"})
SET landRec += {
  name:        "Land Record / Patta",
  description: "State revenue department record confirming ownership or cultivation rights over agricultural land.",
  category:    "land",
  issuer:      "State Revenue / Patwari Office",
  active:      true
};

MERGE (vendorCert:Document {id: "DOC-VENDOR-CERT"})
SET vendorCert += {
  name:        "Street Vendor Certificate of Vending",
  description: "Certificate issued by Urban Local Body / Town Vending Committee identifying the person as a registered street vendor.",
  category:    "occupation",
  issuer:      "Municipal Corporation / ULB",
  active:      true
};

MERGE (nregaCard:Document {id: "DOC-NREGA-JOBCARD"})
SET nregaCard += {
  name:        "NREGA Job Card",
  description: "Job card issued under MGNREGA by the Gram Panchayat entitling rural household members to 100 days of guaranteed wage employment.",
  category:    "employment",
  issuer:      "Gram Panchayat",
  active:      true
};


// Document prerequisite chains
// Aadhaar -> PAN (Aadhaar required to apply for PAN online)
MATCH (aadhaar:Document {id: "DOC-AADHAAR"})
MATCH (pan:Document     {id: "DOC-PAN"})
MERGE (pan)-[:REQUIRES_DOC {note: "Aadhaar required for e-PAN and KYC linking"}]->(aadhaar);

// Bank Account -> Aadhaar (mandatory KYC / Jan Dhan linkage)
MATCH (bankAc:Document  {id: "DOC-BANK-AC"})
MATCH (aadhaar:Document {id: "DOC-AADHAAR"})
MERGE (bankAc)-[:REQUIRES_DOC {note: "Aadhaar required for KYC and DBT linkage"}]->(aadhaar);


// =============================================================================
// SECTION 4 — ProcessStep nodes
// =============================================================================

MERGE (ps1:ProcessStep {id: "PS-NREGA-JOBCARD-APPLY"})
SET ps1 += {
  name:             "Apply for NREGA Job Card",
  description:      "Visit the Gram Panchayat office and submit a written application along with Aadhaar copy and a family photo. The Gram Panchayat must issue the Job Card within 15 days.",
  location:         "Gram Panchayat Office",
  estimated_days:   15,
  cost_inr:         0,
  cost_label:       "Free",
  produces_doc_id:  "DOC-NREGA-JOBCARD",
  requires_doc_ids: ["DOC-AADHAAR"],
  active:           true
};

// Link ProcessStep -> produces Document
MATCH (ps1:ProcessStep {id: "PS-NREGA-JOBCARD-APPLY"})
MATCH (nregaCard:Document {id: "DOC-NREGA-JOBCARD"})
MERGE (ps1)-[:PRODUCES]->(nregaCard);

// Link ProcessStep -> requires Document
MATCH (ps1:ProcessStep {id: "PS-NREGA-JOBCARD-APPLY"})
MATCH (aadhaar:Document {id: "DOC-AADHAAR"})
MERGE (ps1)-[:REQUIRES_DOC]->(aadhaar);

// NREGA Job Card requires Aadhaar (via the ProcessStep)
MATCH (nregaCard:Document {id: "DOC-NREGA-JOBCARD"})
MATCH (aadhaar:Document   {id: "DOC-AADHAAR"})
MERGE (nregaCard)-[:REQUIRES_DOC {
  note: "Aadhaar mandatory for NREGA Job Card application at Gram Panchayat",
  via_process_step: "PS-NREGA-JOBCARD-APPLY"
}]->(aadhaar);


// =============================================================================
// SECTION 5 — IncomeBracket nodes
// =============================================================================

MERGE (ib1:IncomeBracket {id: "IB-BELOW-200K"})
SET ib1 += {
  label:       "Below ₹2,00,000 per annum",
  max_annual:  200000,
  description: "Annual household income below ₹2 lakh — qualifies for most pro-poor central schemes."
};

MERGE (ib2:IncomeBracket {id: "IB-BELOW-500K"})
SET ib2 += {
  label:       "Below ₹5,00,000 per annum",
  max_annual:  500000,
  description: "Annual household income below ₹5 lakh — qualifies for PM-JAY health coverage."
};


// =============================================================================
// SECTION 6 — Requirement nodes
// =============================================================================

// ── Shared requirements ──────────────────────────────────────────────────────

MERGE (req_aadhaar:Requirement {id: "REQ-AADHAAR"})
SET req_aadhaar += {
  name:        "Valid Aadhaar Card",
  description: "Applicant must possess a valid Aadhaar card for identity verification and DBT linkage.",
  category:    "document",
  mandatory:   true
};

MERGE (req_bank:Requirement {id: "REQ-BANK-AC"})
SET req_bank += {
  name:        "Active Bank Account (DBT-linked)",
  description: "A savings bank account linked to Aadhaar for receiving Direct Benefit Transfers.",
  category:    "document",
  mandatory:   true
};

MERGE (req_land:Requirement {id: "REQ-AGRI-LAND"})
SET req_land += {
  name:        "Agricultural Land Ownership or Cultivation Rights",
  description: "Applicant must own or cultivate agricultural land as evidenced by state land records.",
  category:    "land",
  mandatory:   true
};

MERGE (req_income_200k:Requirement {id: "REQ-INCOME-BELOW-200K"})
SET req_income_200k += {
  name:        "Annual Household Income Below ₹2 Lakh",
  description: "Family income must not exceed ₹2,00,000 per year to qualify as a small/marginal farmer family.",
  category:    "income",
  mandatory:   false
};

MERGE (req_ration:Requirement {id: "REQ-RATION-CARD"})
SET req_ration += {
  name:        "Ration Card (PHH or AAY)",
  description: "Priority Household or Antyodaya Anna Yojana ration card as proof of economic vulnerability.",
  category:    "document",
  mandatory:   true
};

MERGE (req_vendor:Requirement {id: "REQ-VENDOR-CERT"})
SET req_vendor += {
  name:        "Street Vendor Certificate of Vending",
  description: "Certificate or Letter of Recommendation from ULB/Town Vending Committee confirming vendor status.",
  category:    "document",
  mandatory:   true
};

MERGE (req_secc:Requirement {id: "REQ-SECC-2011"})
SET req_secc += {
  name:        "SECC 2011 Database Inclusion",
  description: "Household must appear in the Socio-Economic and Caste Census 2011 or meet deprivation criteria mapped by the state.",
  category:    "database",
  mandatory:   true
};

MERGE (req_rural:Requirement {id: "REQ-RURAL-RESIDENCE"})
SET req_rural += {
  name:        "Rural Residence",
  description: "Applicant must reside in a rural area (village listed in Gram Panchayat jurisdiction).",
  category:    "residence",
  mandatory:   true
};

MERGE (req_adult:Requirement {id: "REQ-AGE-18PLUS"})
SET req_adult += {
  name:        "Adult (18 years or above)",
  description: "At least one working-age adult (18+) in the household must be willing to do unskilled manual work.",
  category:    "age",
  mandatory:   true
};

MERGE (req_nrega_card:Requirement {id: "REQ-NREGA-JOBCARD"})
SET req_nrega_card += {
  name:        "NREGA Job Card",
  description: "Valid NREGA Job Card issued by the Gram Panchayat. Can be obtained by applying at the Gram Panchayat office.",
  category:    "document",
  mandatory:   true
};

MERGE (req_pmkisan_bene:Requirement {id: "REQ-PMKISAN-BENEFICIARY"})
SET req_pmkisan_bene += {
  name:        "Existing PM-KISAN Beneficiary",
  description: "Applicant must be a registered and active PM-KISAN beneficiary (scheme PM-KISAN-2026).",
  category:    "prerequisite_scheme",
  mandatory:   true
};


// Link requirements -> fulfilled_by documents
MATCH (req_aadhaar:Requirement {id: "REQ-AADHAAR"})
MATCH (aadhaar:Document        {id: "DOC-AADHAAR"})
MERGE (aadhaar)-[:FULFILLED_BY]->(req_aadhaar);

MATCH (req_bank:Requirement {id: "REQ-BANK-AC"})
MATCH (bankAc:Document      {id: "DOC-BANK-AC"})
MERGE (bankAc)-[:FULFILLED_BY]->(req_bank);

MATCH (req_land:Requirement {id: "REQ-AGRI-LAND"})
MATCH (landRec:Document     {id: "DOC-LAND-RECORD"})
MERGE (landRec)-[:FULFILLED_BY]->(req_land);

MATCH (req_ration:Requirement {id: "REQ-RATION-CARD"})
MATCH (ration:Document        {id: "DOC-RATION"})
MERGE (ration)-[:FULFILLED_BY]->(req_ration);

MATCH (req_vendor:Requirement {id: "REQ-VENDOR-CERT"})
MATCH (vendorCert:Document    {id: "DOC-VENDOR-CERT"})
MERGE (vendorCert)-[:FULFILLED_BY]->(req_vendor);

MATCH (req_nrega_card:Requirement {id: "REQ-NREGA-JOBCARD"})
MATCH (nregaCard:Document         {id: "DOC-NREGA-JOBCARD"})
MERGE (nregaCard)-[:FULFILLED_BY]->(req_nrega_card);

// IncomeBracket fulfills income requirement
MATCH (req_income:Requirement {id: "REQ-INCOME-BELOW-200K"})
MATCH (ib:IncomeBracket       {id: "IB-BELOW-200K"})
MERGE (ib)-[:FULFILLED_BY]->(req_income);


// =============================================================================
// SECTION 7 — Scheme nodes
// =============================================================================

// ── 1. PM-KISAN ──────────────────────────────────────────────────────────────

MERGE (pmkisan:Scheme {id: "PM-KISAN-2026"})
SET pmkisan += {
  name:                 "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)",
  description:          "Provides income support of ₹6,000 per year (in three equal instalments of ₹2,000) to all small and marginal farmer families across India. Amount is transferred directly to the bank account via DBT.",
  ministry:             "Ministry of Agriculture & Farmers Welfare",
  benefit_amount:       "₹6,000 per year",
  benefit_type:         "Direct Cash Transfer (DBT)",
  application_url:      "https://pmkisan.gov.in",
  official_link:        "https://pmkisan.gov.in",
  estimated_time_days:  45,
  estimated_cost:       "Free",
  active:               true,
  tags:                 ["agriculture", "farming", "income_support", "farmer", "land", "rural"]
};

// PM-KISAN REQUIRES relationships
MATCH (pmkisan:Scheme       {id: "PM-KISAN-2026"})
MATCH (req_land:Requirement {id: "REQ-AGRI-LAND"})
MERGE (pmkisan)-[:REQUIRES {order: 1, mandatory: true}]->(req_land);

MATCH (pmkisan:Scheme         {id: "PM-KISAN-2026"})
MATCH (req_aadhaar:Requirement {id: "REQ-AADHAAR"})
MERGE (pmkisan)-[:REQUIRES {order: 2, mandatory: true}]->(req_aadhaar);

MATCH (pmkisan:Scheme      {id: "PM-KISAN-2026"})
MATCH (req_bank:Requirement {id: "REQ-BANK-AC"})
MERGE (pmkisan)-[:REQUIRES {order: 3, mandatory: true}]->(req_bank);

MATCH (pmkisan:Scheme             {id: "PM-KISAN-2026"})
MATCH (req_income:Requirement     {id: "REQ-INCOME-BELOW-200K"})
MERGE (pmkisan)-[:REQUIRES {order: 4, mandatory: false, note: "Scheme now covers all farmer families regardless of income. Income check removed from 2019 revision"}]->(req_income);


// ── 2. PM SVANidhi ───────────────────────────────────────────────────────────

MERGE (svanidhi:Scheme {id: "PM-SVANIDHI-2026"})
SET svanidhi += {
  name:                 "PM SVANidhi (PM Street Vendor's AtmaNirbhar Nidhi)",
  description:          "Provides affordable working capital micro-credit to street vendors to resume their livelihoods post-COVID. Loan starts at ₹10,000, scalable to ₹20,000 and ₹50,000 on timely repayment. Vendors also earn digital transaction incentives.",
  ministry:             "Ministry of Housing and Urban Affairs",
  benefit_amount:       "₹10,000 – ₹50,000 (micro-credit, collateral-free)",
  benefit_type:         "Micro-credit Loan",
  application_url:      "https://pmsvanidhi.mohua.gov.in",
  official_link:        "https://pmsvanidhi.mohua.gov.in",
  estimated_time_days:  30,
  estimated_cost:       "Free (interest subsidy of 7% p.a. provided by govt)",
  active:               true,
  tags:                 ["business", "street_vendor", "loan", "micro_credit", "urban", "self_employed"]
};

MATCH (svanidhi:Scheme        {id: "PM-SVANIDHI-2026"})
MATCH (req_aadhaar:Requirement {id: "REQ-AADHAAR"})
MERGE (svanidhi)-[:REQUIRES {order: 1, mandatory: true}]->(req_aadhaar);

MATCH (svanidhi:Scheme        {id: "PM-SVANIDHI-2026"})
MATCH (req_vendor:Requirement {id: "REQ-VENDOR-CERT"})
MERGE (svanidhi)-[:REQUIRES {order: 2, mandatory: true}]->(req_vendor);

MATCH (svanidhi:Scheme      {id: "PM-SVANIDHI-2026"})
MATCH (req_bank:Requirement {id: "REQ-BANK-AC"})
MERGE (svanidhi)-[:REQUIRES {order: 3, mandatory: true}]->(req_bank);


// ── 3. Ayushman Bharat PM-JAY ────────────────────────────────────────────────

MERGE (pmjay:Scheme {id: "PMJAY-2026"})
SET pmjay += {
  name:                 "Ayushman Bharat PM-JAY (Pradhan Mantri Jan Arogya Yojana)",
  description:          "World's largest government-funded health assurance scheme providing coverage of up to ₹5 lakh per family per year for secondary and tertiary care hospitalisation. Covers 10+ crore poor and vulnerable families identified via SECC 2011 data.",
  ministry:             "Ministry of Health and Family Welfare",
  benefit_amount:       "₹5,00,000 per family per year (hospitalisation cover)",
  benefit_type:         "Health Insurance / Cashless Treatment",
  application_url:      "https://pmjay.gov.in",
  official_link:        "https://pmjay.gov.in",
  estimated_time_days:  7,
  estimated_cost:       "Free",
  active:               true,
  tags:                 ["health", "medical", "insurance", "hospital", "family", "poor"]
};

MATCH (pmjay:Scheme           {id: "PMJAY-2026"})
MATCH (req_secc:Requirement   {id: "REQ-SECC-2011"})
MERGE (pmjay)-[:REQUIRES {order: 1, mandatory: true}]->(req_secc);

MATCH (pmjay:Scheme            {id: "PMJAY-2026"})
MATCH (req_aadhaar:Requirement {id: "REQ-AADHAAR"})
MERGE (pmjay)-[:REQUIRES {order: 2, mandatory: true}]->(req_aadhaar);

MATCH (pmjay:Scheme           {id: "PMJAY-2026"})
MATCH (req_ration:Requirement {id: "REQ-RATION-CARD"})
MERGE (pmjay)-[:REQUIRES {order: 3, mandatory: true}]->(req_ration);


// ── 4. Kisan Credit Card ─────────────────────────────────────────────────────

MERGE (kcc:Scheme {id: "KCC-2026"})
SET kcc += {
  name:                 "Kisan Credit Card (KCC)",
  description:          "Provides farmers with affordable short-term credit for crop cultivation, post-harvest expenses, and allied activities. Credit limit up to ₹3 lakh at a subsidised interest rate of 7% per annum (effective 4% with interest subvention for timely repayment).",
  ministry:             "Ministry of Agriculture & Farmers Welfare / NABARD",
  benefit_amount:       "Up to ₹3,00,000 credit at 7% p.a.",
  benefit_type:         "Revolving Credit Facility",
  application_url:      "https://www.nabard.org/content.aspx?id=580",
  official_link:        "https://nabard.org",
  estimated_time_days:  30,
  estimated_cost:       "Processing fee as per bank norms",
  active:               true,
  tags:                 ["agriculture", "farming", "credit", "loan", "farmer", "land"]
};

MATCH (kcc:Scheme           {id: "KCC-2026"})
MATCH (req_land:Requirement {id: "REQ-AGRI-LAND"})
MERGE (kcc)-[:REQUIRES {order: 1, mandatory: true}]->(req_land);

MATCH (kcc:Scheme                   {id: "KCC-2026"})
MATCH (req_pmkisan:Requirement      {id: "REQ-PMKISAN-BENEFICIARY"})
MERGE (kcc)-[:REQUIRES {order: 2, mandatory: true, note: "PM-KISAN registration streamlines KCC issuance under bank-saturation drive"}]->(req_pmkisan);

MATCH (kcc:Scheme           {id: "KCC-2026"})
MATCH (req_bank:Requirement {id: "REQ-BANK-AC"})
MERGE (kcc)-[:REQUIRES {order: 3, mandatory: true}]->(req_bank);

// KCC PREREQUISITE relationship: PM-KISAN must come first
MATCH (pmkisan:Scheme {id: "PM-KISAN-2026"})
MATCH (kcc:Scheme     {id: "KCC-2026"})
MERGE (kcc)-[:PREREQUISITE {
  auto_unlocks: true,
  note:         "PM-KISAN registration is used as farmer identity proof when applying for KCC under saturation drive"
}]->(pmkisan);

// PM-KISAN scheme node FULFILLS the prerequisite requirement
MATCH (pmkisan:Scheme              {id: "PM-KISAN-2026"})
MATCH (req_pmkisan:Requirement     {id: "REQ-PMKISAN-BENEFICIARY"})
MERGE (pmkisan)-[:FULFILLED_BY]->(req_pmkisan);


// ── 5. MGNREGA ───────────────────────────────────────────────────────────────

MERGE (nrega:Scheme {id: "NREGA-2026"})
SET nrega += {
  name:                 "MGNREGA (Mahatma Gandhi National Rural Employment Guarantee Act)",
  description:          "Guarantees at least 100 days of unskilled manual wage employment per financial year to every rural household whose adult members volunteer for the work. Wages are paid directly to the bank/post office account of the worker.",
  ministry:             "Ministry of Rural Development",
  benefit_amount:       "100 days guaranteed employment @ state-notified wage rate (avg ₹267/day)",
  benefit_type:         "Employment Guarantee / Wage Payment",
  application_url:      "https://nrega.nic.in",
  official_link:        "https://nrega.nic.in",
  estimated_time_days:  20,
  estimated_cost:       "Free",
  active:               true,
  tags:                 ["employment", "rural", "wage", "job", "work", "manual_labor"]
};

MATCH (nrega:Scheme           {id: "NREGA-2026"})
MATCH (req_rural:Requirement  {id: "REQ-RURAL-RESIDENCE"})
MERGE (nrega)-[:REQUIRES {order: 1, mandatory: true}]->(req_rural);

MATCH (nrega:Scheme           {id: "NREGA-2026"})
MATCH (req_adult:Requirement  {id: "REQ-AGE-18PLUS"})
MERGE (nrega)-[:REQUIRES {order: 2, mandatory: true}]->(req_adult);

MATCH (nrega:Scheme            {id: "NREGA-2026"})
MATCH (req_aadhaar:Requirement {id: "REQ-AADHAAR"})
MERGE (nrega)-[:REQUIRES {order: 3, mandatory: true}]->(req_aadhaar);

MATCH (nrega:Scheme                {id: "NREGA-2026"})
MATCH (req_nrega_card:Requirement  {id: "REQ-NREGA-JOBCARD"})
MERGE (nrega)-[:REQUIRES {
  order:     4,
  mandatory: true,
  note:      "Job Card can be obtained free of cost from the Gram Panchayat office within 15 days of application"
}]->(req_nrega_card);

// NREGA -> ProcessStep link for guidance
MATCH (nrega:Scheme   {id: "NREGA-2026"})
MATCH (ps1:ProcessStep {id: "PS-NREGA-JOBCARD-APPLY"})
MERGE (nrega)-[:HAS_STEP {step_order: 1}]->(ps1);


// =============================================================================
// SECTION 8 — Verification queries (run these to check seed data)
// =============================================================================
// MATCH (s:Scheme) RETURN s.id, s.name, s.active ORDER BY s.id;
// MATCH (s:Scheme)-[:REQUIRES]->(r:Requirement) RETURN s.name, count(r) AS req_count;
// MATCH (d:Document)-[:FULFILLED_BY]->(r:Requirement) RETURN d.name, r.name;
// MATCH (s1:Scheme)-[:PREREQUISITE]->(s2:Scheme) RETURN s1.name + ' requires ' + s2.name AS chain;
// MATCH (ps:ProcessStep)-[:PRODUCES]->(d:Document) RETURN ps.name, d.name;
// MATCH (kcc:Scheme {id:'KCC-2026'})-[:PREREQUISITE]->(pre) RETURN pre.name;


// ============================================================================
// SCHEMEPATH 2.0 EXPANSION (PMAY-G, PMMVY, PMMY + PROCUREMENT STEPS)
// ============================================================================

// ---------------------------------------------------------------------------
// 2. New ProcessSteps for Document Procurement
// ---------------------------------------------------------------------------
MERGE (ps:ProcessStep {id: 'PS-MARRIAGE-CERT-APPLY'})
  ON CREATE SET ps.name = 'Apply for Marriage Certificate', ps.location = 'Municipal Corporation / Gram Panchayat', ps.estimated_days = 15, ps.cost_inr = 200, ps.cost_label = '₹100-500'
MERGE (ps)-[:PRODUCES]->(d:Document {id: 'DOC-MARRIAGE-CERT'})
MERGE (ps)-[:REQUIRES_DOC]->(reqDoc:Document {id: 'DOC-AADHAAR'})

MERGE (ps2:ProcessStep {id: 'PS-PREGNANCY-REG'})
  ON CREATE SET ps2.name = 'Register Pregnancy at nearest PHC', ps2.location = 'Primary Health Centre', ps2.estimated_days = 1, ps2.cost_inr = 0, ps2.cost_label = 'Free'
MERGE (ps2)-[:PRODUCES]->(d2:Document {id: 'DOC-PREGNANCY-REG'})
MERGE (ps2)-[:REQUIRES_DOC]->(reqDoc2:Document {id: 'DOC-AADHAAR'})

MERGE (ps3:ProcessStep {id: 'PS-FSSAI-REG'})
  ON CREATE SET ps3.name = 'Apply for FSSAI Basic Registration', ps3.location = 'Online (foscos.fssai.gov.in)', ps3.estimated_days = 7, ps3.cost_inr = 100, ps3.cost_label = '₹100/year'
MERGE (ps3)-[:PRODUCES]->(d3:Document {id: 'DOC-FSSAI-LICENSE'})
MERGE (ps3)-[:REQUIRES_DOC]->(reqDoc3:Document {id: 'DOC-AADHAAR'})

MERGE (ps4:ProcessStep {id: 'PS-UDYAM-REG'})
  ON CREATE SET ps4.name = 'Register on Udyam Portal', ps4.location = 'Online (udyamregistration.gov.in)', ps4.estimated_days = 1, ps4.cost_inr = 0, ps4.cost_label = 'Free'
MERGE (ps4)-[:PRODUCES]->(d4:Document {id: 'DOC-UDYAM-REG'})
MERGE (ps4)-[:REQUIRES_DOC]->(reqDoc4:Document {id: 'DOC-AADHAAR'})
MERGE (ps4)-[:REQUIRES_DOC]->(reqDoc5:Document {id: 'DOC-BANK-AC'})

MERGE (ps5:ProcessStep {id: 'PS-BPL-CERT'})
  ON CREATE SET ps5.name = 'Get BPL Certificate from District Administration', ps5.location = 'Block Development Office', ps5.estimated_days = 21, ps5.cost_inr = 100, ps5.cost_label = '₹50-200'
MERGE (ps5)-[:PRODUCES]->(d5:Document {id: 'DOC-BPL-CERT'})
MERGE (ps5)-[:REQUIRES_DOC]->(reqDoc6:Document {id: 'DOC-AADHAAR'})
MERGE (ps5)-[:REQUIRES_DOC]->(reqDoc7:Document {id: 'DOC-RATION'})

MERGE (ps6:ProcessStep {id: 'PS-VENDOR-CERT-APPLY'})
  ON CREATE SET ps6.name = 'Apply for Vendor Certificate', ps6.location = 'Municipal Corporation / Town Vending Committee', ps6.estimated_days = 20, ps6.cost_inr = 0, ps6.cost_label = 'Free'
MERGE (ps6)-[:PRODUCES]->(d6:Document {id: 'DOC-VENDOR-CERT'})
MERGE (ps6)-[:REQUIRES_DOC]->(reqDoc8:Document {id: 'DOC-AADHAAR'})

MERGE (ps7:ProcessStep {id: 'PS-LAND-TRANSFER'})
  ON CREATE SET ps7.name = 'Transfer land to beneficiary name', ps7.location = 'Tehsildar / Sub-Registrar Office', ps7.estimated_days = 30, ps7.cost_inr = 1500, ps7.cost_label = '₹1000-2000 (stamp duty)'
MERGE (ps7)-[:PRODUCES]->(d7:Document {id: 'DOC-LAND-RECORD'})
MERGE (ps7)-[:REQUIRES_DOC]->(reqDoc9:Document {id: 'DOC-AADHAAR'})
MERGE (ps7)-[:REQUIRES_DOC]->(reqDoc10:Document {id: 'DOC-LAND-RECORD'})

// ---------------------------------------------------------------------------
// 3. New Requirements
// ---------------------------------------------------------------------------
MERGE (r:Requirement {id: 'REQ-BPL-CERT'})
  ON CREATE SET r.name = 'BPL Certificate or SECC Inclusion', r.category = 'income_proof', r.description = 'Must be recognized as Below Poverty Line'
MERGE (d:Document {id: 'DOC-BPL-CERT'})
MERGE (d)-[:FULFILLED_BY]->(r)

MERGE (r2:Requirement {id: 'REQ-MARRIAGE-CERT'})
  ON CREATE SET r2.name = 'Marriage Certificate', r2.category = 'document', r2.description = 'Proof of marriage'
MERGE (d2:Document {id: 'DOC-MARRIAGE-CERT'})
MERGE (d2)-[:FULFILLED_BY]->(r2)

MERGE (r3:Requirement {id: 'REQ-PREGNANCY-REG'})
  ON CREATE SET r3.name = 'Pregnancy Registration', r3.category = 'document', r3.description = 'Registered with health facility'
MERGE (d3:Document {id: 'DOC-PREGNANCY-REG'})
MERGE (d3)-[:FULFILLED_BY]->(r3)

MERGE (r4:Requirement {id: 'REQ-FSSAI-LICENSE'})
  ON CREATE SET r4.name = 'FSSAI Food License', r4.category = 'document'
MERGE (d4:Document {id: 'DOC-FSSAI-LICENSE'})
MERGE (d4)-[:FULFILLED_BY]->(r4)

MERGE (r5:Requirement {id: 'REQ-UDYAM-REG'})
  ON CREATE SET r5.name = 'Udyam Registration', r5.category = 'document'
MERGE (d5:Document {id: 'DOC-UDYAM-REG'})
MERGE (d5)-[:FULFILLED_BY]->(r5)

MERGE (r6:Requirement {id: 'REQ-WOMAN-BENEFICIARY'})
  ON CREATE SET r6.name = 'Female Beneficiary', r6.category = 'demographic'
  
MERGE (r7:Requirement {id: 'REQ-FIRST-PREGNANCY'})
  ON CREATE SET r7.name = 'First Pregnancy', r7.category = 'demographic'

// ---------------------------------------------------------------------------
// 4. New Schemes
// ---------------------------------------------------------------------------
MERGE (s:Scheme {id: 'PMAY-G-2026'})
  ON CREATE SET s.name = 'Pradhan Mantri Awas Yojana - Gramin', s.active = true, s.tags = ['housing', 'rural', 'construction', 'bpl', 'home'], s.ministry = 'Ministry of Rural Development', s.benefit_amount = '₹1,20,000 (plains)', s.benefit_type = 'Direct Cash Transfer', s.application_url = 'https://pmayg.nic.in', s.estimated_time_days = 60, s.estimated_cost = 'Free'
MERGE (s)-[:REQUIRES {order: 1, mandatory: true}]->(r_bpl:Requirement {id: 'REQ-BPL-CERT'})
MERGE (s)-[:REQUIRES {order: 2, mandatory: true}]->(r_aadhaar:Requirement {id: 'REQ-AADHAAR'})
MERGE (s)-[:REQUIRES {order: 3, mandatory: true}]->(r_bank:Requirement {id: 'REQ-BANK-AC'})

MERGE (s2:Scheme {id: 'PMMVY-2026'})
  ON CREATE SET s2.name = 'Pradhan Mantri Matru Vandana Yojana', s2.active = true, s2.tags = ['maternity', 'pregnancy', 'women', 'family', 'child', 'health'], s2.ministry = 'Ministry of Women and Child Development', s2.benefit_amount = '₹11,000 for first child', s2.benefit_type = 'Direct Cash Transfer', s2.application_url = 'https://pmmvy.wcd.gov.in', s2.estimated_time_days = 30, s2.estimated_cost = 'Free'
MERGE (s2)-[:REQUIRES {order: 1, mandatory: true}]->(r_aadhaar)
MERGE (s2)-[:REQUIRES {order: 2, mandatory: true}]->(r_bank)
MERGE (s2)-[:REQUIRES {order: 3, mandatory: true}]->(r_preg:Requirement {id: 'REQ-PREGNANCY-REG'})
MERGE (s2)-[:REQUIRES {order: 4, mandatory: true}]->(r_woman:Requirement {id: 'REQ-WOMAN-BENEFICIARY'})

MERGE (s3:Scheme {id: 'PMMY-2026'})
  ON CREATE SET s3.name = 'Pradhan Mantri Mudra Yojana', s3.active = true, s3.tags = ['business', 'startup', 'loan', 'micro_credit', 'self_employed', 'entrepreneur'], s3.ministry = 'Ministry of Finance / MUDRA Ltd', s3.benefit_amount = 'Loans up to ₹10,00,000', s3.benefit_type = 'Collateral-free Loan', s3.application_url = 'https://www.mudra.org.in', s3.estimated_time_days = 30, s3.estimated_cost = 'Processing fee per bank norms'
MERGE (s3)-[:REQUIRES {order: 1, mandatory: true}]->(r_aadhaar)
MERGE (s3)-[:REQUIRES {order: 2, mandatory: true}]->(r_bank)
MERGE (s3)-[:REQUIRES {order: 3, mandatory: false}]->(r_udyam:Requirement {id: 'REQ-UDYAM-REG'})

// HAS_STEP relationships
MERGE (s)-[:HAS_STEP]->(:ProcessStep {id: 'PS-BPL-CERT'})
MERGE (s2)-[:HAS_STEP]->(:ProcessStep {id: 'PS-PREGNANCY-REG'})
MERGE (s3)-[:HAS_STEP]->(:ProcessStep {id: 'PS-UDYAM-REG'})

