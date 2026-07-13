import React from "react";
import { ChatMessage as ChatMessageType } from "../../lib/types";
import SchemeCardInline from "./SchemeCardInline";
import DocumentCheckInline from "./DocumentCheckInline";
import ProcurementGuideInline from "./ProcurementGuideInline";
import QuickReplies from "./QuickReplies";

interface Props {
  message: ChatMessageType;
  onQuickReply: (option: string) => void;
  onDocResponse: (docId: string, status: "have" | "dont_have" | "in_progress") => void;
}

// Simple regex markdown parser for chat
function renderMarkdown(text: string) {
  if (!text) return null;
  
  // Split by newlines first
  const paragraphs = text.split('\n').filter(p => p.trim() !== '');
  
  return paragraphs.map((p, i) => {
    // Check if it's a list item
    const isListItem = p.match(/^(\d+\.|-|\*)\s+/);
    let content = p;
    
    // If list item, remove the marker for styling
    if (isListItem) {
      content = p.replace(/^(\d+\.|-|\*)\s+/, '');
    }

    // Process bold
    let parts = content.split(/(\*\*.*?\*\*)/g).map((part, j) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={j} className="font-semibold text-slate-100">{part.slice(2, -2)}</strong>;
      }
      return part;
    });

    if (isListItem) {
      return (
        <div key={i} className="flex gap-2 mt-1.5 mb-1.5 ml-2">
          <span className="text-indigo-400 select-none">•</span>
          <span>{parts}</span>
        </div>
      );
    }

    return <p key={i} className={i > 0 ? "mt-3" : ""}>{parts}</p>;
  });
}

export default function ChatMessage({ message, onQuickReply, onDocResponse }: Props) {
  // System messages (e.g. status updates)
  if (message.role === "system") {
    return (
      <div className="flex w-full justify-center py-2 animate-message-in">
        <div className="rounded-full bg-slate-800/50 px-4 py-1.5 text-xs font-medium text-slate-400 border border-slate-700/50">
          {message.content}
        </div>
      </div>
    );
  }

  const isUser = message.role === "user";

  return (
    <div className={`flex w-full py-4 animate-message-in ${isUser ? "justify-end" : "justify-start"}`}>
      <div 
        className={`flex max-w-[85%] flex-col md:max-w-[75%] ${
          isUser ? "items-end" : "items-start"
        }`}
      >
        {/* Message bubble */}
        <div 
          className={`rounded-2xl px-5 py-3.5 text-[15px] leading-relaxed ${
            isUser 
              ? "bg-indigo-600 text-white rounded-br-sm" 
              : "bg-slate-800 text-slate-200 rounded-bl-sm border border-slate-700"
          }`}
        >
          {renderMarkdown(message.content)}
          
          {/* Streaming cursor */}
          {message.isStreaming && (
            <span className="inline-block w-1.5 h-4 ml-1 bg-indigo-400 animate-pulse align-middle" />
          )}
        </div>

        {/* Attached structured content (only for AI) */}
        {!isUser && (
          <div className="w-full mt-2 flex flex-col gap-2">
            {/* Scheme Cards */}
            {message.schemeCards && message.schemeCards.length > 0 && (
              <div className="flex flex-col gap-2 w-full max-w-[400px]">
                {message.schemeCards.map(scheme => (
                  <SchemeCardInline key={scheme.id} scheme={scheme} />
                ))}
              </div>
            )}

            {/* Document Checks */}
            {message.documentCheck && message.documentCheck.length > 0 && (
              <div className="w-full max-w-[400px]">
                <DocumentCheckInline 
                  documents={message.documentCheck} 
                  onResponse={onDocResponse} 
                />
              </div>
            )}

            {/* Procurement Guide */}
            {message.procurementGuide && (
              <div className="w-full max-w-[450px]">
                <ProcurementGuideInline guide={message.procurementGuide} />
              </div>
            )}

            {/* Quick Replies */}
            {message.quickReplies && message.quickReplies.length > 0 && !message.isStreaming && (
              <QuickReplies 
                options={message.quickReplies} 
                onSelect={onQuickReply} 
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
