"use client";

import { useMemo } from "react";
import type { EligibilityMap, EligibilityPath, EligibilityStatus } from "@/lib/types";
import SchemeCard from "./SchemeCard";
import ProgressBar from "./ProgressBar";

interface Props {
  map: EligibilityMap;
}

interface SectionConfig {
  status:    EligibilityStatus;
  emoji:     string;
  title:     string;
  subtitle:  string;
  headerCls: string;
  badgeCls:  string;
  empty:     string;
}

const SECTIONS: SectionConfig[] = [
  {
    status:    "confirmed",
    emoji:     "✅",
    title:     "Confirmed",
    subtitle:  "You can apply now!",
    headerCls: "border-green-500/20 bg-green-500/5",
    badgeCls:  "bg-green-500/20 text-green-400",
    empty:     "Answer more questions to confirm eligibility.",
  },
  {
    status:    "one_step",
    emoji:     "⚡",
    title:     "One Step Away",
    subtitle:  "Just one more thing needed",
    headerCls: "border-yellow-500/20 bg-yellow-500/5",
    badgeCls:  "bg-yellow-500/20 text-yellow-400",
    empty:     "No schemes are one step away yet.",
  },
  {
    status:    "locked",
    emoji:     "🔒",
    title:     "Locked",
    subtitle:  "More info or documents needed",
    headerCls: "border-slate-700 bg-slate-800/40",
    badgeCls:  "bg-slate-700 text-slate-400",
    empty:     "No locked schemes in this category yet. Answer more questions!",
  },
];

function GroupedSchemes({
  schemes = [],
  userGoalTags = [],
}: {
  schemes: EligibilityPath[];
  userGoalTags: string[];
}) {
  return (
    <div className="flex flex-col gap-6">
      {SECTIONS.map((cfg) => {
        const matching = schemes.filter(s => s.status === cfg.status);
        if (matching.length === 0) return null; // hide empty buckets inside grouped section to keep it clean
        return (
          <section className="flex flex-col gap-3" key={cfg.status} id={`section-${cfg.status}`}>
            <div className={`flex items-center justify-between rounded-xl border px-4 py-3 ${cfg.headerCls}`}>
              <div className="flex items-center gap-2">
                <span className="text-lg leading-none">{cfg.emoji}</span>
                <div>
                  <p className="text-sm font-bold text-slate-100">{cfg.title}</p>
                  <p className="text-xs text-slate-400">{cfg.subtitle}</p>
                </div>
              </div>
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${cfg.badgeCls}`}>
                {matching.length}
              </span>
            </div>
            <div className="flex flex-col gap-3">
              {matching.map((s) => (
                <SchemeCard key={s.scheme_id} path={s} userGoalTags={userGoalTags} />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}

export default function EligibilityMapComponent({ map }: Props) {
  const confirmedCount = map.confirmed_schemes?.length || 0;
  const oneStepCount   = map.one_step_schemes?.length || 0;
  const total          = map.total_schemes_analyzed || 0;

  const hasGoals = map.user_goal_tags && map.user_goal_tags.length > 0;
  const hasGoalRelevant = hasGoals && map.goal_relevant_schemes && map.goal_relevant_schemes.length > 0;
  const hasOther = map.other_schemes && map.other_schemes.length > 0;

  const showNudge = !hasGoals;

  return (
    <div className="flex flex-col gap-6">
      {/* Summary header */}
      <div className="rounded-2xl border border-slate-700 bg-slate-800/50 p-5 shadow-lg">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-slate-100">Your Eligibility Map</h2>
            <p className="text-xs text-slate-500">{total} schemes analysed</p>
          </div>
          <div className="flex gap-4 text-center">
            <div>
              <p className="text-2xl font-black text-green-400">{confirmedCount}</p>
              <p className="text-[10px] text-slate-500">confirmed</p>
            </div>
            <div>
              <p className="text-2xl font-black text-yellow-400">{oneStepCount}</p>
              <p className="text-[10px] text-slate-500">close</p>
            </div>
            <div>
              <p className="text-2xl font-black text-slate-400">{map.locked_schemes?.length || 0}</p>
              <p className="text-[10px] text-slate-500">locked</p>
            </div>
          </div>
        </div>
        <ProgressBar completion={map.profile_completion} label="Profile completeness" />
      </div>

      {showNudge && (
        <div className="rounded-xl border border-blue-500/20 bg-blue-500/10 p-4 text-sm text-blue-200">
          <strong>Tip:</strong> Try describing your goal more specifically (for example: "I need health insurance" or "I want to start farming") for better recommendations.
        </div>
      )}

      {hasGoalRelevant && (
        <div className="mt-2">
          <h2 className="mb-1 text-xl font-black text-white">Top Matches for Your Goal</h2>
          {map.user_goal && (
            <p className="mb-4 text-sm text-slate-400 italic">"{map.user_goal}"</p>
          )}
          {map.goal_relevant_schemes.some(s => s.status === 'confirmed') && (
            <div className="mb-4 rounded-xl bg-gradient-to-r from-green-600 to-emerald-500 p-4 shadow-lg shadow-green-900/50">
              <h3 className="font-bold text-white">🎉 You are ready to apply!</h3>
              <p className="text-xs text-green-100">You have all required documents for a scheme matching your goal.</p>
            </div>
          )}
          <GroupedSchemes schemes={map.goal_relevant_schemes || []} userGoalTags={map.user_goal_tags || []} />
        </div>
      )}

      {!hasGoalRelevant && hasOther && hasGoals && (
        <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-4 text-sm text-slate-300">
          We don't have schemes matching your goal yet, but here are other benefits you may qualify for.
        </div>
      )}

      {(hasOther || !hasGoals) && (
        <div className="mt-6">
          <h2 className="mb-4 text-lg font-bold text-slate-200">
            {!hasGoals ? "All Schemes" : "Other Schemes You May Qualify For"}
          </h2>
          <GroupedSchemes schemes={(!hasGoals ? map.goal_relevant_schemes : map.other_schemes) || []} userGoalTags={[]} />
        </div>
      )}
    </div>
  );
}
