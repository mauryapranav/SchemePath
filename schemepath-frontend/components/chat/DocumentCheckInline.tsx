import React, { useState } from "react";
import { Check, X, Clock } from "lucide-react";
import { DocumentCheckData } from "../../lib/types";

interface Props {
  documents: DocumentCheckData[];
  onResponse: (docId: string, status: "have" | "dont_have" | "in_progress") => void;
}

export default function DocumentCheckInline({ documents, onResponse }: Props) {
  const [answeredDocs, setAnsweredDocs] = useState<Record<string, string>>({});

  const handleResponse = (doc: DocumentCheckData, status: "have" | "dont_have" | "in_progress") => {
    setAnsweredDocs(prev => ({ ...prev, [doc.id]: status }));
    onResponse(doc.id, status);
  };

  if (!documents || documents.length === 0) return null;

  return (
    <div className="mt-4 flex flex-col gap-3">
      {documents.map(doc => {
        const answered = answeredDocs[doc.id];
        
        return (
          <div key={doc.id} className="rounded-xl border border-slate-700 bg-slate-800 p-4">
            <h4 className="font-medium text-slate-200 mb-1">{doc.name}</h4>
            <p className="text-sm text-slate-400 mb-3">{doc.question || `Do you have a ${doc.name}?`}</p>
            
            {answered ? (
              <div className="flex items-center text-sm font-medium">
                {answered === "have" && <span className="text-green-500 flex items-center gap-1"><Check className="h-4 w-4" /> You have this</span>}
                {answered === "dont_have" && <span className="text-red-400 flex items-center gap-1"><X className="h-4 w-4" /> You don't have this</span>}
                {answered === "in_progress" && <span className="text-yellow-500 flex items-center gap-1"><Clock className="h-4 w-4" /> You are getting this</span>}
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                <button 
                  onClick={() => handleResponse(doc, "have")}
                  className="flex items-center gap-1 rounded-md bg-green-500/10 border border-green-500/30 px-3 py-1.5 text-xs font-medium text-green-400 hover:bg-green-500/20 transition-colors"
                >
                  <Check className="h-3.5 w-3.5" /> Yes, I have it
                </button>
                <button 
                  onClick={() => handleResponse(doc, "dont_have")}
                  className="flex items-center gap-1 rounded-md bg-red-500/10 border border-red-500/30 px-3 py-1.5 text-xs font-medium text-red-400 hover:bg-red-500/20 transition-colors"
                >
                  <X className="h-3.5 w-3.5" /> No, I don't
                </button>
                <button 
                  onClick={() => handleResponse(doc, "in_progress")}
                  className="flex items-center gap-1 rounded-md bg-yellow-500/10 border border-yellow-500/30 px-3 py-1.5 text-xs font-medium text-yellow-500 hover:bg-yellow-500/20 transition-colors"
                >
                  <Clock className="h-3.5 w-3.5" /> Applied / Getting it
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
