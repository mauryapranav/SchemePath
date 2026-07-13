import React from "react";
import { CheckCircle, Clock, Lock } from "lucide-react";
import { SchemeCardData } from "../../lib/types";

export default function SchemeCardInline({ scheme }: { scheme: SchemeCardData }) {
  // Determine styling based on status
  let statusBadge = null;
  let borderClass = "border-slate-700 hover:border-slate-500";
  let bgClass = "bg-slate-800/80";

  if (scheme.status === "confirmed") {
    borderClass = "border-green-500/30 hover:border-green-500/50";
    bgClass = "bg-green-950/20";
    statusBadge = (
      <span className="badge-confirmed mb-2">
        <CheckCircle className="h-3 w-3" /> Eligible
      </span>
    );
  } else if (scheme.status === "one_step") {
    borderClass = "border-yellow-500/30 hover:border-yellow-500/50";
    bgClass = "bg-yellow-950/20";
    statusBadge = (
      <span className="badge-one_step mb-2">
        <Clock className="h-3 w-3" /> 1 Step Away
      </span>
    );
  } else if (scheme.status === "locked") {
    borderClass = "border-slate-600 hover:border-slate-500";
    statusBadge = (
      <span className="badge-locked mb-2">
        <Lock className="h-3 w-3" /> Needs Details
      </span>
    );
  }

  return (
    <div className={`mt-3 mb-2 rounded-xl border p-4 transition-all duration-200 hover:shadow-md ${borderClass} ${bgClass}`}>
      {statusBadge}
      
      <h4 className="font-bold text-slate-100">{scheme.name}</h4>
      <p className="mt-1 text-sm text-slate-400 line-clamp-2">{scheme.description}</p>
      
      <div className="mt-3 flex items-center justify-between">
        <div className="text-sm font-semibold text-indigo-400">
          {scheme.benefit_amount || "Variable Benefit"}
        </div>
        
        {scheme.status === "confirmed" && scheme.application_url && (
          <a 
            href={scheme.application_url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="rounded bg-green-600 px-3 py-1 text-xs font-medium text-white hover:bg-green-500 transition-colors"
          >
            Apply →
          </a>
        )}
        
        {scheme.status === "one_step" && scheme.missing_requirements && scheme.missing_requirements.length > 0 && (
          <div className="text-xs text-yellow-500/80">
            Missing: {scheme.missing_requirements[0].name}
          </div>
        )}
      </div>
    </div>
  );
}
