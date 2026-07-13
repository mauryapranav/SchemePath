// ─────────────────────────────────────────────────────────────────────────────
// lib/api.ts — Axios instance + typed API functions
// ─────────────────────────────────────────────────────────────────────────────

import axios, { AxiosError, AxiosResponse } from "axios";
import type {
  AnswerRequest,
  AnswerResponse,
  CitizenProfileResponse,
  CitizenProfileUpdate,
  EligibilityMap,
  EligibilityPath,
  NextQuestion,
  SchemeDetail,
} from "./types";

// ---------------------------------------------------------------------------
// Axios instance
// ---------------------------------------------------------------------------

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
  timeout: 30_000, // 30 s — Gemini calls can be slow
});

// ── Request interceptor ────────────────────────────────────────────────────
api.interceptors.request.use(
  (config) => {
    // Attach auth token here if needed in future:
    // config.headers.Authorization = `Bearer ${getToken()}`;
    return config;
  },
  (error: AxiosError) => {
    console.error("[API] Request error:", error.message);
    return Promise.reject(error);
  }
);

// ── Response interceptor ───────────────────────────────────────────────────
// We use a response interceptor here so every single API call across the frontend
// handles errors exactly the same way. It prevents us from having to write 
// try/catch JSON-parsing boilerplate in every single component.
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError<{ detail?: string }>) => {
    const status = error.response?.status;
    const detail = error.response?.data?.detail ?? error.message;

    if (status === 404) {
      console.warn(`[API] 404 Not Found — ${error.config?.url}`);
    } else if (status === 422) {
      console.error("[API] 422 Validation error:", detail);
    } else if (status && status >= 500) {
      console.error(`[API] Server error ${status}:`, detail);
    } else {
      console.error("[API] Error:", detail);
    }

    // Re-throw a cleaned-up error so callers can surface it in UI
    const cleaned = new Error(detail);
    (cleaned as Error & { status?: number }).status = status;
    return Promise.reject(cleaned);
  }
);

export default api;

// ---------------------------------------------------------------------------
// Profile endpoints
// ---------------------------------------------------------------------------

/**
 * POST /profile/create
 * Parse raw citizen text with Gemini and persist a new CitizenProfile.
 */
export async function createProfile(
  rawInput: string
): Promise<CitizenProfileResponse> {
  const { data } = await api.post<CitizenProfileResponse>("/profile/create", {
    raw_input: rawInput,
  });
  return data;
}

/**
 * PATCH /profile/{profileId}
 * Apply a partial update to an existing CitizenProfile.
 */
export async function updateProfile(
  profileId: string,
  update: CitizenProfileUpdate
): Promise<CitizenProfileResponse> {
  const { data } = await api.patch<CitizenProfileResponse>(
    `/profile/${profileId}`,
    update
  );
  return data;
}

// ---------------------------------------------------------------------------
// Eligibility endpoints
// ---------------------------------------------------------------------------

/**
 * GET /eligibility/map/{profileId}
 * Return the full eligibility map (confirmed, one_step, locked schemes).
 */
export async function getEligibilityMap(
  profileId: string
): Promise<EligibilityMap> {
  const { data } = await api.get<EligibilityMap>(
    `/eligibility/map/${profileId}`
  );
  return data;
}

/**
 * GET /eligibility/path/{profileId}/{schemeId}
 * Return the EligibilityPath for a single scheme.
 */
export async function getEligibilityPath(
  profileId: string,
  schemeId: string
): Promise<EligibilityPath> {
  const { data } = await api.get<EligibilityPath>(
    `/eligibility/path/${profileId}/${schemeId}`
  );
  return data;
}

// ---------------------------------------------------------------------------
// Question endpoints
// ---------------------------------------------------------------------------

/**
 * GET /questions/next/{profileId}
 * Fetch the highest-impact next question for this profile.
 * Returns null if the profile is complete (backend returns { message: "..." }).
 */
export async function getNextQuestion(
  profileId: string
): Promise<NextQuestion | null> {
  const { data } = await api.get<AnswerResponse>(
    `/questions/next/${profileId}`
  );
  // Backend returns either a NextQuestion or { message: "Profile complete!" }
  if ("message" in data) return null;
  return data as NextQuestion;
}

/**
 * POST /questions/answer/{profileId}
 * Submit an answer and receive the next question (or null if complete).
 */
export async function answerQuestion(
  profileId: string,
  questionId: string,
  answer: unknown
): Promise<NextQuestion | null> {
  const body: AnswerRequest = { question_id: questionId, answer };
  const { data } = await api.post<AnswerResponse>(
    `/questions/answer/${profileId}`,
    body
  );
  if ("message" in data) return null;
  return data as NextQuestion;
}

// ---------------------------------------------------------------------------
// Scheme endpoints
// ---------------------------------------------------------------------------

/**
 * GET /scheme/{schemeId}  (or /eligibility/scheme/{schemeId} — adjust prefix)
 * Return full SchemeDetail for a scheme node.
 */
export async function getSchemeDetail(
  schemeId: string
): Promise<SchemeDetail> {
  const { data } = await api.get<SchemeDetail>(`/scheme/${schemeId}`);
  return data;
}
