<div align="center">

# 🌊 ORCA — Marine Ecosystem Reasoning with Collaborative Agents

**Autonomous Multi-Agent Intelligence & Real-Time Ocean Telemetry Platform**

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%20%7C%20LangGraph-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2016%20%7C%20Tailwind%20v4-black?style=flat-square&logo=next.js)](https://nextjs.org)
[![Python](https://img.shields.io/badge/Python-3.12+-blue?style=flat-square&logo=python)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-blue?style=flat-square&logo=typescript)](https://www.typescriptlang.org/)
[![Tests Passing](https://img.shields.io/badge/Tests-196%20Backend%20%7C%2056%20Frontend%20Passing-success?style=flat-square)](https://github.com/kishore1035/ORCA)
[![SIH Problem](https://img.shields.io/badge/Smart%20India%20Hackathon-SIH26176-orange?style=flat-square)](https://www.sih.gov.in/)

</div>

---

## 📌 Executive Overview

**ORCA** is an agentic marine intelligence platform engineered for fishermen, coastal communities, maritime operators, and ocean researchers. Traditional marine safety apps provide disjointed forecasts or raw meteorological numbers that require nautical expertise to decipher. 

ORCA solves this by orchestrating a **specialist multi-agent directed acyclic graph (DAG)** powered by **LangGraph**. When a user asks an advisory question — such as *"Can I fish near Mangaluru tomorrow at 6 AM?"* or *"What's the safest route from Kochi to Alappuzha?"* — ORCA decomposes the query, fetches real-time telemetry from Indian and international maritime institutes (**INCOIS**, **IMD**, **NOAA**, **ISRO**, **GDACS**, **Blitzortung**), verifies coastal constraints, calculates composite safety and hazard risks, and synthesizes a grounded advisory accompanied by an animated live workflow trace and geospatial map.

---

## ✨ Key Features & Capabilities

- 🤖 **Transparent Multi-Agent Reasoning**: Every response displays an interactive reasoning trace detailing which agents executed, telemetry sources queried, latency, and whether data was live or cached.
- 📈 **Animated Workflow Graph**: An SVG-powered DAG visualization that pulses and connects in real time as each specialist agent activates during query execution.
- 🎯 **Grounding & Evidence Panel**: Auditable metrics with verification badges citing wave heights, swell periods, wind speeds, sea surface temperature (SST), and chlorophyll-a concentrations.
- 🗺️ **Interactive Geospatial Intelligence**: Leaflet-powered maps rendering coastal sectors, bathymetry lines, hazard warning zones, and multi-waypoint transit safety corridors.
- ⏱️ **What-If Time Analysis**: Comparative departure window evaluations comparing current conditions against delayed departures (e.g., +3h, +6h) to find safer navigation windows.
- 🌊 **PFZ (Potential Fishing Zone) Diagnostics**: Correlates SST gradients and chlorophyll concentrations with INCOIS advisory boundaries.
- ⚡ **Proactive Hazard Alerting & Push Notifications**: Real-time SSE channel polling for cyclone advisories, high-wave alerts, and lightning strikes, with optional Web Push notifications.
- 🎨 **Apple HIG-Inspired Fluid Interface**: Sleek dark and light UI built with Tailwind CSS v4, dynamic spring-physics AI prompt inputs, and zero UI clutter.

---

## 🏗️ System Architecture

```
                                      ┌──────────────────────────────────────────────────────────┐
                                      │                    ORCA NEXT.JS CLIENT                   │
                                      │  - Fluid 3-Panel Layout (Chat, Workflow Graph, Map)      │
                                      │  - Animated SVG Pipeline Graph                           │
                                      │  - Spring Physics Prompt Input                           │
                                      └────────────────────────────┬─────────────────────────────┘
                                                                   │ Server-Sent Events (SSE)
                                                                   ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    FASTAPI LANGGRAPH BACKEND                                   │
│                                                                                                │
│   ┌──────────────┐         ┌──────────────┐         ┌──────────────┐         ┌─────────────┐   │
│   │   PLANNER    │ ──────► │  GEOSPATIAL  │ ──────► │   WEATHER    │ ──────► │ RISK ENGINE │   │
│   │ Intent & DAG │         │ Nominatim/   │         │ Open-Meteo & │         │ Composite   │   │
│   │ Formulation  │         │ Overpass OSM │         │ IMD Feeds    │         │ Safety (100)│   │
│   └──────┬───────┘         └──────────────┘         └──────────────┘         └──────┬──────┘   │
│          │                                                                          │          │
│          │ (Route Request)                                                          ▼          │
│          ▼                                                                   ┌─────────────┐   │
│   ┌──────────────┐                                                           │    OCEAN    │   │
│   │ ROUTE AGENT  │                                                           │  ANALYTICS  │   │
│   │ 5-Waypoint   │                                                           │ NOAA ERDDAP │   │
│   │ Hazard Scan  │                                                           │ SST / Chl-a │   │
│   └──────┬───────┘                                                           └──────┬──────┘   │
│          │                                                                          │          │
│          └───────────────────────────────────┬──────────────────────────────────────┘          │
│                                              ▼                                                 │
│                                    ┌───────────────────┐                                       │
│                                    │  REPORTING AGENT  │                                       │
│                                    │ Evidence Synthesis│ ──► Client Stream                     │
│                                    │ & Safety Advisory │                                       │
│                                    └───────────────────┘                                       │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📡 Grounded Data Connectors

ORCA enforces a strict **Zero-Fabrication Contract**. Every external connector implements standard schema caching and fallback behavior: `{data, source, fetched_at, is_cached}`. If upstream feeds encounter timeouts, verified local snapshots are served with transparent citation.

| Telemetry Domain | Primary Live Feed | Fallback Snapshot | Authentication |
|---|---|---|---|
| **Waves & Wind** | [Open-Meteo Marine API](https://open-meteo.com) | Committed historical cache | Free / No Key |
| **SST & Chlorophyll** | NOAA ERDDAP (`jplMURSST41`, `erdMH1chla1day`) | ISRO / INCOIS coastal baseline | Free / No Key |
| **Cyclone Tracking** | Global Disaster Alert and Coordination System ([GDACS](https://www.gdacs.org)) | Regional cyclone archive | Free / No Key |
| **Lightning Real-Time** | Blitzortung Public MQTT Bridge | Real-time 5s strike buffer | Free / No Key |
| **Geocoding & Harbours** | OpenStreetMap Nominatim | Indian coastal landing centres | Free / No Key |
| **Marine Protected Areas** | OpenStreetMap Overpass API | Wildlife sanctuary geofences | Free / No Key |

---

## 🚀 Quickstart Guide

### Prerequisites

- **Python**: `3.12+` (with `uv` recommended)
- **Node.js**: `18+` or `20+` (with `npm`)
- **LLM API Key**: Free [Ollama Cloud](https://ollama.com) API Key or OpenAI-compatible endpoint

### 1. Clone the Repository

```bash
git clone https://github.com/kishore1035/ORCA.git
cd ORCA
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate    # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt

# Configure environment variables
cp .env.example .env        # Or create .env with OLLAMA_API_KEY

# Start backend server
uv run uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd ../frontend

# Install packages
npm install

# Start Next.js development server
npm run dev
```

Visit [`http://localhost:3000`](http://localhost:3000) in your browser.

---

## 🧪 Testing & Verification

ORCA is engineered with high test coverage across both backend multi-agent flows and frontend user interface components.

```bash
# Run Python backend test suite (196 tests)
cd backend
uv run pytest -v

# Run Frontend test suite (56 tests)
cd frontend
npm test

# Verify TypeScript compilation
npm run build
```

---

## 📂 Project Structure

```
ORCA/
├── backend/
│   ├── app/
│   │   ├── agents/          # LangGraph agents (planner, geospatial, weather, risk, ocean, route, reporting)
│   │   ├── connectors/      # Resilient external data sources (Open-Meteo, NOAA, GDACS, Blitzortung, OSM)
│   │   ├── alerting.py      # Background hazard evaluator & SSE push
│   │   ├── auth.py          # Session security & JWT handling
│   │   ├── config.py        # Pydantic v2 application configuration
│   │   ├── db.py            # SQLite schema & persistent conversation storage
│   │   ├── graph.py         # Multi-agent LangGraph orchestration graph
│   │   ├── llm.py           # Multi-provider LLM client with intelligent fallback
│   │   └── main.py          # FastAPI endpoints (/chat, /auth, /sessions, /alerts)
│   ├── data/snapshots/      # Committed fallback data snapshots
│   └── tests/               # 196 unit & integration tests
│
├── frontend/
│   ├── app/                 # Next.js App Router (/page.tsx, /demo/page.tsx, globals.css)
│   ├── components/
│   │   ├── ui/              # ai-chat-input.tsx (Cubic-bezier animated spring input)
│   │   ├── AgentWorkflowPanel.tsx  # Dynamic workflow side panel
│   │   ├── WorkflowGraph.tsx       # Live animated SVG multi-agent DAG
│   │   ├── ChatPanel.tsx           # Advisory conversation & quick prompts
│   │   ├── EvidencePanel.tsx       # Grounding metrics & telemetry citations
│   │   ├── MapView.tsx             # Interactive Leaflet map with route markers
│   │   ├── MarkdownContent.tsx     # Formatted advisory report renderer
│   │   ├── RecommendationHero.tsx  # Top-level GO / CAUTION / NO-GO banner
│   │   ├── SstTrendChart.tsx       # 7-day sea surface temperature trend visualization
│   │   └── WhatIfCard.tsx          # Temporal departure comparison analysis
│   └── lib/                 # chatClient.ts (SSE consumer), push.ts, types.ts
│
├── .vscode/                 # Preconfigured IDE CSS linting rules for Tailwind v4
└── README.md                # Platform documentation
```

---

## 💡 Example Queries to Try

- 🎣 **Fishing Feasibility**: *"Can I go fishing near Mangaluru tomorrow at 6 AM?"*
- ⏰ **Departure Comparison**: *"What if I leave at 11 AM instead?"*
- 🧭 **Potential Fishing Zones**: *"Where is the nearest fishing zone near Kochi?"*
- ⚡ **Marine Hazard Inspection**: *"Any cyclone or lightning alerts near Veraval Port?"*
- 🗺️ **Transit Safety Scan**: *"Is the sea route safe between Chennai and Visakhapatnam?"*

---

## 🏆 Hackathon Submission

Developed for **Smart India Hackathon 2024** — Problem Statement **SIH26176**: *Intelligent Multi-Agent System for Coastal Fisheries and Ocean Safety Advisory*.

---

<div align="center">
  <sub>Built with ❤️ by the ORCA Engineering Team</sub>
</div>
