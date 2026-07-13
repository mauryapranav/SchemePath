"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2, MapIcon, PartyPopper, RefreshCw } from "lucide-react";
import { answerQuestion, getEligibilityMap, getNextQuestion } from "@/lib/api";
import type { EligibilityMap, NextQuestion } from "@/lib/types";
import QuestionCard from "@/components/QuestionCard";
import EligibilityMapComponent from "@/components/EligibilityMap";
import ProgressBar from "@/components/ProgressBar";

// ── Skeleton ──────────────────────────────────────────────────────────────────
function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div className={`animate-pulse rounded-xl bg-slate-700/40 ${className}`} />
  );
}

function QuestionSkeleton() {
  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-slate-700 bg-slate-800/50 p-6">
      <Skeleton className="h-4 w-32" />
      <Skeleton className="h-6 w-full" />
      <Skeleton className="h-4 w-3/4" />
      <div className="flex flex-col gap-2 pt-2">
        {[1, 2, 3].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
      </div>
      <Skeleton className="h-12 w-full" />
    </div>
  );
}

function MapSkeleton() {
  return (
    <div className="flex flex-col gap-3">
      <Skeleton className="h-28 w-full" />
      <Skeleton className="h-10 w-full" />
      {[1, 2, 3].map((i) => <Skeleton key={i} className="h-32 w-full" />)}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
type Phase = "loading" | "questioning" | "complete" | "error";

export default function ProfileDashboard() {
  const { id: profileId } = useParams<{ id: string }>();
  const router = useRouter();

  const [phase,          setPhase]          = useState<Phase>("loading");
  const [question,       setQuestion]       = useState<NextQuestion | null>(null);
  const [eligibilityMap, setEligibilityMap] = useState<EligibilityMap | null>(null);
  const [mapLoading,     setMapLoading]     = useState(false);
  const [submitting,     setSubmitting]     = useState(false);
  const [error,          setError]          = useState<string | null>(null);

  // Fetch the eligibility map (can be called at any time)
  const refreshMap = useCallback(async () => {
    setMapLoading(true);
    try {
      const map = await getEligibilityMap(profileId);
      setEligibilityMap(map);
    } catch {
      // Non-fatal — map may not exist yet if profile is brand new
    } finally {
      setMapLoading(false);
    }
  }, [profileId]);

  // Fetch next question and (re)load the map
  const loadNext = useCallback(async () => {
    try {
      const [q] = await Promise.all([
        getNextQuestion(profileId),
        refreshMap(),
      ]);
      if (q === null) {
        setPhase("complete");
      } else {
        setQuestion(q);
        setPhase("questioning");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load profile");
      setPhase("error");
    }
  }, [profileId, refreshMap]);

  useEffect(() => { loadNext(); }, [loadNext]);

  // Handle answer submission
  async function handleAnswer(questionId: string, answer: unknown) {
    setSubmitting(true);
    try {
      const next = await answerQuestion(profileId, questionId, answer);
      // Refresh map in background while showing next question
      refreshMap();
      if (next === null) {
        setPhase("complete");
      } else {
        setQuestion(next);
        setPhase("questioning");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save answer");
    } finally {
      setSubmitting(false);
    }
  }

  // Skip / don't know — advance without saving a real answer
  async function handleSkipOrDontKnow(questionId: string) {
    await handleAnswer(questionId, null);
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  if (phase === "error") {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4 px-4">
        <p className="max-w-sm text-center text-sm text-red-400">{error}</p>
        <div className="flex gap-3">
          <button
            onClick={() => { setPhase("loading"); loadNext(); }}
            className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500"
          >
            <RefreshCw className="h-4 w-4" /> Retry
          </button>
          <button
            onClick={() => router.push("/")}
            className="rounded-xl border border-slate-700 px-4 py-2.5 text-sm text-slate-400 hover:text-slate-200"
          >
            Start over
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto min-h-screen max-w-7xl px-4 py-8">
      {/* ── Top bar ────────────────────────────────────────────────────────── */}
      <header className="mb-6 flex items-center justify-between gap-4">
        <div>
          <button
            onClick={() => router.push("/")}
            className="text-lg font-black tracking-tight text-slate-100"
          >
            <span className="bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
              Scheme
            </span>
            Path
          </button>
          <p className="text-xs text-slate-500">Profile: {profileId}</p>
        </div>
        <button
          onClick={refreshMap}
          disabled={mapLoading}
          className="flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-400 hover:border-indigo-500/50 hover:text-slate-200 disabled:opacity-40"
        >
          <MapIcon className="h-3.5 w-3.5" />
          {mapLoading ? "Refreshing…" : "Refresh map"}
        </button>
      </header>

      {/* ── Progress bar (full-width, above columns) ───────────────────────── */}
      {eligibilityMap && (
        <div className="mb-6">
          <ProgressBar completion={eligibilityMap.profile_completion} />
        </div>
      )}

      {/* ── Two-column layout ──────────────────────────────────────────────── */}
      {/* We use this two-column layout on desktop so the user can answer questions
          on the left while seeing their eligibility map update in real-time on the right. 
          This creates a powerful feedback loop that encourages them to keep answering. */}
      <div className="flex flex-col gap-6 lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)] lg:items-start">

        {/* ── LEFT — Questions / completion ──────────────────────────────── */}
        <div className="flex flex-col gap-4">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500">
            Profile Questions
          </h2>

          {phase === "loading" && <QuestionSkeleton />}

          {phase === "questioning" && question && (
            <QuestionCard
              question={question}
              onAnswer={handleAnswer}
              onSkip={handleSkipOrDontKnow}
              onDontKnow={handleSkipOrDontKnow}
              submitting={submitting}
            />
          )}

          {phase === "complete" && (
            <div className="flex flex-col items-center gap-3 rounded-2xl border border-green-500/20 bg-green-500/5 p-8 text-center">
              <PartyPopper className="h-10 w-10 text-green-400" />
              <h3 className="text-lg font-bold text-slate-100">
                🎉 Profile complete!
              </h3>
              <p className="text-sm text-slate-400">
                Here&apos;s your personalised eligibility map. You can apply for
                confirmed schemes right now.
              </p>
            </div>
          )}
        </div>

        {/* ── RIGHT — Eligibility map ────────────────────────────────────── */}
        <div className="flex flex-col gap-4">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500">
            Eligibility Map
          </h2>

          {(phase === "loading" || mapLoading) && !eligibilityMap
            ? <MapSkeleton />
            : eligibilityMap
              ? <EligibilityMapComponent map={eligibilityMap} />
              : (
                <div className="flex flex-col items-center gap-2 rounded-2xl border border-slate-700 p-8 text-center text-sm text-slate-500">
                  <Loader2 className="h-6 w-6 animate-spin text-indigo-400" />
                  Building your eligibility map…
                </div>
              )
          }
        </div>
      </div>
    </main>
  );
}
