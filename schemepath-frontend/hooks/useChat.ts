import { useState, useEffect, useCallback, useRef } from "react";
import { ChatMessage, ServerMessage, ClientMessage, GraphNodeData, GraphEdgeData } from "../lib/types";

export function useChat(sessionId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [graphData, setGraphData] = useState<{ nodes: GraphNodeData[]; edges: GraphEdgeData[] } | null>(null);
  const [showGraph, setShowGraph] = useState(false);
  
  const wsRef = useRef<WebSocket | null>(null);
  const isConnectingRef = useRef(false);

  // Add welcome message on mount
  useEffect(() => {
    setMessages([
      {
        id: "welcome",
        role: "assistant",
        content: "Namaste! \ud83d\ude4f Tell me what's going on in your life \u2014 I'll find the right government schemes for you. For example, you could say something like 'I'm a farmer in Bihar' or 'I need help with medical expenses'.",
        timestamp: new Date()
      }
    ]);
  }, []);

  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN || isConnectingRef.current) return;
    
    isConnectingRef.current = true;
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = process.env.NEXT_PUBLIC_API_URL?.replace(/^https?:\/\//, "") || "localhost:8000";
    const wsUrl = `${protocol}//${host}/chat/${sessionId}`;
    
    console.log("Connecting to WebSocket:", wsUrl);
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log("WebSocket connected");
      setIsConnected(true);
      isConnectingRef.current = false;
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as ServerMessage;
        
        switch (data.type) {
          case "ai_message":
            setIsTyping(!data.done);
            setMessages(prev => {
              // If there's an existing streaming message, update it
              const lastMsg = prev[prev.length - 1];
              if (lastMsg && lastMsg.role === "assistant" && lastMsg.isStreaming) {
                const newMessages = [...prev];
                newMessages[newMessages.length - 1] = {
                  ...lastMsg,
                  content: data.content,
                  isStreaming: !data.done
                };
                return newMessages;
              } else {
                // Add new message
                return [...prev, {
                  id: crypto.randomUUID(),
                  role: "assistant",
                  content: data.content,
                  timestamp: new Date(),
                  isStreaming: !data.done
                }];
              }
            });
            break;
            
          case "scheme_cards":
            setMessages(prev => {
              const newMessages = [...prev];
              const lastMsg = newMessages[newMessages.length - 1];
              if (lastMsg && lastMsg.role === "assistant") {
                lastMsg.schemeCards = data.schemes;
              }
              return newMessages;
            });
            break;
            
          case "document_check":
            setMessages(prev => {
              const newMessages = [...prev];
              const lastMsg = newMessages[newMessages.length - 1];
              if (lastMsg && lastMsg.role === "assistant") {
                lastMsg.documentCheck = data.documents;
              }
              return newMessages;
            });
            break;
            
          case "quick_replies":
            setMessages(prev => {
              const newMessages = [...prev];
              const lastMsg = newMessages[newMessages.length - 1];
              if (lastMsg && lastMsg.role === "assistant") {
                lastMsg.quickReplies = data.options;
              }
              return newMessages;
            });
            break;
            
          case "procurement_guide":
            setMessages(prev => {
              const newMessages = [...prev];
              const lastMsg = newMessages[newMessages.length - 1];
              if (lastMsg && lastMsg.role === "assistant") {
                lastMsg.procurementGuide = data;
              }
              return newMessages;
            });
            break;
            
          case "status_update":
            setMessages(prev => [
              ...prev,
              {
                id: crypto.randomUUID(),
                role: "system",
                content: data.message,
                timestamp: new Date(),
                statusUpdate: data.message
              }
            ]);
            break;
            
          case "graph_data":
            setGraphData({ nodes: data.nodes, edges: data.edges });
            setShowGraph(true);
            break;
            
          case "error":
            console.error("Server error:", data.message);
            setIsTyping(false);
            setMessages(prev => [
              ...prev,
              {
                id: crypto.randomUUID(),
                role: "system",
                content: `Error: ${data.message}`,
                timestamp: new Date()
              }
            ]);
            break;
        }
      } catch (err) {
        console.error("Failed to parse WebSocket message:", err);
      }
    };
    
    ws.onclose = () => {
      console.log("WebSocket disconnected");
      setIsConnected(false);
      isConnectingRef.current = false;
      // Simple reconnect logic
      setTimeout(() => {
        if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED) {
          connectWebSocket();
        }
      }, 5000);
    };
    
    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
      isConnectingRef.current = false;
    };
    
    wsRef.current = ws;
  }, [sessionId]);

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connectWebSocket]);

  // Fallback REST sender
  const sendRestMessage = async (payload: ClientMessage) => {
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${baseUrl}/chat/${sessionId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: payload.type === "user_message" ? payload.content : JSON.stringify(payload) })
      });
      
      const data = await res.json();
      if (data.responses) {
        data.responses.forEach((msg: ServerMessage) => {
           // Simulate receiving via WS
           const event = new MessageEvent("message", { data: JSON.stringify(msg) });
           wsRef.current?.onmessage?.(event as any);
        });
      }
    } catch (err) {
      console.error("REST fallback failed:", err);
      setIsTyping(false);
    }
  };

  const sendPayload = (payload: ClientMessage) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload));
    } else {
      console.warn("WebSocket not connected, falling back to REST");
      sendRestMessage(payload);
    }
  };

  const sendMessage = (content: string) => {
    if (!content.trim()) return;
    
    // Add user message to UI immediately
    setMessages(prev => [
      ...prev,
      {
        id: crypto.randomUUID(),
        role: "user",
        content,
        timestamp: new Date()
      }
    ]);
    
    setIsTyping(true);
    sendPayload({ type: "user_message", content });
  };

  const sendDocumentResponse = (documentId: string, status: "have" | "dont_have" | "in_progress") => {
    // We don't add a user message bubble for this to keep UI clean,
    // we just let the agent respond
    setIsTyping(true);
    sendPayload({ type: "document_response", document_id: documentId, status });
  };

  const requestGraph = () => {
    sendPayload({ type: "request_graph" });
  };

  const toggleGraph = () => {
    if (!showGraph && !graphData) {
      requestGraph();
    } else {
      setShowGraph(!showGraph);
    }
  };

  return { 
    messages, 
    isConnected, 
    isTyping, 
    graphData, 
    showGraph, 
    sendMessage, 
    sendDocumentResponse, 
    requestGraph, 
    toggleGraph 
  };
}
