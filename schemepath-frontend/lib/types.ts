// ─────────────────────────────────────────────────────────────────────────────
// lib/types.ts — TypeScript interfaces mirroring all backend Pydantic models
// ─────────────────────────────────────────────────────────────────────────────

// We maintain these interfaces as a strict contract with the Python backend.
// By keeping them exactly in sync with the Pydantic models, we catch 
// serialization bugs at compile time instead of crashing at runtime.

// ---------------------------------------------------------------------------
// Generic
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: string;
  neo4j_connected: boolean;
}

export interface ErrorResponse {
  detail: string;
}

// ---------------------------------------------------------------------------
// Citizen Profile
// ---------------------------------------------------------------------------

export interface CitizenProfileCreate {
  raw_input: string;
}

export interface CitizenProfileUpdate {
  age?: number | null;
  gender?: "male" | "female" | "other" | null;
  caste?: string | null;
  state?: string | null;
  district?: string | null;
  location_type?: "rural" | "urban" | "semi-urban" | null;
  family_income_annual?: number | null;
  occupation?: string | null;
  goal?: string | null;
  goal_tags?: string[] | null;
  has_documents?: string[] | null;
  has_land?: boolean | null;
  land_acres?: number | null;
}

/** Structured profile extracted by Gemini from raw citizen input. */
export interface ParsedProfile {
  age: number | null;
  gender: string | null;
  caste: string | null;
  state: string | null;
  location_type: string | null;
  family_income_annual: number | null;
  occupation: string | null;
  goal: string | null;
  goal_tags: string[];
  mentioned_documents: string[];
  confidence_score: number;
}

/** API response after creating a new profile. */
export interface CitizenProfileResponse {
  id: string;
  age: number | null;
  gender: string | null;
  caste: string | null;
  state: string | null;
  location_type: string | null;
  family_income_annual: number | null;
  occupation: string | null;
  goal: string | null;
  mentioned_documents: string[];
  confidence_score: number;
}

// ---------------------------------------------------------------------------
// Question engine
// ---------------------------------------------------------------------------

export type QuestionType =
  | "single_choice"
  | "multi_select"
  | "boolean"
  | "number"
  | "text";

export interface QuestionOption {
  id: string;
  label: string;
}

export interface NextQuestion {
  question_id: string;
  question_text: string;
  question_type: QuestionType;
  options: QuestionOption[] | null;
  context: string;
  schemes_unlocked_estimate: number;
  category: string;
}

/** Shape of the POST /questions/answer/{profile_id} request body. */
export interface AnswerRequest {
  question_id: string;
  answer: unknown; // varies: string | string[] | boolean | number
}

/** Response from the answer endpoint — the next question, or completion. */
export type AnswerResponse =
  | NextQuestion
  | { message: string };

// ---------------------------------------------------------------------------
// Eligibility
// ---------------------------------------------------------------------------

export type EligibilityStatus =
  | "confirmed"
  | "one_step"
  | "locked"
  | "unknown";

export interface RequirementSummary {
  id: string;
  name: string;
  description?: string;
  category?: string;
}

export interface NextStep {
  action: string;
}

export interface EligibilityPath {
  scheme_id: string;
  scheme_name: string;
  scheme_description: string;
  benefit_amount: string | null;
  scheme_tags: string[];
  status: EligibilityStatus;
  total_steps: number;
  completed_steps: number;
  missing_requirements: RequirementSummary[];
  next_steps: NextStep[];
  estimated_time_days: number | null;
  estimated_cost: string | null;
  path_visualization: string[];
}

export interface EligibilityMap {
  profile_id: string;
  goal_relevant_schemes: EligibilityPath[];
  other_schemes: EligibilityPath[];
  confirmed_schemes: EligibilityPath[];
  one_step_schemes: EligibilityPath[];
  locked_schemes: EligibilityPath[];
  total_schemes_analyzed: number;
  profile_completion: number;
  user_goal_tags: string[];
  user_goal: string | null;
}

// ---------------------------------------------------------------------------
// Scheme detail
// ---------------------------------------------------------------------------

export interface RequirementDetail {
  id: string;
  name: string;
  description?: string;
  category?: string;
  mandatory?: boolean;
}

export interface SchemeDetail {
  id: string;
  name: string;
  description: string;
  ministry: string;
  benefit_amount: string | null;
  benefit_type: string | null;
  application_url: string | null;
  official_link: string | null;
  requirements: RequirementDetail[];
  prerequisite_schemes: string[];
  mutually_exclusive_with: string[];
}

// ===========================================================================
// Chat Message Types (SchemePath 2.0)
// ===========================================================================

export type ChatMessageRole = 'user' | 'assistant' | 'system';

