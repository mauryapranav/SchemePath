import React from "react";

export default function TypingIndicator() {
  return (
    <div className="flex w-full py-4 justify-start animate-message-in">
      <div className="flex max-w-[85%] items-start">
        <div className="rounded-2xl rounded-bl-sm border border-slate-700 bg-slate-800 px-5 py-4">
          <div className="flex items-center gap-1.5">
            <div className="h-2 w-2 rounded-full bg-slate-500 typing-dot"></div>
            <div className="h-2 w-2 rounded-full bg-slate-500 typing-dot"></div>
            <div className="h-2 w-2 rounded-full bg-slate-500 typing-dot"></div>
          </div>
        </div>
      </div>
    </div>
  );
}
