"use client";

import dynamic from "next/dynamic";
import { useMemo } from "react";
import type { SchemeDetail, RequirementDetail } from "@/lib/types";

// ── Lazy-load React Flow (requires DOM) ───────────────────────────────────────
const ReactFlow = dynamic(
  () => import("reactflow").then((m) => m.default),
  { ssr: false, loading: () => <FlowSkeleton /> }
);
const Background = dynamic(() => import("reactflow").then((m) => m.Background), { ssr: false });
const Controls   = dynamic(() => import("reactflow").then((m) => m.Controls),   { ssr: false });
const MiniMap    = dynamic(() => import("reactflow").then((m) => m.MiniMap),    { ssr: false });

import "reactflow/dist/style.css";
import type { Node, Edge } from "reactflow";

// ── Helpers ───────────────────────────────────────────────────────────────────
function FlowSkeleton() {
  return (
    <div className="flex h-72 w-full animate-pulse items-center justify-center rounded-2xl border border-slate-700 bg-slate-800/40 text-slate-600 text-sm">
      Loading path graph…
    </div>
  );
}

// Node style factories
// We design these custom React Flow nodes to look like native UI components rather 
// than generic diagram boxes. By using distinct colors and emojis for "You", 
// "Document", and "Scheme", the user can intuitively understand the graph at a glance.
const nodeBase = {
  style: { fontFamily: "inherit", fontSize: 12, fontWeight: 600 },
};

function youNode(id: string, x: number, y: number): Node {
  return {
    id, position: { x, y },
    data: { label: "👤 You" },
    style: {
      ...nodeBase.style,
      background: "#166534",
      border: "2px solid #22c55e",
      borderRadius: "50%",
      color: "#bbf7d0",
      width: 80, height: 80,
      display: "flex", alignItems: "center", justifyContent: "center",
      boxShadow: "0 0 20px rgba(34,197,94,0.3)",
    },
    type: "default",
  };
}

function docNode(req: RequirementDetail, x: number, y: number, have: boolean): Node {
  return {
    id: `req-${req.id}`,
    position: { x, y },
    data: { label: have ? `✓ ${req.name}` : `🔒 ${req.name}` },
    style: {
      ...nodeBase.style,
      background: have ? "#1e3a5f" : "#3b1f1f",
      border: `2px solid ${have ? "#3b82f6" : "#ef4444"}`,
      borderRadius: 10,
      color: have ? "#93c5fd" : "#fca5a5",
      width: 160,
      padding: "8px 12px",
      textAlign: "center" as const,
    },
    type: "default",
  };
}

function schemeNode(name: string, x: number, y: number): Node {
  return {
    id: "scheme-target",
    position: { x, y },
    data: { label: `⭐ ${name}` },
    style: {
      ...nodeBase.style,
      background: "#14532d",
      border: "2px solid #22c55e",
      borderRadius: "50%",
      color: "#bbf7d0",
      width: 110, height: 110,
      display: "flex", alignItems: "center", justifyContent: "center",
      textAlign: "center" as const,
      boxShadow: "0 0 24px rgba(34,197,94,0.4)",
    },
    type: "default",
  };
}

function prereqNode(id: string, label: string, x: number, y: number): Node {
  return {
    id: `pre-${id}`,
    position: { x, y },
    data: { label: `📋 ${label}` },
    style: {
      ...nodeBase.style,
      background: "#312e81",
      border: "2px solid #818cf8",
      borderRadius: 10,
      color: "#c7d2fe",
      width: 160,
      padding: "8px 12px",
      textAlign: "center" as const,
    },
    type: "default",
  };
}

// ── Component ─────────────────────────────────────────────────────────────────
interface Props {
  scheme: SchemeDetail;
  /** Set of document IDs the user already has (optional — used for colouring) */
  userDocIds?: string[];
}

export default function PathVisualizer({ scheme, userDocIds = [] }: Props) {
  const { nodes, edges } = useMemo(() => {
    const nodes: Node[] = [];
    const edges: Edge[] = [];

    const COL_YOU    = 0;
    const COL_DOCS   = 260;
    const COL_SCHEME = 520;
    const ROW_GAP    = 110;
    const CENTER_Y   = Math.max((scheme.requirements.length - 1) * ROW_GAP * 0.5, 40);

    // YOU node
    nodes.push(youNode("you", COL_YOU, CENTER_Y - 40));

    // Requirement nodes
    scheme.requirements.forEach((req, i) => {
      const y = i * ROW_GAP;
      const have = userDocIds.includes(req.id);
      nodes.push(docNode(req, COL_DOCS, y, have));

      // YOU → req edge
      edges.push({
        id: `you-${req.id}`,
        source: "you",
        target: `req-${req.id}`,
        animated: !have,
        style: {
          stroke: have ? "#22c55e" : "#ef4444",
          strokeWidth: 2,
          strokeDasharray: have ? undefined : "6 3",
        },
        label: have ? "✓" : "missing",
        labelStyle: { fill: have ? "#22c55e" : "#ef4444", fontSize: 10 },
      });

      // req → scheme edge
      edges.push({
        id: `${req.id}-scheme`,
        source: `req-${req.id}`,
        target: "scheme-target",
        animated: have,
        style: {
          stroke: have ? "#22c55e" : "#475569",
          strokeWidth: have ? 2 : 1,
          opacity: have ? 1 : 0.3,
        },
      });
    });

    // Scheme target node
    nodes.push(schemeNode(scheme.name, COL_SCHEME, CENTER_Y - 55));

    // Prerequisite scheme nodes (above, stacked)
    scheme.prerequisite_schemes.forEach((preId, i) => {
      const y = -(i + 1) * ROW_GAP;
      nodes.push(prereqNode(preId, preId, COL_DOCS, y));
      edges.push({
        id: `pre-${preId}-scheme`,
        source: `pre-${preId}`,
        target: "scheme-target",
        animated: true,
        style: { stroke: "#818cf8", strokeWidth: 2 },
        label: "prerequisite",
        labelStyle: { fill: "#818cf8", fontSize: 10 },
      });
      edges.push({
        id: `you-pre-${preId}`,
        source: "you",
        target: `pre-${preId}`,
        style: { stroke: "#4f46e5", strokeWidth: 1, opacity: 0.5 },
      });
    });

    return { nodes, edges };
  }, [scheme, userDocIds]);

  if (scheme.requirements.length === 0 && scheme.prerequisite_schemes.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center rounded-2xl border border-slate-700 bg-slate-800/40 text-sm text-slate-500">
        No requirement graph data available for this scheme.
      </div>
    );
  }

  return (
    <div
      className="h-[400px] w-full overflow-hidden rounded-2xl border border-slate-700 bg-slate-900"
      id="path-visualizer"
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#334155" gap={20} size={1} />
        <Controls showInteractive={false} className="!bg-slate-800 !border-slate-700" />
        <MiniMap
          nodeColor={(n) => {
            if (n.id === "you" || n.id === "scheme-target") return "#22c55e";
            if (n.id.startsWith("pre-")) return "#818cf8";
            return n.style?.border?.toString().includes("22c55e") ? "#3b82f6" : "#ef4444";
          }}
          maskColor="rgba(15,23,42,0.7)"
          className="!bg-slate-800 !border-slate-700"
        />
      </ReactFlow>
    </div>
  );
}
