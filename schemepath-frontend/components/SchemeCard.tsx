"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  ExternalLink, ChevronDown, ChevronUp,
  IndianRupee, Clock, ArrowRight, AlertCircle,
} from "lucide-react";
import { clsx } from "clsx";
import type { EligibilityPath, EligibilityStatus } from "@/lib/types";
import PathVisualizer from "./PathVisualizer";

interface Props {
  path: EligibilityPath;
  userGoalTags?: string[];
}

const STATUS_BADGE: Record<EligibilityStatus, { label: string; cls: string }> = {
  confirmed: { label: "✓ Eligible",       cls: "bg-green-500/15 text-green-400 border-green-500/30" },
  one_step:  { label: "⚡ 1 step away",   cls: "bg-yellow-500/15 text-yellow-400 border-yellow-500/30" },
  locked:    { label: "🔒 Locked",         cls: "bg-slate-700 text-slate-400 border-slate-600" },
  unknown:   { label: "? Unknown",         cls: "bg-slate-700 text-slate-500 border-slate-600" },
};

export default function SchemeCard({ path, userGoalTags = [] }: Props) {
  const router = useRouter();
  const [expanded, setExpanded] = useState(false);
  const badge = STATUS_BADGE[path.status];

  const isConfirmed = path.status === "confirmed";
  const isOneStep   = path.status === "one_step";
  const isLocked    = path.status === "locked";

  return (
    <div
      className={clsx(
        "group rounded-2xl border bg-slate-800/50 p-5 shadow-sm transition-all duration-200",
        "hover:shadow-md hover:-translate-y-0.5",
        // We use these status-driven border colors so the user can visually scan 
        // a large list of schemes and immediately know their status without reading.
        isConfirmed && "border-green-500/20 hover:border-green-500/40",
        isOneStep   && "border-yellow-500/20 hover:border-yellow-500/40",
        isLocked    && "border-slate-700 hover:border-slate-600"
      )}
      id={`scheme-card-${path.scheme_id}`}
    >
      {/* Top row */}
      <div className="mb-2 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-bold text-slate-100 leading-snug">
            {path.scheme_name}
          </h3>
        </div>
        <span
          className={clsx(
            "shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-semibold",
            badge.cls
          )}
        >
          {badge.label}
        </span>
      </div>

      {/* Description */}
      <p className="mb-4 line-clamp-2 text-xs leading-relaxed text-slate-400">
        {path.scheme_description}
      </p>

      {/* Meta strip */}
      <div className="mb-4 flex flex-wrap gap-3">
        {path.benefit_amount && (
          <span
            className={clsx(
              "flex items-center gap-1 text-xs font-semibold",
              isConfirmed ? "text-green-400" : "text-slate-300"
            )}
          >
            <IndianRupee className="h-3 w-3" />
            {path.benefit_amount}
          </span>
        )}
        {path.estimated_time_days != null && (
          <span className="flex items-center gap-1 text-xs text-slate-500">
            <Clock className="h-3 w-3" />
            ~{path.estimated_time_days} days
          </span>
        )}
        {path.total_steps > 0 && (
          <span className="text-xs text-slate-500">
            {path.completed_steps}/{path.total_steps} requirements met
          </span>
        )}
      </div>

      {/* Goal Tags Match Highlight */}
      {path.scheme_tags && path.scheme_tags.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {path.scheme_tags.map((tag) => {
            const isMatch = userGoalTags.includes(tag);
            return (
              <span
                key={tag}
                className={clsx(
                  "rounded-full px-2 py-0.5 text-[10px] font-medium",
                  isMatch
                    ? "bg-blue-500/20 text-blue-400"
                    : "bg-slate-800 text-slate-500 border border-slate-700"
                )}
                title={isMatch ? "Matches your goal" : undefined}
              >
                {tag}
              </span>
            );
          })}
        </div>
      )}

      {/* ── Confirmed: Apply Now button ────────────────────────────── */}
      {isConfirmed && (
        <a
          href={`https://www.myscheme.gov.in/search`}   /* fallback – real URL comes from SchemeDetail */
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-2 rounded-xl bg-green-600 py-2.5 text-sm font-semibold text-white shadow-md shadow-green-900/30 transition hover:bg-green-500"
          id={`apply-btn-${path.scheme_id}`}
          onClick={(e) => e.stopPropagation()}
        >
          <ExternalLink className="h-4 w-4" />
          Apply Now
        </a>
      )}

      {/* ── One Step Away: expandable missing section ──────────────── */}
      {isOneStep && (
        <div className="rounded-xl border border-yellow-500/20 bg-yellow-500/5">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex w-full items-center justify-between px-4 py-2.5 text-xs font-semibold text-yellow-400"
            id={`expand-btn-${path.scheme_id}`}
          >
            <span className="flex items-center gap-2">
              <AlertCircle className="h-3.5 w-3.5" />
              What&apos;s missing?
            </span>
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>

          {expanded && (
            <div className="border-t border-yellow-500/10 px-4 pb-4 pt-3 flex flex-col gap-3">
              {path.missing_requirements.map((req) => (
                <div key={req.id} className="flex items-start gap-2">
                  <span className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-yellow-400" />
                  <div>
                    <p className="text-xs font-semibold text-slate-200">{req.name}</p>
                    {req.description && (
                      <p className="text-xs text-slate-500">{req.description}</p>
                    )}
                  </div>
                </div>
              ))}
              <button
                onClick={() => router.push(`/scheme/${path.scheme_id}`)}
                className="mt-1 flex items-center justify-center gap-2 rounded-lg border border-yellow-500/30 py-2 text-xs font-semibold text-yellow-400 transition hover:bg-yellow-500/10"
              >
                View full path <ArrowRight className="h-3.5 w-3.5" />
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── Locked: View Path button ───────────────────────────────── */}
      {isLocked && (
        <button
          onClick={() => router.push(`/scheme/${path.scheme_id}`)}
          className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-700 py-2.5 text-xs font-semibold text-slate-400 transition hover:border-slate-500 hover:text-slate-200"
          id={`view-path-btn-${path.scheme_id}`}
        >
          View Path <ArrowRight className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}
