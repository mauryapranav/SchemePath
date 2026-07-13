"use client";

import React, { useMemo } from "react";
import dynamic from "next/dynamic";
import { X, CheckCircle, Clock, Lock } from "lucide-react";
import { GraphNodeData, GraphEdgeData } from "../lib/types";

// Import ReactFlow dynamically with no SSR to avoid hydration errors
const ReactFlow = dynamic(
  () => import("reactflow").then((mod) => mod.ReactFlow),
  { ssr: false, loading: () => <div className="flex h-full w-full items-center justify-center text-slate-500">Loading map...</div> }
);

const Background = dynamic(
  () => import("reactflow").then((mod) => mod.Background),
  { ssr: false }
);

const Controls = dynamic(
  () => import("reactflow").then((mod) => mod.Controls),
  { ssr: false }
);

interface Props {
  isOpen: boolean;
  onClose: () => void;
  graphData: { nodes: GraphNodeData[]; edges: GraphEdgeData[] } | null;
}

// Custom Node styles
const nodeStyles = {
  user: { background: "#4f46e5", color: "white", border: "none" },
  scheme: { 
    confirmed: { background: "#14532d", color: "#4ade80", border: "1px solid #22c55e" },
    one_step: { background: "#422006", color: "#facc15", border: "1px solid #eab308" },
    locked: { background: "#1e293b", color: "#94a3b8", border: "1px solid #475569" }
  },
  document: {
    missing: { background: "#450a0a", color: "#f87171", border: "1px dashed #ef4444" },
    have: { background: "#0f172a", color: "#60a5fa", border: "1px solid #3b82f6" }
  }
};

export default function GraphDrawer({ isOpen, onClose, graphData }: Props) {
  // Convert our simple graph data to ReactFlow format
  const { nodes, edges, counts } = useMemo(() => {
    if (!graphData) return { nodes: [], edges: [], counts: { confirmed: 0, one_step: 0, locked: 0 } };

    let cConfirmed = 0, cOneStep = 0, cLocked = 0;
    
    // Very basic layout algorithm
    const yOffsets = { scheme: 0, document: 0 };
    
    const rfNodes = graphData.nodes.map((node) => {
      let style = {};
      let x = 0, y = 0;
      
      if (node.type === "user") {
        style = nodeStyles.user;
        x = 50; y = 200;
      } else if (node.type === "scheme") {
        if (node.status === "confirmed") { style = nodeStyles.scheme.confirmed; cConfirmed++; }
        else if (node.status === "one_step") { style = nodeStyles.scheme.one_step; cOneStep++; }
        else { style = nodeStyles.scheme.locked; cLocked++; }
        
        x = 500; 
        y = 50 + (yOffsets.scheme * 80);
        yOffsets.scheme++;
      } else if (node.type === "document") {
        style = node.status === "have" ? nodeStyles.document.have : nodeStyles.document.missing;
        x = 250;
        y = 100 + (yOffsets.document * 60);
        yOffsets.document++;
      }

      return {
        id: node.id,
        position: { x, y },
        data: { label: node.label },
        style: { ...style, borderRadius: "8px", padding: "10px", width: 180, textAlign: "center" as const, fontSize: "12px", fontWeight: "bold" },
        type: "default"
      };
    });

    const rfEdges = graphData.edges.map((edge, i) => ({
      id: `e${i}-${edge.source}-${edge.target}`,
      source: edge.source,
      target: edge.target,
      label: edge.label,
      animated: !edge.satisfied,
      style: { stroke: edge.satisfied ? "#22c55e" : "#ef4444", strokeWidth: 2 },
      labelStyle: { fill: "#94a3b8", fontSize: 10 },
      labelBgStyle: { fill: "#0f172a" }
    }));

    return { nodes: rfNodes, edges: rfEdges, counts: { confirmed: cConfirmed, one_step: cOneStep, locked: cLocked } };
  }, [graphData]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop overlay */}
      <div 
        className="drawer-overlay"
        onClick={onClose}
      />
      
      {/* Slide-in panel */}
      <div className="drawer-panel fixed top-0 right-0 z-50 flex h-full w-full max-w-[450px] flex-col border-l border-slate-700 bg-slate-900 shadow-2xl">
        
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 p-4">
          <h2 className="flex items-center gap-2 text-lg font-bold text-slate-100">
            <span>📊</span> Your Eligibility Map
          </h2>
          <button 
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        
        {/* Summary Stats */}
        <div className="flex gap-2 p-4 pb-2">
          <div className="flex flex-1 flex-col items-center justify-center rounded-lg border border-green-500/20 bg-green-950/20 p-2">
            <CheckCircle className="mb-1 h-5 w-5 text-green-500" />
            <span className="text-xl font-black text-slate-100">{counts.confirmed}</span>
            <span className="text-[10px] uppercase tracking-wider text-slate-400">Available</span>
          </div>
          <div className="flex flex-1 flex-col items-center justify-center rounded-lg border border-yellow-500/20 bg-yellow-950/20 p-2">
            <Clock className="mb-1 h-5 w-5 text-yellow-500" />
            <span className="text-xl font-black text-slate-100">{counts.one_step}</span>
            <span className="text-[10px] uppercase tracking-wider text-slate-400">1 Step Away</span>
          </div>
          <div className="flex flex-1 flex-col items-center justify-center rounded-lg border border-slate-700/50 bg-slate-800/30 p-2">
            <Lock className="mb-1 h-5 w-5 text-slate-500" />
            <span className="text-xl font-black text-slate-100">{counts.locked}</span>
            <span className="text-[10px] uppercase tracking-wider text-slate-400">Locked</span>
          </div>
        </div>
        
        {/* Graph Area */}
        <div className="flex-1 overflow-hidden relative">
          {!graphData ? (
            <div className="flex h-full w-full items-center justify-center p-8 text-center text-slate-500">
              Your map is empty. Chat with SchemePath to discover schemes!
            </div>
          ) : (
            <ReactFlow
              nodes={nodes}
              edges={edges}
              fitView
              attributionPosition="bottom-right"
              className="bg-slate-900"
            >
              <Background color="#334155" gap={16} />
              <Controls className="bg-slate-800 fill-slate-300 border-slate-700" />
            </ReactFlow>
          )}
        </div>
      </div>
    </>
  );
}
