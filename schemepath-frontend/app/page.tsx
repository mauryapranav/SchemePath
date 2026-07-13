"use client";

import React, { useState, useEffect } from "react";
import { BarChart3, MessageSquarePlus } from "lucide-react";
import ChatThread from "@/components/chat/ChatThread";
import ChatInput from "@/components/chat/ChatInput";
import GraphDrawer from "@/components/GraphDrawer";
import { useChat } from "@/hooks/useChat";

export default function ChatPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);

  // Initialize session ID on client side only to avoid hydration mismatch
  useEffect(() => {
    // Basic UUID fallback if crypto.randomUUID is not available
    const uuid = typeof crypto !== 'undefined' && crypto.randomUUID 
      ? crypto.randomUUID() 
      : `session-${Math.random().toString(36).substring(2, 15)}`;
    setSessionId(uuid);
  }, []);

  // Use the chat hook
  const { 
    messages, 
    isTyping, 
    graphData, 
    showGraph, 
    sendMessage, 
    sendDocumentResponse, 
    toggleGraph 
  } = useChat(sessionId || "temp-session");

  const startNewChat = () => {
    window.location.reload();
  };

  // Don't render until we have a session ID
  if (!sessionId) return <div className="flex min-h-screen bg-slate-900" />;

  return (
    <main className="flex h-screen w-full flex-col overflow-hidden bg-slate-900">
      
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-800 bg-slate-900/90 px-4 md:px-6 z-10">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 text-xl font-black tracking-tight text-slate-100">
            <span className="bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
              Scheme
            </span>
            <span>Path</span>
          </div>
          <span className="ml-2 rounded bg-indigo-500/20 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-indigo-400 border border-indigo-500/30">
            Beta
          </span>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={toggleGraph}
            className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm font-medium transition-all ${
              showGraph || graphData 
                ? "border-indigo-500/50 bg-indigo-500/10 text-indigo-300 hover:bg-indigo-500/20" 
                : "border-slate-700 bg-slate-800/50 text-slate-300 hover:bg-slate-700"
            }`}
          >
            <BarChart3 className="h-4 w-4" />
            <span className="hidden sm:inline">Map</span>
          </button>
          
          <button
            onClick={startNewChat}
            className="flex items-center justify-center rounded-lg border border-slate-700 bg-slate-800 p-1.5 text-slate-400 transition-all hover:bg-slate-700 hover:text-white"
            title="New Chat"
          >
            <MessageSquarePlus className="h-5 w-5" />
          </button>
        </div>
      </header>

      {/* ── Main Chat Area ─────────────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col overflow-hidden relative">
        <ChatThread 
          messages={messages} 
          isTyping={isTyping} 
          onQuickReply={sendMessage}
          onDocResponse={sendDocumentResponse}
        />
        
        <div className="mt-auto shrink-0 z-10">
          <ChatInput 
            onSendMessage={sendMessage} 
            isTyping={isTyping} 
          />
        </div>
      </div>

      {/* ── Graph Drawer ───────────────────────────────────────────────────── */}
      <GraphDrawer 
        isOpen={showGraph} 
        onClose={toggleGraph} 
        graphData={graphData} 
      />
      
    </main>
  );
}
