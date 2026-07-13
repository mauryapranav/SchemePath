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
