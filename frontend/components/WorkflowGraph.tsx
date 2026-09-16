// frontend/components/WorkflowGraph.tsx
"use client";

import React, { useState, useEffect } from "react";
import {
  MessageSquare,
  Compass,
  MapPin,
  Waves,
  Scale,
  Satellite,
  FileText,
  Navigation,
  CheckCircle2,
  Shield,
  Globe,
  AlertTriangle,
  Zap,
  Radio,
  TrendingUp,
  Anchor,
  X,
  Maximize2,
  Plus,
  Minus,
} from "lucide-react";
import { TraceEntry } from "@/lib/types";

interface WorkflowGraphProps {
  trace: TraceEntry[];
  isStreaming?: boolean;
}

interface WorkflowNode {
  id: string;
  label: string;
  sublabel: string;
  x: number;
  y: number;
  width: number;
  height: number;
  type: "user" | "planner" | "agent" | "connector" | "output";
  agentKey?: string;
  connectorName?: string;
  themeColor: "red" | "green" | "amber";
}

function renderNodeIcon(id: string) {
  const cls = "w-3.5 h-3.5";
  switch (id) {
    case "user_message":
      return <MessageSquare className={`${cls} text-emerald-600`} />;
    case "planner":
      return <Compass className={`${cls} text-rose-600`} />;
    case "geospatial":
      return <MapPin className={`${cls} text-emerald-600`} />;
    case "weather":
      return <Waves className={`${cls} text-emerald-600`} />;
    case "risk":
      return <Scale className={`${cls} text-emerald-600`} />;
    case "ocean_analytics":
      return <Satellite className={`${cls} text-emerald-600`} />;
    case "reporting":
      return <FileText className={`${cls} text-emerald-600`} />;
    case "route":
      return <Navigation className={`${cls} text-amber-600`} />;
    case "answer_trace":
      return <CheckCircle2 className={`${cls} text-emerald-600`} />;
    case "osm_geocoding":
      return <MapPin className={`${cls} text-slate-600`} />;
    case "overpass_mpa":
      return <Shield className={`${cls} text-slate-600`} />;
    case "incois_osf":
      return <Waves className={`${cls} text-slate-600`} />;
    case "open_meteo":
      return <Globe className={`${cls} text-slate-600`} />;
    case "imd_alerts":
      return <AlertTriangle className={`${cls} text-slate-600`} />;
    case "gdacs_storm":
      return <Zap className={`${cls} text-slate-600`} />;
    case "isro_mosdac":
      return <Radio className={`${cls} text-slate-600`} />;
    case "noaa_sst":
      return <TrendingUp className={`${cls} text-slate-600`} />;
    case "searoute_net":
      return <Anchor className={`${cls} text-slate-600`} />;
    default:
      return <FileText className={cls} />;
  }
}

