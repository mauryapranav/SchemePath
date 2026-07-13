"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ChevronLeft, ExternalLink, CheckCircle2,
  Lock, RefreshCw, IndianRupee, Clock, Building2,
} from "lucide-react";
import { getSchemeDetail } from "@/lib/api";
import type { SchemeDetail } from "@/lib/types";
import PathVisualizer from "@/components/PathVisualizer";

// ── Skeletons ─────────────────────────────────────────────────────────────────
function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-xl bg-slate-700/40 ${className}`} />;
}

function DetailSkeleton() {
  return (
    <div className="flex flex-col gap-5">
      <Skeleton className="h-5 w-28" />
      <Skeleton className="h-9 w-3/4" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-5/6" />
      <Skeleton className="h-14 w-full" />
      <Skeleton className="h-48 w-full" />
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function SchemeDetailPage() {
  const { id: schemeId } = useParams<{ id: string }>();
  const router = useRouter();

  const [scheme,   setScheme]   = useState<SchemeDetail | null>(null);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await getSchemeDetail(schemeId);
      setScheme(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load scheme");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [schemeId]);

  // ── Error state ────────────────────────────────────────────────────────────
  if (error) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4 px-4">
        <p className="max-w-sm text-center text-sm text-red-400">{error}</p>
        <div className="flex gap-3">
          <button
            onClick={load}
            className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500"
          >
            <RefreshCw className="h-4 w-4" /> Retry
          </button>
          <button
            onClick={() => router.back()}
            className="rounded-xl border border-slate-700 px-4 py-2.5 text-sm text-slate-400 hover:text-slate-200"
          >
            Go back
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto min-h-screen max-w-3xl px-4 py-10">
      {/* ── Back button ──────────────────────────────────────────────────────── */}
      <button
        onClick={() => router.back()}
        className="mb-8 flex items-center gap-1.5 text-sm text-slate-400 transition hover:text-slate-200"
        id="back-btn"
      >
        <ChevronLeft className="h-4 w-4" />
        Back to Map
      </button>

      {loading ? (
        <DetailSkeleton />
      ) : scheme ? (
        <div className="flex flex-col gap-8">

          {/* ── Hero card ──────────────────────────────────────────────────── */}
          <div className="rounded-2xl border border-slate-700 bg-slate-800/50 p-6 shadow-lg">
            {/* Ministry */}
            <div className="mb-3 flex items-center gap-1.5 text-xs font-medium text-indigo-400">
              <Building2 className="h-3.5 w-3.5" />
              {scheme.ministry}
            </div>

            {/* Title */}
            <h1 className="mb-3 text-2xl font-black leading-tight text-slate-100">
              {scheme.name}
            </h1>

            {/* Description */}
            <p className="mb-6 text-sm leading-relaxed text-slate-400">
              {scheme.description}
            </p>

            {/* Benefit + meta */}
            <div className="flex flex-wrap gap-3">
              {scheme.benefit_amount && (
                <div className="flex items-center gap-2 rounded-xl bg-green-500/10 px-4 py-2.5 text-sm font-bold text-green-400 ring-1 ring-green-500/20">
                  <IndianRupee className="h-4 w-4" />
                  {scheme.benefit_amount}
                </div>
              )}
              {scheme.benefit_type && (
                <div className="flex items-center gap-2 rounded-xl bg-slate-700/50 px-4 py-2.5 text-sm text-slate-300">
                  {scheme.benefit_type}
                </div>
              )}
            </div>
          </div>

          {/* ── Requirements ───────────────────────────────────────────────── */}
          {scheme.requirements.length > 0 && (
            <section>
              <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-slate-500">
                Requirements
              </h2>
              <div className="flex flex-col gap-2">
                {scheme.requirements.map((req) => (
                  <div
                    key={req.id}
                    className="flex items-start gap-3 rounded-xl border border-slate-700/60 bg-slate-800/40 px-4 py-3"
                  >
                    {req.mandatory ? (
                      <Lock className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
                    ) : (
                      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-400" />
                    )}
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-200">{req.name}</p>
                      {req.description && (
                        <p className="mt-0.5 text-xs leading-relaxed text-slate-500">
                          {req.description}
                        </p>
                      )}
                      {req.category && (
                        <span className="mt-1 inline-block rounded-full bg-slate-700 px-2 py-0.5 text-[10px] text-slate-400 capitalize">
                          {req.category.replace("_", " ")}
                        </span>
                      )}
                    </div>
                    <span className="ml-auto shrink-0 text-[10px] font-semibold uppercase text-slate-600">
                      {req.mandatory ? "Mandatory" : "Optional"}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* ── Prerequisite schemes ───────────────────────────────────────── */}
          {scheme.prerequisite_schemes.length > 0 && (
            <section>
              <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-slate-500">
                Prerequisite Schemes
              </h2>
              <div className="flex flex-col gap-2">
                {scheme.prerequisite_schemes.map((preId) => (
                  <button
                    key={preId}
                    onClick={() => router.push(`/scheme/${preId}`)}
                    className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-800/40 px-4 py-3 text-left text-sm text-indigo-400 transition hover:border-indigo-500/50"
                  >
                    {preId}
                    <ChevronLeft className="h-4 w-4 rotate-180" />
                  </button>
                ))}
              </div>
            </section>
          )}

          {/* ── Path visualizer ────────────────────────────────────────────── */}
          <section>
            {/* We include this path visualization because seeing a transparent,
                step-by-step breakdown builds enormous user trust. It demystifies
                the "computer says no" black box and shows them exactly what's blocking them. */}
            <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-slate-500">
              Path Visualisation
            </h2>
            <PathVisualizer scheme={scheme} />
          </section>

          {/* ── Action links ───────────────────────────────────────────────── */}
          <div className="flex flex-col gap-3">
            {scheme.application_url && (
              <a
                href={scheme.application_url}
                target="_blank"
                rel="noopener noreferrer"
                id="apply-now-btn"
                className="flex items-center justify-center gap-2 rounded-2xl bg-indigo-600 py-4 text-sm font-bold text-white shadow-xl shadow-indigo-900/30 transition hover:bg-indigo-500 active:scale-[.98]"
              >
                <ExternalLink className="h-4 w-4" />
                Apply Now — Official Portal
              </a>
            )}
            {scheme.official_link && scheme.official_link !== scheme.application_url && (
              <a
                href={scheme.official_link}
                target="_blank"
                rel="noopener noreferrer"
                id="official-link-btn"
                className="flex items-center justify-center gap-2 rounded-2xl border border-slate-700 py-3.5 text-sm font-semibold text-slate-300 transition hover:border-indigo-500/50 hover:text-slate-100"
              >
                <ExternalLink className="h-4 w-4" />
                Official Website
              </a>
            )}
          </div>
        </div>
      ) : null}
    </main>
  );
}
