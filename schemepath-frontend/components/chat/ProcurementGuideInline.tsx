import React from "react";
import { FileText, MapPin, IndianRupee, Clock } from "lucide-react";
import { ProcurementGuideData } from "../../lib/types";

export default function ProcurementGuideInline({ guide }: { guide: ProcurementGuideData }) {
  if (!guide || !guide.steps || guide.steps.length === 0) return null;

  return (
    <div className="mt-4 overflow-hidden rounded-xl border border-indigo-500/30 bg-slate-800/60">
      <div className="bg-indigo-500/10 px-4 py-3 border-b border-indigo-500/20 flex items-center gap-2">
        <FileText className="h-5 w-5 text-indigo-400" />
        <h4 className="font-semibold text-slate-200">How to get: {guide.document_name}</h4>
      </div>
      
      <div className="p-4 flex flex-col gap-4">
        {guide.steps.map((step, idx) => (
          <div key={idx} className="relative pl-6">
            {/* Step line connector */}
            {idx < guide.steps.length - 1 && (
              <div className="absolute left-[11px] top-6 bottom-[-16px] w-[2px] bg-slate-700"></div>
            )}
            
            {/* Step number circle */}
            <div className="absolute left-0 top-1 flex h-6 w-6 items-center justify-center rounded-full bg-indigo-500 text-xs font-bold text-white shadow-[0_0_0_4px_var(--color-surface)]">
              {step.step_number}
            </div>
            
            <div className="mb-1 font-medium text-slate-200">{step.action}</div>
            
            <div className="flex flex-col gap-1.5 mt-2">
              {step.location && (
                <div className="flex items-start gap-2 text-sm text-slate-400">
                  <MapPin className="h-4 w-4 mt-0.5 shrink-0 text-slate-500" />
                  <span>{step.location}</span>
                </div>
              )}
              
              <div className="flex gap-4">
                {step.cost && (
                  <div className="flex items-center gap-1.5 text-sm text-slate-400">
                    <IndianRupee className="h-4 w-4 text-slate-500" />
                    <span>{step.cost}</span>
                  </div>
                )}
                
                {step.time && (
                  <div className="flex items-center gap-1.5 text-sm text-slate-400">
                    <Clock className="h-4 w-4 text-slate-500" />
                    <span>{step.time}</span>
                  </div>
                )}
              </div>
              
              {step.prerequisites && step.prerequisites.length > 0 && (
                <div className="mt-1 text-xs text-amber-500/80 bg-amber-500/10 px-2 py-1 rounded inline-block">
                  Requires: {step.prerequisites.join(", ")}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