// Canvas coordinate space: 700 x 860
const NODES: WorkflowNode[] = [
  // ── 1. ENTRY: USER MESSAGE ──
  {
    id: "user_message",
    label: "User message",
    sublabel: "Natural Language Query",
    x: 350,
    y: 48,
    width: 170,
    height: 44,
    type: "user",
    themeColor: "green",
  },

  // ── 2. PLANNER NODE ──
  {
    id: "planner",
    label: "planner",
    sublabel: "Goal & Branch Intent",
    x: 350,
    y: 140,
    width: 170,
    height: 44,
    type: "planner",
    agentKey: "planner",
    themeColor: "red",
  },

  // ── 3. CENTER SPINE: ONE LOCATION PIPELINE ──
  {
    id: "geospatial",
    label: "geospatial",
    sublabel: "Sector & Coordinates",
    x: 350,
    y: 245,
    width: 170,
    height: 44,
    type: "agent",
    agentKey: "geospatial",
    themeColor: "green",
  },
  {
    id: "weather",
    label: "weather",
    sublabel: "MetOcean Wave & Wind",
    x: 350,
    y: 350,
    width: 170,
    height: 44,
    type: "agent",
    agentKey: "weather",
    themeColor: "green",
  },
  {
    id: "risk",
    label: "risk",
    sublabel: "Safety & Hazard Scoring",
    x: 350,
    y: 455,
    width: 170,
    height: 44,
    type: "agent",
    agentKey: "risk",
    themeColor: "green",
  },
  {
    id: "ocean_analytics",
    label: "ocean_analytics",
    sublabel: "SST & Chlorophyll-a",
    x: 350,
    y: 560,
    width: 180,
    height: 44,
    type: "agent",
    agentKey: "ocean_analytics",
    themeColor: "green",
  },
  {
    id: "reporting",
    label: "reporting",
    sublabel: "Advisory Synthesis",
    x: 350,
    y: 675,
    width: 170,
    height: 44,
    type: "agent",
    agentKey: "reporting",
    themeColor: "green",
  },

  // ── 4. RIGHT BRANCH: TWO LOCATIONS PIPELINE ──
  {
    id: "route",
    label: "route",
    sublabel: "Corridor & Detour Scan",
    x: 570,
    y: 400,
    width: 170,
    height: 44,
    type: "agent",
    agentKey: "route",
    themeColor: "amber",
  },

  // ── 5. FINAL TERMINAL NODE ──
  {
    id: "answer_trace",
    label: "Answer + trace",
    sublabel: "Verified Marine Advisory",
    x: 350,
    y: 785,
    width: 180,
    height: 44,
    type: "output",
    themeColor: "green",
  },

  // ── 6. TELEMETRY CONNECTORS (LEAVES) ──
  // Geospatial leaves
  {
    id: "osm_geocoding",
    label: "OSM Nominatim",
    sublabel: "Bathymetry Grid",
    x: 120,
    y: 225,
    width: 148,
    height: 38,
    type: "connector",
    connectorName: "OSM/Nominatim",
    themeColor: "green",
  },
  {
    id: "overpass_mpa",
    label: "Overpass MPA",
    sublabel: "Protected Zones",
    x: 120,
    y: 270,
    width: 148,
    height: 38,
    type: "connector",
    connectorName: "overpass-osm-protected-areas",
    themeColor: "green",
  },

  // Weather leaves
  {
    id: "incois_osf",
    label: "INCOIS OSF & PFZ",
    sublabel: "Ocean State",
    x: 120,
    y: 330,
    width: 148,
    height: 38,
    type: "connector",
    connectorName: "INCOIS",
    themeColor: "green",
  },
  {
    id: "open_meteo",
    label: "Open-Meteo",
    sublabel: "Swell & Waves",
    x: 120,
    y: 375,
    width: 148,
    height: 38,
    type: "connector",
    connectorName: "open-meteo-marine",
    themeColor: "green",
  },

  // Risk leaves
  {
    id: "imd_alerts",
    label: "IMD Coastal",
    sublabel: "Cyclone Watch",
    x: 120,
    y: 435,
    width: 148,
    height: 38,
    type: "connector",
    connectorName: "IMD",
    themeColor: "green",
  },
  {
    id: "gdacs_storm",
    label: "GDACS / Blitz",
    sublabel: "Lightning Feeds",
    x: 120,
    y: 480,
    width: 148,
    height: 38,
    type: "connector",
    connectorName: "gdacs-cyclone-tracker",
    themeColor: "green",
  },

  // Ocean leaves
  {
    id: "isro_mosdac",
    label: "ISRO-MOSDAC",
    sublabel: "Satellite Telemetry",
    x: 570,
    y: 540,
    width: 148,
    height: 38,
    type: "connector",
    connectorName: "ISRO-MOSDAC",
    themeColor: "green",
  },
  {
    id: "noaa_sst",
    label: "NOAA ERDDAP",
    sublabel: "7-Day SST Trend",
    x: 570,
    y: 585,
    width: 148,
    height: 38,
    type: "connector",
    connectorName: "noaa-erddap-sst",
    themeColor: "green",
  },

  // Route leaves
  {
    id: "searoute_net",
    label: "Searoute Net",
    sublabel: "Waypoints",
    x: 570,
    y: 460,
    width: 148,
    height: 38,
    type: "connector",
    connectorName: "searoute-maritime-network",
    themeColor: "green",
  },
];

