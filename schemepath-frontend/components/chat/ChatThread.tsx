import React, { useEffect, useRef } from "react";
import { ChatMessage as ChatMessageType } from "../../lib/types";
import ChatMessage from "./ChatMessage";
import TypingIndicator from "./TypingIndicator";
import { ArrowDown } from "lucide-react";

interface Props {
  messages: ChatMessageType[];
  isTyping: boolean;
  onQuickReply: (option: string) => void;
  onDocResponse: (docId: string, status: "have" | "dont_have" | "in_progress") => void;
}

export default function ChatThread({ messages, isTyping, onQuickReply, onDocResponse }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [showScrollButton, setShowScrollButton] = React.useState(false);

  // Scroll to bottom whenever messages change or typing state changes
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isTyping]);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    // Show button if user scrolled up more than 100px from bottom
    setShowScrollButton(scrollHeight - scrollTop - clientHeight > 100);
  };

  const scrollToBottom = () => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <div className="relative flex h-full w-full flex-col">
      <div 
        ref={scrollRef}
        onScroll={handleScroll}
        className="chat-scroll flex-1 overflow-y-auto overflow-x-hidden p-4 pb-10"
      >
        <div className="mx-auto flex w-full max-w-4xl flex-col gap-1">
          {messages.map((msg) => (
            <ChatMessage 
              key={msg.id} 
              message={msg} 
              onQuickReply={onQuickReply}
              onDocResponse={onDocResponse}
            />
          ))}
          
          {isTyping && <TypingIndicator />}
          
          {/* Invisible div to scroll to */}
          <div ref={bottomRef} className="h-4 w-full" />
        </div>
      </div>

      {showScrollButton && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-6 left-1/2 -translate-x-1/2 rounded-full border border-slate-700 bg-slate-800/90 p-2 text-slate-300 shadow-lg backdrop-blur hover:bg-slate-700 hover:text-white transition-all z-10"
        >
          <ArrowDown className="h-5 w-5" />
        </button>
      )}
    </div>
  );
}
