"use client";

import { useState } from "react";
import { Loader2, Zap, SkipForward, HelpCircle } from "lucide-react";
import { clsx } from "clsx";
import type { NextQuestion, QuestionOption } from "@/lib/types";

interface Props {
  question: NextQuestion;
  onAnswer:    (questionId: string, answer: unknown) => void;
  onSkip?:     (questionId: string) => void;
  onDontKnow?: (questionId: string) => void;
  submitting?: boolean;
}

export default function QuestionCard({
  question,
  onAnswer,
  onSkip,
  onDontKnow,
  submitting = false,
}: Props) {
  const [selected,      setSelected]      = useState<string | boolean | null>(null);
  const [multiSelected, setMultiSelected] = useState<Set<string>>(new Set());
  const [textValue,     setTextValue]     = useState("");
  const [numberValue,   setNumberValue]   = useState("");
  const [visible,       setVisible]       = useState(true);

  function toggleMulti(id: string) {
    setMultiSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function buildAnswer(): unknown {
    switch (question.question_type) {
      case "multi_select": return Array.from(multiSelected);
      case "text":         return textValue.trim();
      case "number":       return numberValue !== "" ? Number(numberValue) : null;
      default:             return selected;
    }
  }

  function isReady(): boolean {
    switch (question.question_type) {
      case "multi_select": return multiSelected.size > 0;
      case "text":         return textValue.trim().length > 0;
      case "number":       return numberValue !== "";
      default:             return selected !== null;
    }
  }

  function resetState() {
    setSelected(null);
    setMultiSelected(new Set());
    setTextValue("");
    setNumberValue("");
  }

  function animateThen(cb: () => void) {
    setVisible(false);
    setTimeout(() => { cb(); setVisible(true); }, 200);
  }

  function handleSubmit() {
    if (!isReady() || submitting) return;
    animateThen(() => { onAnswer(question.question_id, buildAnswer()); resetState(); });
  }

  function handleSkip() {
    animateThen(() => { onSkip?.(question.question_id); resetState(); });
  }

  function handleDontKnow() {
    animateThen(() => { onDontKnow?.(question.question_id); resetState(); });
  }

  const opts: QuestionOption[] = question.options ?? [];

  return (
    <div
      className={clsx(
        "rounded-2xl border border-slate-700 bg-white/[0.03] p-6 shadow-xl backdrop-blur-sm transition-opacity duration-200",
        visible ? "opacity-100" : "opacity-0"
      )}
      id={`question-card-${question.question_id}`}
    >
      {/* Context badge */}
      <div className="mb-5 flex items-center gap-2">
        <span className="flex items-center gap-1.5 rounded-full border border-blue-500/30 bg-blue-500/10 px-3 py-1 text-xs font-semibold text-blue-400">
          <Zap className="h-3.5 w-3.5" />
          This helps us find {question.schemes_unlocked_estimate} scheme
          {question.schemes_unlocked_estimate !== 1 ? "s" : ""}
        </span>
        <span className="rounded-full border border-slate-700 px-2.5 py-1 text-xs text-slate-500 capitalize">
          {question.category.replace("_", " ")}
        </span>
      </div>

      {/* Question text */}
      <h2 className="mb-1 text-xl font-semibold leading-snug text-slate-100">
        {question.question_text}
      </h2>
      {question.context && (
        <p className="mb-6 text-sm text-slate-400">{question.context}</p>
      )}

      {/* ── single_choice ─────────────────────────────────────────────── */}
      {/* We use this branching logic because different graph requirement categories 
          need entirely different UI paradigms. E.g., 'income' is a single choice bucket, 
          but 'documents' is a multi-select checklist. */}
      {question.question_type === "single_choice" && (
        <div className="flex flex-col gap-2">
          {opts.map((opt) => (
            <button
              key={opt.id}
              id={`opt-${opt.id}`}
              onClick={() => setSelected(opt.id)}
              className={clsx(
                "w-full rounded-xl border px-4 py-3 text-left text-sm font-medium transition",
                selected === opt.id
                  ? "border-blue-500 bg-blue-500/10 text-blue-300 shadow-sm shadow-blue-900/30"
                  : "border-slate-700 text-slate-300 hover:border-slate-500 hover:bg-white/[0.03]"
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}

      {/* ── multi_select ──────────────────────────────────────────────── */}
      {question.question_type === "multi_select" && (
        <div className="flex flex-col gap-2">
          {opts.map((opt) => (
            <label
              key={opt.id}
              htmlFor={`ms-${opt.id}`}
              className={clsx(
                "flex cursor-pointer items-center gap-3 rounded-xl border px-4 py-3 text-sm transition",
                multiSelected.has(opt.id)
                  ? "border-blue-500 bg-blue-500/10 text-blue-300"
                  : "border-slate-700 text-slate-300 hover:border-slate-500"
              )}
            >
              <input
                type="checkbox"
                id={`ms-${opt.id}`}
                checked={multiSelected.has(opt.id)}
                onChange={() => toggleMulti(opt.id)}
                className="h-4 w-4 accent-blue-500"
              />
              {opt.label}
            </label>
          ))}
          {multiSelected.size > 0 && (
            <p className="mt-1 text-xs text-slate-500">
              {multiSelected.size} selected
            </p>
          )}
        </div>
      )}

      {/* ── boolean ───────────────────────────────────────────────────── */}
      {question.question_type === "boolean" && (
        <div className="flex gap-3">
          {[
            { id: "yes", val: true,  label: "Yes" },
            { id: "no",  val: false, label: "No"  },
          ].map((opt) => (
            <button
              key={opt.id}
              id={`bool-${opt.id}`}
              onClick={() => setSelected(opt.val)}
              className={clsx(
                "flex-1 rounded-xl border py-4 text-sm font-semibold transition",
                selected === opt.val
                  ? "border-blue-500 bg-blue-500/10 text-blue-300 shadow-sm shadow-blue-900/30"
                  : "border-slate-700 text-slate-300 hover:border-slate-500"
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}

      {/* ── number ────────────────────────────────────────────────────── */}
      {question.question_type === "number" && (
        <input
          id="q-number-input"
          type="number"
          value={numberValue}
          onChange={(e) => setNumberValue(e.target.value)}
          placeholder="Enter a number…"
          className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-100 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
        />
      )}

      {/* ── text ──────────────────────────────────────────────────────── */}
      {question.question_type === "text" && (
        <textarea
          id="q-text-input"
          value={textValue}
          onChange={(e) => setTextValue(e.target.value)}
          rows={3}
          placeholder="Type your answer…"
          className="w-full resize-none rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-100 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
        />
      )}

      {/* Actions */}
      <div className="mt-6 flex items-center gap-3">
        <button
          id="question-submit-btn"
          onClick={handleSubmit}
          disabled={!isReady() || submitting}
          className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-blue-600 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-900/30 transition hover:bg-blue-500 active:scale-[.98] disabled:opacity-40"
        >
          {submitting
            ? <><Loader2 className="h-4 w-4 animate-spin" /> Saving…</>
            : "Continue →"}
        </button>

        <button
          id="dont-know-btn"
          onClick={handleDontKnow}
          disabled={submitting}
          className="rounded-xl border border-slate-700 px-4 py-3 text-sm text-slate-400 transition hover:border-slate-500 hover:text-slate-200 disabled:opacity-40"
          title="I don't know"
        >
          <HelpCircle className="h-4 w-4" />
        </button>

        <button
          id="skip-btn"
          onClick={handleSkip}
          disabled={submitting}
          className="rounded-xl border border-slate-700 px-4 py-3 text-sm text-slate-400 transition hover:border-slate-500 hover:text-slate-200 disabled:opacity-40"
          title="Skip for now"
        >
          <SkipForward className="h-4 w-4" />
        </button>
      </div>

      {/* Skip / don't know labels */}
      <div className="mt-2 flex justify-end gap-4 text-[10px] text-slate-600">
        <span>? = I don&apos;t know</span>
        <span>⏭ = Skip for now</span>
      </div>
    </div>
  );
}