interface WorkflowEdge {
  id: string;
  from: string;
  to: string;
  branch?: "one_location" | "two_locations" | "no_location";
  agentKey?: string;
  color: string;
  customPath?: string;
}

const EDGES: WorkflowEdge[] = [
  // User to Planner
  { id: "e-user-planner", from: "user_message", to: "planner", agentKey: "planner", color: "#e11d48" },

  // Planner Branch 1: "one location" (Main Spine)
  { id: "e-planner-geo", from: "planner", to: "geospatial", branch: "one_location", agentKey: "geospatial", color: "#059669" },
  { id: "e-geo-weather", from: "geospatial", to: "weather", agentKey: "weather", color: "#059669" },
  { id: "e-weather-risk", from: "weather", to: "risk", agentKey: "risk", color: "#059669" },
  { id: "e-risk-ocean", from: "risk", to: "ocean_analytics", agentKey: "ocean_analytics", color: "#059669" },
  { id: "e-ocean-reporting", from: "ocean_analytics", to: "reporting", agentKey: "reporting", color: "#059669" },

  // Planner Branch 2: "two locations" (Route branch)
  {
    id: "e-planner-route",
    from: "planner",
    to: "route",
    branch: "two_locations",
    agentKey: "route",
    color: "#d97706",
    customPath: "M 432 140 C 530 140, 570 240, 570 379",
  },
  {
    id: "e-route-reporting",
    from: "route",
    to: "reporting",
    agentKey: "reporting",
    color: "#d97706",
    customPath: "M 570 421 C 570 540, 480 675, 432 675",
  },

  // Planner Branch 3: "no location" (Bypass around the left straight to reporting)
  {
    id: "e-planner-bypass-reporting",
    from: "planner",
    to: "reporting",
    branch: "no_location",
    agentKey: "reporting",
    color: "#64748b",
    customPath: "M 268 140 C 35 140, 35 675, 268 675",
  },

  // Reporting to Terminal
  { id: "e-reporting-terminal", from: "reporting", to: "answer_trace", agentKey: "reporting", color: "#059669" },

  // Telemetry leaf edges
  { id: "e-geo-osm", from: "geospatial", to: "osm_geocoding", agentKey: "geospatial", color: "#059669" },
  { id: "e-geo-mpa", from: "geospatial", to: "overpass_mpa", agentKey: "geospatial", color: "#059669" },
  { id: "e-weather-incois", from: "weather", to: "incois_osf", agentKey: "weather", color: "#059669" },
  { id: "e-weather-meteo", from: "weather", to: "open_meteo", agentKey: "weather", color: "#059669" },
  { id: "e-risk-imd", from: "risk", to: "imd_alerts", agentKey: "risk", color: "#059669" },
  { id: "e-risk-gdacs", from: "risk", to: "gdacs_storm", agentKey: "risk", color: "#059669" },
  { id: "e-ocean-isro", from: "ocean_analytics", to: "isro_mosdac", agentKey: "ocean_analytics", color: "#059669" },
  { id: "e-ocean-noaa", from: "ocean_analytics", to: "noaa_sst", agentKey: "ocean_analytics", color: "#059669" },
  { id: "e-route-searoute", from: "route", to: "searoute_net", agentKey: "route", color: "#d97706" },
];

