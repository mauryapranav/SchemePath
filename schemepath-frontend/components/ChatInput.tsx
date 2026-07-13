"use client";

import { useState, useRef, KeyboardEvent } from "react";
import { useRouter } from "next/navigation";
import { Send, Loader2, Lock, Sparkles } from "lucide-react";
import { createProfile } from "@/lib/api";

export default function ChatInput() {
  const router = useRouter();
  const [value, setValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const EXAMPLES = [
    "I am a farmer in Bihar wanting to start a small business",
    "Street vendor in Mumbai, no bank account yet, have Aadhaar",
    "Rural woman in UP, BPL ration card, looking for health support",
    "45-year-old marginal farmer in Rajasthan with 2 acres of land",
  ];

  async function handleSubmit() {
    const trimmed = value.trim();
    if (!trimmed || loading) return;
    setError(null);
    setLoading(true);
    try {
      const profile = await createProfile(trimmed);
      sessionStorage.setItem("sp_profile_id", profile.id);
      sessionStorage.setItem("sp_profile_goal", profile.goal ?? trimmed);
      router.push(`/profile/${profile.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
      setLoading(false);
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(); }
  }

  function useExample(ex: string) {
    if (loading) return;
    setValue(ex);
    textareaRef.current?.focus();
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col items-center gap-6 px-4">
      {/* Heading */}
      <div className="flex flex-col items-center gap-2 text-center">
        <div className="flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-4 py-1.5 text-sm font-medium text-indigo-400">
          <Sparkles className="h-4 w-4" />
          AI-powered eligibility in seconds
        </div>
        <h1 className="text-4xl font-bold tracking-tight text-slate-100">
          Find every scheme you deserve
        </h1>
        <p className="max-w-md text-sm text-slate-400">
          Describe your situation and what you need help with. SchemePath maps all central
          and state schemes you qualify for — prioritised by your goal.
        </p>
      </div>

      {/* Input card */}
      <div className="w-full rounded-2xl border border-slate-700 bg-slate-800/60 p-4 shadow-xl backdrop-blur-sm focus-within:border-indigo-500/60 transition-colors">
        <textarea
          id="main-chat-input"
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          placeholder={`Describe your situation and your goal...\ne.g., "I need health insurance" or "I am a farmer wanting to start a small business"`}
          rows={4}
          className="w-full resize-none bg-transparent text-sm leading-relaxed text-slate-100 placeholder:text-slate-500 focus:outline-none disabled:opacity-50"
        />

        {/* Footer row */}
        <div className="mt-3 flex items-center justify-between gap-3">
          <p className="text-xs text-slate-500">
            <kbd className="rounded bg-slate-700 px-1 py-0.5 text-slate-400">Enter</kbd> to submit
            &nbsp;·&nbsp;
            <kbd className="rounded bg-slate-700 px-1 py-0.5 text-slate-400">Shift+Enter</kbd> new line
          </p>
          <button
            id="chat-submit-btn"
            onClick={handleSubmit}
            disabled={loading || !value.trim()}
            aria-label="Find my schemes"
            className="flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-900/40 transition hover:bg-indigo-500 active:scale-95 disabled:opacity-40"
          >
            {loading
              ? <><Loader2 className="h-4 w-4 animate-spin" />Analysing…</>
              : <><Send className="h-4 w-4" />Find my schemes</>}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-400">
          {error}
        </p>
      )}

      {/* Example prompts */}
      <div className="flex w-full flex-col gap-2">
        <p className="text-center text-xs font-medium text-slate-500 uppercase tracking-wider">
          Try an example
        </p>
        <div className="flex flex-wrap justify-center gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => useExample(ex)}
              disabled={loading}
              className="rounded-full border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-400 transition hover:border-indigo-500/50 hover:text-slate-200 disabled:opacity-40"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>

      {/* Privacy notice */}
      {/* We place this privacy notice right below the main call-to-action because 
          users in India are highly sensitive to Aadhaar data collection. Reassuring 
          them immediately reduces friction and increases completion rates. */}
      <p className="flex items-center gap-2 text-center text-xs text-slate-500">
        <Lock className="h-3.5 w-3.5 shrink-0 text-slate-500" />
        We don&apos;t store Aadhaar numbers or personal details.
        Your session auto-deletes in 24 hours.
      </p>
    </div>
  );
}