export interface SchemeCardData {
  id: string;
  name: string;
  description: string;
  benefit_amount: string | null;
  benefit_type: string | null;
  status: EligibilityStatus;
  missing_requirements: RequirementSummary[];
  application_url: string | null;
}

export interface DocumentCheckData {
  id: string;
  name: string;
  question: string;
}

export interface ProcurementStepData {
  step_number: number;
  action: string;
  location: string;
  cost: string;
  time: string;
  prerequisites?: string;
}

export interface ProcurementGuideData {
  document_name: string;
  document_id: string;
  steps: ProcurementStepData[];
}

export interface GraphNodeData {
  id: string;
  label: string;
  type: 'user' | 'scheme' | 'document' | 'requirement';
  status: 'confirmed' | 'one_step' | 'locked' | 'have' | 'missing';
}

export interface GraphEdgeData {
  source: string;
  target: string;
  label: string;
  satisfied: boolean;
}

// ---------------------------------------------------------------------------
// WebSocket protocol — discriminated unions
// ---------------------------------------------------------------------------

/** Messages the server sends to the frontend. */
export type ServerMessage =
  | { type: 'ai_message'; content: string; done: boolean }
  | { type: 'scheme_cards'; schemes: SchemeCardData[] }
  | { type: 'document_check'; documents: DocumentCheckData[] }
  | { type: 'quick_replies'; options: string[] }
  | { type: 'graph_data'; nodes: GraphNodeData[]; edges: GraphEdgeData[] }
  | { type: 'status_update'; message: string }
  | { type: 'procurement_guide'; document_name: string; document_id: string; steps: ProcurementStepData[] }
  | { type: 'error'; message: string };

/** Messages the frontend sends to the server. */
export type ClientMessage =
  | { type: 'user_message'; content: string }
  | { type: 'document_response'; document_id: string; status: 'have' | 'dont_have' | 'in_progress' }
  | { type: 'request_graph' };

// ---------------------------------------------------------------------------
// Chat display model
// ---------------------------------------------------------------------------

/** A single message in the chat thread, with optional structured attachments. */
export interface ChatMessage {
  id: string;
  role: ChatMessageRole;
  content: string;
  timestamp: Date;
  // Structured attachments rendered inline below the text
  schemeCards?: SchemeCardData[];
  documentCheck?: DocumentCheckData[];
  quickReplies?: string[];
  procurementGuide?: ProcurementGuideData;
  statusUpdate?: string;
  isStreaming?: boolean;
}
import { ChatMessageRole, EligibilityStatus, RequirementSummary } from "./types";

export interface SchemeCardData {
  id: string;
  name: string;
  description: string;
  benefit_amount: string | null;
  benefit_type: string | null;
  status: EligibilityStatus;
  missing_requirements: RequirementSummary[];
  application_url: string | null;
}

export interface DocumentCheckData {
  id: string;
  name: string;
  question: string;
}

export interface ProcurementStepData {
  step_number: number;
  action: string;
  location: string;
  cost: string;
  time: string;
  prerequisites?: string[];
}

export interface ProcurementGuideData {
  document_name: string;
  document_id: string;
  steps: ProcurementStepData[];
}

export interface GraphNodeData {
  id: string;
  label: string;
  type: "user" | "scheme" | "document" | "requirement";
  status: "confirmed" | "one_step" | "locked" | "have" | "missing";
}

export interface GraphEdgeData {
  source: string;
  target: string;
  label: string;
  satisfied: boolean;
}

// Discriminated union for WebSocket messages from server
export type ServerMessage =
  | { type: "ai_message"; content: string; done: boolean }
  | { type: "scheme_cards"; schemes: SchemeCardData[] }
  | { type: "document_check"; documents: DocumentCheckData[] }
  | { type: "quick_replies"; options: string[] }
  | { type: "graph_data"; nodes: GraphNodeData[]; edges: GraphEdgeData[] }
  | { type: "status_update"; message: string }
  | { type: "procurement_guide"; document_name: string; document_id: string; steps: ProcurementStepData[] }
  | { type: "error"; message: string }
  | { type: "request_graph_render" };

// Client message types
export type ClientMessage =
  | { type: "user_message"; content: string }
  | { type: "document_response"; document_id: string; status: "have" | "dont_have" | "in_progress" }
  | { type: "request_graph" };

// Chat message for display
export interface ChatMessage {
  id: string;
  role: ChatMessageRole;
  content: string;
  timestamp: Date;
  // Structured attachments
  schemeCards?: SchemeCardData[];
  documentCheck?: DocumentCheckData[];
  quickReplies?: string[];
  procurementGuide?: ProcurementGuideData;
  statusUpdate?: string;
  isStreaming?: boolean;
}