export function WorkflowGraph({ trace, isStreaming = false }: WorkflowGraphProps) {
  const [zoom, setZoom] = useState(1);
  const [selectedNode, setSelectedNode] = useState<WorkflowNode | null>(null);

  // Simulation steps for flow animation
  const [simStep, setSimStep] = useState<number | null>(null);

  useEffect(() => {
    if (simStep === null) return;
    if (simStep >= 7) {
      const t = setTimeout(() => setSimStep(null), 3500);
      return () => clearTimeout(t);
    }
    const timer = setTimeout(() => {
      setSimStep((s) => (s !== null ? s + 1 : null));
    }, 1100);
    return () => clearTimeout(timer);
  }, [simStep]);

  function handleStartSimulation() {
    setSimStep(0);
  }

  // Determine which agents have executed
  const executedAgents = new Set(
    simStep !== null
      ? [
          ...(simStep >= 1 ? ["planner"] : []),
          ...(simStep >= 2 ? ["geospatial"] : []),
          ...(simStep >= 3 ? ["weather"] : []),
          ...(simStep >= 4 ? ["risk"] : []),
          ...(simStep >= 5 ? ["ocean_analytics"] : []),
          ...(simStep >= 6 ? ["reporting"] : []),
        ]
      : trace.map((t) => t.agent.toLowerCase())
  );

  const effectiveStreaming = isStreaming || (simStep !== null && simStep < 7);

  const activeAgent =
    simStep !== null
      ? simStep === 0
        ? "planner"
        : simStep === 1
        ? "geospatial"
        : simStep === 2
        ? "weather"
        : simStep === 3
        ? "risk"
        : simStep === 4
        ? "ocean_analytics"
        : simStep === 5
        ? "reporting"
        : null
      : isStreaming && trace.length > 0
      ? trace[trace.length - 1].agent.toLowerCase()
      : isStreaming
      ? "planner"
      : null;

  const isQueryActive = effectiveStreaming || trace.length > 0 || simStep !== null;

  // Determine active branch based on trace
  const hasRouteInTrace = executedAgents.has("route") || activeAgent === "route";
  const hasGeospatialInTrace = executedAgents.has("geospatial") || activeAgent === "geospatial";
  const isNoLocation =
    executedAgents.has("reporting") && !hasRouteInTrace && !hasGeospatialInTrace;

  function getNodeById(id: string): WorkflowNode | undefined {
    return NODES.find((n) => n.id === id);
  }

  // Generate smooth straight or cubic bezier curves between nodes
  function getEdgePath(edge: WorkflowEdge, from: WorkflowNode, to: WorkflowNode): string {
    if (edge.customPath) return edge.customPath;

    // Telemetry leaf connectors (horizontal from agent edge to leaf edge)
    if (to.type === "connector") {
      if (to.x < from.x) {
        // Left side connector
        const startX = from.x - from.width / 2;
        const startY = from.y;
        const endX = to.x + to.width / 2;
        const endY = to.y;
        const curvature = Math.abs(startX - endX) * 0.45;
        return `M ${startX} ${startY} C ${startX - curvature} ${startY}, ${endX + curvature} ${endY}, ${endX} ${endY}`;
      } else {
        // Right side connector
        const startX = from.x + from.width / 2;
        const startY = from.y;
        const endX = to.x - to.width / 2;
        const endY = to.y;
        const curvature = Math.abs(endX - startX) * 0.45;
        return `M ${startX} ${startY} C ${startX + curvature} ${startY}, ${endX - curvature} ${endY}, ${endX} ${endY}`;
      }
    }

    // Vertical spine connection (top edge to bottom edge)
    const startX = from.x;
    const startY = from.y + from.height / 2;
    const endX = to.x;
    const endY = to.y - to.height / 2;
    return `M ${startX} ${startY} L ${endX} ${endY}`;
  }

  // Determine if an edge is actively connected or completed
  function getEdgeState(edge: WorkflowEdge): { isConnected: boolean; isActive: boolean } {
    if (!isQueryActive) return { isConnected: false, isActive: false };

    // User message to Planner
    if (edge.id === "e-user-planner") {
      return { isConnected: true, isActive: activeAgent === "planner" };
    }

    // Branch filtering: only connect the branch that applies to the query
    if (edge.branch === "two_locations") {
      if (!hasRouteInTrace) return { isConnected: false, isActive: false };
      return {
        isConnected: true,
        isActive: activeAgent === "route",
      };
    }

    if (edge.branch === "no_location") {
      if (!isNoLocation) return { isConnected: false, isActive: false };
      return {
        isConnected: true,
        isActive: activeAgent === "reporting",
      };
    }

    if (edge.branch === "one_location") {
      if (hasRouteInTrace || isNoLocation) return { isConnected: false, isActive: false };
      const isConnected = executedAgents.has("geospatial") || activeAgent === "geospatial";
      return { isConnected, isActive: activeAgent === "geospatial" };
    }

    // Route to reporting
    if (edge.id === "e-route-reporting") {
      if (!hasRouteInTrace) return { isConnected: false, isActive: false };
      const isConnected = executedAgents.has("reporting") || activeAgent === "reporting";
      return { isConnected, isActive: activeAgent === "reporting" };
    }

    // Reporting to terminal
    if (edge.id === "e-reporting-terminal") {
      const isConnected =
        (trace.length > 0 && !isStreaming) || (simStep !== null && simStep >= 6);
      return { isConnected, isActive: activeAgent === "reporting" };
    }

    // Sequential agent edges
    if (edge.agentKey) {
      const isConnected =
        executedAgents.has(edge.agentKey) || (effectiveStreaming && activeAgent === edge.agentKey);
      const isActive = effectiveStreaming && activeAgent === edge.agentKey;
      return { isConnected, isActive };
    }

    return { isConnected: false, isActive: false };
  }

  function getNodeState(node: WorkflowNode): "active" | "completed" | "idle" {
    if (node.id === "user_message") {
      return isQueryActive ? "completed" : "idle";
    }
    if (node.id === "answer_trace") {
      return (trace.length > 0 && !isStreaming) || (simStep !== null && simStep >= 6)
        ? "completed"
        : "idle";
    }
    if (node.agentKey) {
      if (activeAgent === node.agentKey) return "active";
      if (executedAgents.has(node.agentKey)) return "completed";
      return "idle";
    }
    if (node.connectorName) {
      const isCited = trace.some((t) =>
        t.sources?.some((s) => s.toLowerCase().includes(node.connectorName!.toLowerCase()))
      );
      if (isCited) return "completed";

      const parentEdge = EDGES.find((e) => e.to === node.id);
      if (parentEdge?.agentKey && executedAgents.has(parentEdge.agentKey)) {
        return "completed";
      }
      if (parentEdge?.agentKey && activeAgent === parentEdge.agentKey) {
        return "active";
      }
      return "idle";
    }
    return "idle";
  }

  const selectedTraceEntry = selectedNode?.agentKey
    ? trace.find((t) => t.agent.toLowerCase() === selectedNode.agentKey)
    : null;

  return (
    <div className="relative w-full h-full bg-slate-50/70 overflow-hidden flex flex-col select-none">
      {/* Test / accessibility status without eating vertical canvas space */}
      <span className="sr-only" data-testid="graph-status">
        {effectiveStreaming ? "ACTIVE DISPATCH" : isQueryActive ? "CONVERGED" : "IDLE"}
      </span>

      {/* Main Canvas Area - fills 100% of panel height */}
      <div className="relative flex-1 w-full h-full overflow-hidden flex items-center justify-center p-2 bg-slate-50/50">
        {/* Subtle Canvas Dot Grid matching UI light theme */}
        <div
          className="absolute inset-0 pointer-events-none opacity-40"
          style={{
            backgroundImage:
              "radial-gradient(circle, #cbd5e1 1.2px, transparent 1.2px), radial-gradient(circle, #e2e8f0 1.2px, transparent 1.2px)",
            backgroundSize: "28px 28px",
            backgroundPosition: "0 0, 14px 14px",
          }}
        />

        <div
          className="w-full h-full flex items-center justify-center transition-transform duration-300 ease-out"
          style={{ transform: `scale(${zoom})` }}
        >
          <svg
            viewBox="12 25 648 785"
            className="w-full h-full object-contain overflow-visible"
            preserveAspectRatio="xMidYMid meet"
          >
            <defs>
              <filter id="glow-light" x="-30%" y="-30%" width="160%" height="160%">
                <feGaussianBlur stdDeviation="2.5" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>

            {/* ── BRANCH DECISION LABELS (From user's reference diagram, light theme) ── */}
            <g className="select-none pointer-events-none">
              {/* "one location" label on central spine */}
              <rect x="298" y="180" width="104" height="24" rx="6" fill="#ffffff" stroke="#cbd5e1" strokeWidth="1" />
              <text x="350" y="196" fill="#334155" fontSize="10.5" fontFamily="monospace" textAnchor="middle" fontWeight="bold">
                one location
              </text>

              {/* "two locations" label on right detour branch */}
              <rect x="486" y="240" width="110" height="24" rx="6" fill="#fffbeb" stroke="#fde68a" strokeWidth="1" />
              <text x="541" y="256" fill="#b45309" fontSize="10.5" fontFamily="monospace" textAnchor="middle" fontWeight="bold">
                two locations
              </text>

              {/* "no location" label on left bypass branch */}
              <rect x="20" y="390" width="100" height="24" rx="6" fill="#ffffff" stroke="#cbd5e1" strokeWidth="1" />
              <text x="70" y="406" fill="#475569" fontSize="10.5" fontFamily="monospace" textAnchor="middle" fontWeight="bold">
                no location
              </text>
            </g>

            {/* ── CONNECTING CURVES (Connected ONLY when working or finished) ── */}
            {EDGES.map((edge) => {
              const fromNode = getNodeById(edge.from);
              const toNode = getNodeById(edge.to);
              if (!fromNode || !toNode) return null;

              const { isConnected, isActive } = getEdgeState(edge);
              if (!isConnected) return null; // "connect the lines only when it is working on each thing. do not keep it connected before"

              const curvePath = getEdgePath(edge, fromNode, toNode);
              const strokeColor = isActive ? "#0284c7" : edge.color;

              return (
                <g key={edge.id} data-testid="edge-line" className="animate-in fade-in duration-300">
                  {/* Outer halo when active */}
                  {isActive && (
                    <path
                      d={curvePath}
                      fill="none"
                      stroke={strokeColor}
                      strokeWidth={5}
                      strokeOpacity={0.25}
                      filter="url(#glow-light)"
                    />
                  )}

                  {/* Main Line */}
                  <path
                    d={curvePath}
                    fill="none"
                    stroke={strokeColor}
                    strokeWidth={isActive ? 2.5 : 2}
                    strokeOpacity={isActive ? 1 : 0.9}
                    strokeDasharray={isActive ? "6, 4" : undefined}
                    className={isActive ? "animate-pulse" : ""}
                  />

                  {/* Animated traveling energy particle */}
                  {isActive && (
                    <circle r="4" fill="#0284c7" filter="url(#glow-light)">
                      <animateMotion path={curvePath} dur="1.1s" repeatCount="indefinite" />
                    </circle>
                  )}
                </g>
              );
            })}

            {/* ── NODES (Light Theme Cards with Vibrant Colored Borders) ── */}
            {NODES.map((node) => {
              const state = getNodeState(node);
              const isSelected = selectedNode?.id === node.id;
              const isIdle = state === "idle";

              let borderStyle = "border-[#10b981] shadow-[0_2px_8px_rgba(16,185,129,0.18)]";
              let dotColor = "bg-[#10b981] shadow-[0_0_6px_#10b981]";

              if (node.themeColor === "red") {
                borderStyle = "border-[#f43f5e] shadow-[0_2px_8px_rgba(244,63,94,0.18)]";
                dotColor = "bg-[#f43f5e] shadow-[0_0_6px_#f43f5e]";
              } else if (node.themeColor === "amber") {
                borderStyle = "border-[#f59e0b] shadow-[0_2px_8px_rgba(245,158,11,0.18)]";
                dotColor = "bg-[#f59e0b] shadow-[0_0_6px_#f59e0b]";
              }

              const activeRing =
                state === "active"
                  ? "ring-2 ring-sky-400 border-sky-500 shadow-[0_0_14px_rgba(2,132,199,0.35)]"
                  : "";

              return (
                <foreignObject
                  key={node.id}
                  x={node.x - node.width / 2}
                  y={node.y - node.height / 2}
                  width={node.width}
                  height={node.height}
                  className="overflow-visible"
                >
                  <button
                    type="button"
                    onClick={() => setSelectedNode(node)}
                    className={`group w-full h-full flex items-center justify-between px-2.5 py-1 rounded-xl transition-all duration-300 cursor-pointer text-left bg-white/95 backdrop-blur-md border ${borderStyle} ${activeRing} ${
                      isIdle ? "opacity-90" : "opacity-100"
                    } ${isSelected ? "ring-2 ring-slate-800 scale-105" : "hover:scale-[1.02] hover:shadow-md"}`}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      {/* Left icon tile */}
                      <span className="w-7 h-7 rounded-lg bg-slate-100 border border-slate-200/90 flex items-center justify-center text-xs shrink-0 shadow-2xs">
                        {renderNodeIcon(node.id)}
                      </span>
                      <div className="min-w-0">
                        <div className="text-[12.5px] font-bold text-slate-900 truncate leading-tight tracking-tight">
                          {node.label}
                        </div>
                        <div className="text-[10px] font-mono text-slate-500 truncate leading-tight mt-0.5">
                          {state === "active" ? "Processing..." : node.sublabel}
                        </div>
                      </div>
                    </div>

                    {/* Right status dot */}
                    <div className="shrink-0 pl-1.5 flex items-center">
                      {state === "active" ? (
                        <span className="w-2 h-2 rounded-full bg-sky-500 animate-ping shadow-[0_0_8px_#0284c7]" />
                      ) : (
                        <span className={`w-2 h-2 rounded-full ${dotColor}`} />
                      )}
                    </div>
                  </button>
                </foreignObject>
              );
            })}
          </svg>
        </div>

        {/* ── BOTTOM-LEFT CONTROLS (Light Theme with Lucide icons) ── */}
        <div className="absolute bottom-3 left-3 z-30 flex flex-col gap-0.5 bg-white/95 backdrop-blur-md p-1 rounded-xl border border-slate-200 shadow-md">
          <button
            type="button"
            onClick={() => setZoom((z) => Math.min(z + 0.15, 1.6))}
            title="Zoom in"
            className="w-7 h-7 flex items-center justify-center text-slate-700 hover:text-black hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => setZoom((z) => Math.max(z - 0.15, 0.7))}
            title="Zoom out"
            className="w-7 h-7 flex items-center justify-center text-slate-700 hover:text-black hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
          >
            <Minus className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => setZoom(1)}
            title="Fit to view"
            className="w-7 h-7 flex items-center justify-center text-slate-500 hover:text-black hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Selected Node Details Drawer (Light Theme) */}
        {selectedNode && (
          <div className="absolute bottom-3 right-3 z-30 w-72 max-w-[calc(100%-2rem)] bg-white/95 backdrop-blur-xl border border-slate-200 p-3.5 rounded-2xl shadow-xl animate-in fade-in slide-in-from-bottom-2 duration-200 text-slate-800">
            <div className="flex items-center justify-between pb-1.5 border-b border-slate-100 mb-2">
              <div className="flex items-center gap-1.5">
                <span>{renderNodeIcon(selectedNode.id)}</span>
                <span className="text-xs font-bold text-slate-900">{selectedNode.label}</span>
              </div>
              <button
                type="button"
                onClick={() => setSelectedNode(null)}
                className="text-slate-400 hover:text-slate-700 text-xs p-1 rounded hover:bg-slate-100 cursor-pointer"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="space-y-1.5 text-xs text-slate-600">
              <div className="text-[11px] font-medium text-slate-700">
                {selectedNode.sublabel}
              </div>

              {selectedTraceEntry ? (
                <>
                  <div className="flex items-center justify-between text-[10px] pt-1">
                    <span className="text-slate-500">Execution Status:</span>
                    <span className="font-mono text-emerald-700 font-bold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                      COMPLETED
                    </span>
                  </div>
                  {selectedTraceEntry.sources && selectedTraceEntry.sources.length > 0 && (
                    <div className="pt-1">
                      <span className="text-[10px] text-slate-500">Data Sources Consulted:</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {selectedTraceEntry.sources.map((s, idx) => (
                          <span
                            key={idx}
                            className="px-1.5 py-0.5 rounded bg-slate-100 text-[10px] font-mono text-slate-700 border border-slate-200"
                          >
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {selectedTraceEntry.is_cached && (
                    <div className="text-[10px] text-amber-800 bg-amber-50 border border-amber-200 p-1.5 rounded-lg mt-1">
                      Cached snapshot fallback served.
                    </div>
                  )}
                </>
              ) : (
                <div className="text-[10px] text-slate-500 leading-normal pt-1">
                  Node in ORCA multi-agent LangGraph workflow.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
