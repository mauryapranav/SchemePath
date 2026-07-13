"use client";

import { clsx } from "clsx";

interface Segment {
  key:   string;
  label: string;
}

const SEGMENTS: Segment[] = [
  { key: "age",      label: "Age"      },
  { key: "gender",   label: "Gender"   },
  { key: "state",    label: "State"    },
  { key: "caste",    label: "Caste"    },
  { key: "income",   label: "Income"   },
  { key: "location", label: "Location" },
  { key: "docs",     label: "Docs"     },
];

interface Props {
  /** 0.0 – 1.0 overall completion, used to derive filled segment count */
  completion: number;
  /** Optionally pass individual field flags to colour segments precisely */
  fields?: Partial<Record<string, boolean>>;
  label?: string;
  className?: string;
}

export default function ProgressBar({
  completion,
  fields,
  label = "Profile completeness",
  className,
}: Props) {
  const pct = Math.round(completion * 100);

  // If per-field flags are provided use them; otherwise fill proportionally
  const filledCount = fields
    ? SEGMENTS.filter((s) => fields[s.key]).length
    : Math.round(completion * SEGMENTS.length);

  return (
    <div className={clsx("flex flex-col gap-2", className)}>
      {/* Label row */}
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium text-slate-400">{label}</span>
        <span className="font-bold text-slate-300">{pct}%</span>
      </div>

      {/* Segmented bar */}
      <div
        className="flex h-2.5 w-full gap-1 overflow-hidden"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label}
      >
        {SEGMENTS.map((seg, i) => {
          const filled = fields ? !!fields[seg.key] : i < filledCount;
          return (
            <div
              key={seg.key}
              title={seg.label}
              className={clsx(
                "flex-1 rounded-full transition-all duration-500",
                filled
                  ? "bg-gradient-to-r from-indigo-500 to-purple-500"
                  : "bg-slate-700"
              )}
            />
          );
        })}
      </div>

      {/* Segment labels */}
      <div className="flex w-full gap-1">
        {SEGMENTS.map((seg, i) => {
          const filled = fields ? !!fields[seg.key] : i < filledCount;
          return (
            <div key={seg.key} className="flex flex-1 flex-col items-center gap-0.5">
              <span
                className={clsx(
                  "text-[9px] font-medium leading-none",
                  filled ? "text-indigo-400" : "text-slate-600"
                )}
              >
                {seg.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
