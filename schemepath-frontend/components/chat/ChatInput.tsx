import React, { useState, useRef, useEffect } from "react";
import { SendHorizonal } from "lucide-react";

interface Props {
  onSendMessage: (message: string) => void;
  isTyping: boolean;
}

export default function ChatInput({ onSendMessage, isTyping }: Props) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  }, [input]);

  const handleSend = () => {
    if (input.trim() && !isTyping) {
      onSendMessage(input.trim());
      setInput("");
      // Reset height
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="w-full border-t border-slate-800 bg-slate-900/95 p-4 backdrop-blur-md">
      <div className="mx-auto flex w-full max-w-4xl items-end gap-3 rounded-2xl border border-slate-700 bg-slate-800/50 p-2 pl-4 focus-within:border-indigo-500/50 focus-within:bg-slate-800 shadow-sm transition-all">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Tell me what's going on in your life..."
          disabled={isTyping}
          className="max-h-[150px] min-h-[24px] w-full resize-none bg-transparent py-3 text-[15px] text-slate-100 placeholder-slate-500 outline-none disabled:opacity-50"
          rows={1}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || isTyping}
          className="mb-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-500 text-white transition-all hover:bg-indigo-400 disabled:bg-slate-700 disabled:text-slate-500"
        >
          <SendHorizonal className="h-5 w-5" />
        </button>
      </div>
      <div className="mx-auto mt-2 max-w-4xl text-center text-xs text-slate-500">
        SchemePath can make mistakes. Verify important information.
      </div>
    </div>
  );
}
