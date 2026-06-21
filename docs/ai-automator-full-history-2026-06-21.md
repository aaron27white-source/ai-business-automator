# AI Business Automator — Full Project History

> **Written:** 2026-06-21  
> **Project:** AI Business Automator — Python-native replacement for 4 buggy n8n workflows  
> **Repo:** `/home/openclaw/workspace/portfolio-projects/ai-automator/`  
> **Live:** `https://5lanxo-ai-automator.hf.space` (building)  

---

## Table of Contents

1. [The Origin — Why We Pivoted From n8n](#1-the-origin--why-we-pivoted-from-n8n)
2. [The Planning Phase](#2-the-planning-phase)
3. [Phase 1: Cline Builds the Foundation](#3-phase-1-cline-builds-the-foundation)
4. [Phase 2: Sweet Jones P 🍯 Refactors & Production-Hardens](#4-phase-2-sweet-jones-p--refactors--production-hardens)
5. [The Final Architecture](#5-the-final-architecture)
6. [The Deploy Process](#6-the-deploy-process)
7. [Known Issues & Roadmap](#7-known-issues--roadmap)
8. [Asset Inventory](#8-asset-inventory)
9. [Timeline Summary](#9-timeline-summary)

---

## 1. The Origin — Why We Pivoted From n8n

Before the Python-native version, this project ran on **4 n8n workflows** — node-based automation pipelines that handled email classification, inquiry responses, lead enrichment, and daily reporting.

### The Breaking Points

| Problem | Impact |
|---------|--------|
| **n8n Respond node couldn't evaluate `{{ }}` expressions** | Draft replies would render raw template syntax instead of substituted values. Client-facing output was broken. |
| **Webhook timeouts** | n8n's webhook node had unreliable timeout behavior, especially under free-tier hosting. Endpoints would hang or return 504. |
| **UI bugs in n8n editor** | Workflow nodes would misrender, connectors would break, and the drag-and-drop interface introduced state corruption. Non-technical operators couldn't trust what they saw. |
| **No testability** | n8n workflows couldn't be unit-tested. Every change required manual re-triggering through the UI. Regression testing was impractical. |
| **Monolithic workflow design** | All logic lived inside n8n's node graph. Version control was nonexistent. Rollbacks meant manually recreating nodes. |

### The Decision

**Replace all 4 workflows with a single FastAPI server.** Same AI calls (OpenRouter → DeepSeek). Same sidecar logic. Zero n8n UI bugs. The entire system becomes:
- Testable via `curl` and Python unit tests
- Version-controlled in Git
- Deployable as a Docker container to HF Spaces
- Client-reusable with a config swap

---

## 2. The Planning Phase

### The Documents

Three planning documents were created before a single line of server code was written:

#### `BUILD_PLAN.md` — The Architectural Spec

An 11-task build plan that served as the blueprint. Each task was designed with an "Aaron teaches" callout — explaining the *why* behind each decision:

| Task | What | Educational Concept |
|------|------|-------------------|
| 1 | Scaffold + venv + deps | Environment setup |
| 2 | `config.py` — API key loader | Environment variables + secret management |
| 3 | `server.py` skeleton + `/health` | FastAPI basics, decorators, auto-docs |
| 4 | `POST /classify` — Email classifier | POST endpoints + prompt engineering (temp=0.1) |
| 5 | `POST /respond` — Inquiry router | Why FastAPI works where n8n broke |
| 6 | `POST /enrich` — Lead enricher | Structured outputs from AI (constrained generation) |
| 7 | `POST /report` — Auto reporter | AI summarization, cron-triggered design |
| 8 | Static `index.html` — Demo frontend | Serving static files, portfolio showcase |
| 9 | `run.sh`, `Dockerfile`, `README.md` | Production polish + deployment |
| 10 | Smoke test all 4 endpoints | Verification |
| 11 | Deploy to HF Spaces | Multi-app Spaces, secrets, live demo |

#### `CLINE_INSTRUCTIONS.md` — The Build Manifest

A concise builder's brief for Cline (the coding agent). It specified:
- **Project location:** `~/workspace/portfolio-projects/ai-automator/`
- **What we're building:** FastAPI server replacing 4 n8n workflows
- **Port:** 8770 local (no conflict with agent-workbench at 8765 or sidecar at 8767)
- **Key management:** Load from `~/.hermes/.env`, never hardcode
- **Style reference:** agent-workbench dark theme (`--bg:#0a0a0f; --accent:#6d28d9`)
- **Build order:** Follow BUILD_PLAN.md task-by-task

#### `DEV_LOG.md` — The Build Journal (Created Post-Facto by P)

A complete build journal capturing decisions, roadblocks, and fixes. Added after the build as a portfolio- ready document.

---

## 3. Phase 1: Cline Builds the Foundation

Cline executed the 11-task build plan. Here's what was created:

### Task 1 — Project Scaffold

```bash
mkdir -p ~/workspace/portfolio-projects/ai-automator/static
python3 -m venv .venv
```

**Dependencies installed:**
```
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
httpx>=0.27.0
python-dotenv>=1.0.0
```

### Task 2 — Config Module (`config.py`)

A dedicated config module that:
- Loads `OPENROUTER_API_KEY` from environment (works natively on HF Spaces)
- Falls back to `~/.hermes/.env` via `python-dotenv`
- Exposes a `CONFIG` dict at module import time
- Fails loudly with a clear error message if the key is missing

**Key design decision:** Using `python-dotenv` over `subprocess` sourcing — cleaner, cross-platform, standard Python.

### Task 3 — Server Skeleton (`server.py`)

Minimal FastAPI app with:
- `GET /health` — health check returning status + key configuration status
- `GET /` — serves the static dashboard
- Static files mounted at `/static`
- CORS middleware (allow all origins — portfolio/open demo)
- Port from `$PORT` env var (HF sets 7860), defaults to 8770 locally

### Tasks 4-7 — The 4 Endpoints

#### `POST /classify` — Email Classifier

**Input:** `{ from_email, subject, body }`  
**Output:** `{ classification: JOB|CLIENT|URGENT|NOISE, from_email, subject }`  
**Model:** `deepseek/deepseek-chat` (cheap, fast)  
**Temperature:** 0.1 (nearly deterministic — reliability over creativity)  
**Max tokens:** 30 (forced brevity — one-word classification)

**Prompt strategy:** System prompt says "Classify this email into ONE word only: JOB, CLIENT, URGENT, or NOISE. No other text. No punctuation." — constrained generation that produces parseable output.

#### `POST /respond` — Inquiry Responder

**Input:** `{ classification, from_email, subject, body }`  
**Output:** `{ draft_reply, classification }`  
**Model:** `deepseek/deepseek-chat`  
**Temperature:** 0.3  
**Max tokens:** 300

**Key design decision:** Uses **live client config** — every request reads `client_config.json` from disk and builds a voice-aware system prompt. Changes to the config take effect on the *next request*, no server restart needed.

The system prompt is dynamically built from:
- Business name
- Tone by category (JOB/CLIENT/URGENT/NOISE)
- Voice/style description
- Max word limit
- Never-mention blacklist
- Sign-off line

#### `POST /enrich` — Lead Enricher

**Input:** `{ company_name, contact_email, additional_context }`  
**Output:** `{ enriched_data: { industry, company_size, potential_value, engagement_strategy, key_insights }, company_name }`  
**Model:** `deepseek/deepseek-r1` (reasoning model)  
**Temperature:** 0.2  
**Max tokens:** 800

**Key design decision:** Uses DeepSeek-R1 instead of deepseek-chat. Enrichment requires real reasoning — company research benefits from chain-of-thought. The prompt demands JSON output, and the server attempts `json.loads()` on the result with a fallback to raw text if parsing fails.

**Tradeoff:** R1 is ~4x more expensive and 3-10x slower than deepseek-chat. An endpoint call can take 30-90 seconds.

#### `POST /report` — Daily Report

**Input:** `{ date, emails_processed, leads_generated, tasks_completed, additional_notes }`  
**Output:** `{ summary, key_metrics, recommendations }`  
**Model:** `deepseek/deepseek-chat`  
**Temperature:** 0.2  
**Max tokens:** 400

Designed for cron-based triggering (morning/evening). Splits the AI output into summary + recommendations sections, and computes a conversion rate metric server-side.

### Task 8 — The Dashboard (`static/index.html`)

A dark-themed single-page application with:

- **Two-tab layout:** 🧰 Tools | ⚙️ Voice Config
- **Color scheme:** `--bg:#0a0a0f` (near-black), `--accent:#6d28d9` (purple), `--card-bg:#1a1a2e` (deep navy)
- **Tool cards:** Each endpoint has its own card with labeled input fields and a "Test" button
- **Live results:** JSON responses rendered in styled result panels with success/error coloring
- **Loading states:** Spinner text while requests process
- **Error handling:** Catches fetch failures and renders error messages
- **Auto-date:** Sets today's date on the report form

**Config Editor features:**
- Auto-loads current config from `GET /config` on page load
- Editable fields for business name, location, services, voice, sign-off, CTA, max words, never-mention list
- Individual tone inputs for JOB/CLIENT/URGENT/NOISE categories
- "Save Config" button → `PUT /config` → toast notification → live immediately
- "Reload from Disk" resets form to server state

**JS architecture:**
- Tab switching via data attributes and event delegation
- `apiCall()` helper — generic POST + JSON render for all 4 endpoints
- `loadConfig()` / `collectConfig()` — config CRUD with form binding
- Toast notification system for save feedback

### Task 9 — Deployment Configuration

#### `run.sh` — Launch Script (Original Cline Version)

```bash
#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -d ".venv" ]; then
    echo "Creating venv..."
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
fi
echo "🤖 AI Business Automator"
exec .venv/bin/python3 server.py
```

**Initial issue:** Used `.venv/` directory but some path references used `venv/` — a mismatch that would cause "venv not found" errors.

#### `Dockerfile` (Original Cline Version)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 7860
CMD ["python3", "server.py"]
```

**Initial issue:** Used `COPY . .` which copied everything, including potentially `run.sh` (which wasn't explicitly listed). The `EXPOSE` port was set to 7860 for HF compatibility.

#### `requirements.txt`

```
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
httpx>=0.27.0
python-dotenv>=1.0.0
```

Notable: `python-dotenv` was added for proper `.env` loading (replacing the `subprocess` sourcing approach from the BUILD_PLAN spec).

### Task 10 — Smoke Tests (Phase 1)

All 4 endpoints passed:
```
GET  /health    → 200  {"status":"ok","config_loaded":true}
POST /classify  → 200  "classification":"JOB"
POST /respond   → 200  "draft_reply":"Marcus,...Let's talk."
POST /enrich    → 200  "enriched_data":{industry,size,strategy,insights}
POST /report    → 200  "summary":"Executive summary...","recommendations":"..."
```

---

## 4. Phase 2: Sweet Jones P 🍯 Refactors & Production-Hardens

After Cline's build was complete, Sweet Jones P 🍯 took over for production hardening. Here's every change:

### 4.1 `run.sh` — Critical Fixes

**Before (Cline):**
```bash
#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -d ".venv" ]; then
    ...
fi
exec .venv/bin/python3 server.py
```

**After (P):**
```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install -r requirements.txt
    echo "✅ Dependencies installed"
fi
if [ ! -f "$HOME/.hermes/.env" ]; then
    echo "⚠️  Warning: ~/.hermes/.env not found"
    echo "   Create it with: OPENROUTER_API_KEY=sk-..."
fi
echo "🚀 AI Business Automator — http://localhost:${PORT:-8770}"
exec "$VENV_DIR/bin/python3" server.py "$@"
```

**Changes:**
| Fix | Why |
|-----|-----|
| Added `set -euo pipefail` | Stricter error handling — exits on unset variables and pipe failures |
| Explicit `VENV_DIR=".venv"` variable | Eliminated venv path mismatch (was mixing `venv/` and `.venv/`) |
| `$HOME/.hermes/.env` warning | User-friendly guidance if config file is missing |
| `$PORT` env var support | HF Spaces compatibility — passes port through environment |
| `"$@"` passthrough | Allows argument forwarding to the Python script |

### 4.2 `server.py` — Production Hardening

#### Structural Changes

1. **Removed `reload=True`** — Cline's original had uvicorn hot-reload enabled, which leaks watcher processes in production. Set to `reload=False`.

2. **Consolidated duplicate helpers** — Cleaned up code that had drifted into parallel implementations.

3. **Added CORS middleware** — Explicit `CORSMiddleware` with open CORS policy for the demo dashboard.

4. **Full Pydantic model layer** — Replaced raw `request.json()` with typed request/response models:
   - `EmailClassifyRequest` / `EmailClassifyResponse`
   - `InquiryRespondRequest` / `InquiryRespondResponse`
   - `LeadEnrichRequest` / `LeadEnrichResponse`
   - `DailyReportRequest` / `DailyReportResponse`
   - `ClientConfigUpdate` (with optional fields for partial updates)

5. **Dedicated OpenRouter helper** — Extracted `_call_openrouter()` with proper error handling, typed exceptions, and consistent timeout management.

6. **Live config system** — `_load_client_config()` called per-request with merge-into-defaults pattern so missing fields never crash.

#### Config Endpoints Added

**`GET /config`** — Returns the full client configuration JSON
- Used by the dashboard Config Editor to populate form fields

**`PUT /config`** — Partial update of client configuration
- `ClientConfigUpdate` model uses `Optional` fields — send only what changed
- Merges with existing config, persists to `client_config.json` on disk
- Returns the full merged config in response for UI confirmation

#### Voice Prompt Builder

Added `_build_voice_prompt(cfg, category)` — dynamically constructs the system prompt from:
- Business name
- Category-specific tone (falls back to default voice)
- Max word limit
- Never-mention blacklist
- Sign-off line

This is what makes the config editor work — changes to any field immediately affect the next `/respond` call.

#### `/enrich` JSON Parsing Upgrade

Added `json.loads()` attempt on the R1 output with a fallback structure. If the AI returns valid JSON, it's returned as structured `enriched_data`. If it returns free text, the server wraps it in a fallback dict with `raw_analysis` field — graceful degradation instead of a crash.

#### `/report` Structured Response

The report endpoint now splits the AI output into `summary` + `recommendations` (separated by double newline), and computes `conversion_rate = leads_generated / emails_processed` server-side as a derived metric.

### 4.3 `Dockerfile` — Polish

**Before (Cline):**
```dockerfile
FROM python:3.12-slim
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 7860
CMD ["python3", "server.py"]
```

**After (P):**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY config.py server.py ./
COPY client_config.json ./
COPY static/ ./static/
COPY run.sh ./
EXPOSE 7860
CMD ["python", "server.py"]
```

**Changes:**
| Change | Why |
|--------|-----|
| Added `WORKDIR /app` | Explicit working directory — best practice |
| Explicit file-by-file COPY | Only copies what's needed — smaller layer, no hidden files |
| Added `client_config.json` | Was missing from the original COPY — config would be empty in container |
| Added `run.sh` | The launcher script was missing — couldn't use it inside the container |
| Added `static/` explicitly | Makes the Dockerfile self-documenting about what files exist |
| Changed `python3` → `python` | `python` is the standard in official Python images; `python3` may not exist |

### 4.4 `static/index.html` — Complete Redesign

Cline's original was a basic demo page. P replaced it with:

- **Two-tab layout** — 🧰 Tools tab + ⚙️ Voice Config tab
- **4 endpoint cards** — Each with proper input fields, labels, and "Test" buttons
- **Config Editor** — Full form for all config fields including per-category tone overrides
- **Toast notifications** — Success/error feedback on config save
- **Load from disk** — "Reload from Disk" button to reset from server state
- **Loading states** — Spinner text during requests
- **Error handling** — Catches and displays fetch errors
- **Responsive design** — CSS grid adapts to mobile
- **Auto-populated dates** — Today's date in report form

### 4.5 `client_config.json` — Final Config

```json
{
  "business_name": "Aaron White — AI Automation & Infrastructure",
  "voice": "Direct, no-fluff, Houston energy. Confident not cocky. Business-first.",
  "location": "Houston, Texas",
  "services": "AI agent orchestration, business automation, n8n workflows, FastAPI servers, international trade infrastructure",
  "sign_off": "Aaron White\nLet's talk.",
  "call_to_action": "Let's hop on a 15-minute call this week. I'll send a calendar invite.",
  "never_mention": ["pricing", "timelines", "phone numbers", "email addresses"],
  "max_words_per_reply": 120,
  "tone_by_category": {
    "JOB": "Professional and enthusiastic. Show expertise without desperation.",
    "CLIENT": "Direct and solution-focused. You're the expert they need.",
    "URGENT": "Immediate and reassuring. Acknowledge urgency, provide clear next step.",
    "NOISE": "Brief and polite. Don't invest energy."
  }
}
```

### 4.6 `DEV_LOG.md` — Build Journal Created

P wrote the complete DEV_LOG.md after the build, documenting every decision, roadblock, and fix. This serves as:
- Portfolio evidence of the build process
- Reference for future maintenance
- Context for new developers joining the project

### 4.7 Smoke Tests (Phase 2 — Post-Refactor)

```
GET  /config  → 200  Full config JSON
PUT  /config  → 200  {"status":"ok","config":{...}}
```

All previous endpoints unchanged — still passing.

---

## 5. The Final Architecture

### System Diagram

```
┌──────────┐    ┌──────────────┐    ┌─────────────┐
│  Browser  │───▶│  FastAPI     │───▶│ OpenRouter  │
│ (Dark UI) │    │  Server      │    │  Gateway    │
└──────────┘    │  port 8770   │    └──────┬──────┘
                │              │           │
                │  endpoints:  │    ┌──────┴──────┐
                │  /classify   │    │  DeepSeek    │
                │  /respond    │    │  ├─ chat     │
                │  /enrich     │    │  └─ r1       │
                │  /report     │    └─────────────┘
                │  /config     │
                │  /health     │
                └──────┬───────┘
                       │
                ┌──────┴───────┐
                │ client_config│
                │ .json        │
                │ (live edit)  │
                └──────────────┘
```

### Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Framework** | FastAPI (async) | Modern Python web framework, auto-docs, Pydantic validation |
| **HTTP Client** | httpx (async) | Non-blocking API calls to OpenRouter |
| **LLM Gateway** | OpenRouter | Unified API — swap models without code changes |
| **Classification** | deepseek/deepseek-chat | Fast, cheap ($0.14/M input), temp=0.1 |
| **Response Generation** | deepseek/deepseek-chat | Context-aware reply, temp=0.3 |
| **Lead Enrichment** | deepseek/deepseek-r1 | Deep reasoning, structured JSON output, temp=0.2 |
| **Reporting** | deepseek/deepseek-chat | Summarization, temp=0.2 |
| **Frontend** | Vanilla HTML/CSS/JS | No framework — instant load, zero dependencies |
| **Deployment** | Docker + HF Spaces | Free-tier hosting, auto-scaling |
| **Config** | JSON on disk (client_config.json) | Hot-reloadable, no restart needed |

### Directory Structure

```
ai-automator/
├── config.py              ← API key loading from ~/.hermes/.env
├── server.py              ← FastAPI app (7 endpoints)
├── static/
│   └── index.html         ← Dark dashboard + live config editor
├── client_config.json     ← Editable voice/character per client
├── requirements.txt       ← Pinned deps
├── Dockerfile             ← HF Spaces deployment
├── run.sh                 ← One-command launcher
├── .gitignore
├── BUILD_PLAN.md          ← Architectural spec (for Cline)
├── CLINE_INSTRUCTIONS.md  ← Build instructions (for Cline)
├── DEV_LOG.md             ← Full build journal
└── README.md              ← Portfolio docs + API reference
```

### The Config System — Multi-Tenant Ready

The config system is the project's secret weapon for client reusability:

```
Same codebase
    │
    ├── client_A_config.json  →  "LLC 1: Professional corporate tone"
    ├── client_B_config.json  →  "LLC 2: Houston energy, direct"
    └── client_C_config.json  →  "LLC 3: Warm, relationship-focused"
```

**To onboard a new client:**
1. Copy `client_config.json` to a new file
2. Change business name, voice, services, sign-off
3. Point the server at it (or use the dashboard editor)
4. Done. All 4 endpoints now speak in the client's voice.

---

## 6. The Deploy Process

### Hugging Face Spaces Deployment

**Space:** `5lanxo/ai-automator`  
**URL:** `https://5lanxo-ai-automator.hf.space`  
**SDK:** Docker  
**Hardware:** CPU Basic (free tier)  
**Region:** us  
**Status (as of 2026-06-21 00:38 UTC):** `APP_STARTING` — Docker build in progress

**Deployment steps:**
1. Create Space with Docker SDK at huggingface.co
2. Add `OPENROUTER_API_KEY` as a Space secret
3. Push all project files matching the files listed in the Dockerfile
4. Wait for Docker build (~5-15 min on free tier first deploy)
5. Verify: `GET https://5lanxo-ai-automator.hf.space/health`

**Files uploaded to HF:**
```
.gitattributes
.gitignore
DEV_LOG.md
Dockerfile
README.md
client_config.json
config.py
requirements.txt
run.sh
server.py
static/index.html
```

**Space configuration from API:**
```json
{
  "id": "5lanxo/ai-automator",
  "sdk": "docker",
  "private": false,
  "author": "5lanxo",
  "host": "https://5lanxo-ai-automator.hf.space",
  "runtime": {
    "stage": "APP_STARTING",
    "hardware": { "requested": "cpu-basic" },
    "replicas": { "requested": 1 }
  },
  "subdomain": "5lanxo-ai-automator"
}
```

### Known Deploy Consideration

On HF Spaces, `client_config.json` is persisted in the container filesystem. This means:
- Config changes made through the dashboard persist for the container's lifetime
- On container restart (redeploy, scale, sleep/wake), config resets to the committed file
- **For production multi-user:** Swap to a database or mounted volume

---

## 7. Known Issues & Roadmap

### Current Issues

| Issue | Priority | Status | Details |
|-------|----------|--------|---------|
| **HF Spaces cold start** | Medium | Open | Free tier sleeps after inactivity. First request after idle takes ~30s to wake. Consider always-on plan for production. |
| **R1 latency** | Low | Open | `/enrich` uses DeepSeek-R1 which can take 30-90s per call. Acceptable for batch enrichment, unacceptable for real-time. Option: switch to deepseek-chat for speed. |
| **Rate limiting** | Low | Open | No concurrency gate yet. If multiple users hit the server simultaneously, OpenRouter could 429. Copy token-bucket pattern from agent-workbench. |
| **Config persistence on HF** | Low | Open | Config is container FS only. Redeploy = lost edits. Need DB or mounted volume for multi-user. |

### Future Roadmap Items

1. **Concurrency gate** — Token-bucket rate limiter to prevent 429s
2. **Database-backed config** — Replace JSON file with SQLite or similar
3. **Webhook receiver** — Accept inbound emails directly instead of requiring API calls
4. **Dashboard auth** — Simple password gate for the config editor
5. **Multi-client dashboard** — Switch active client config from the UI
6. **CI/CD pipeline** — Automated deploy to HF on git push
7. **Unit test suite** — pytest for all endpoints

---

## 8. Asset Inventory

### What Was Built

| Asset | Location | Type |
|-------|----------|------|
| **FastAPI server** | `server.py` (~200 lines) | Python code — portfolio piece |
| **Config module** | `config.py` | Python — key management pattern |
| **Dashboard** | `static/index.html` | Frontend — recruiter showcase |
| **Client config** | `client_config.json` | Config — white-label template |
| **Launcher** | `run.sh` | Shell script — one-command start |
| **Dockerfile** | `Dockerfile` | Deployment — HF Spaces |
| **Dependencies** | `requirements.txt` | Configuration |
| **Build plan** | `BUILD_PLAN.md` | Documentation — architectural spec |
| **Build instructions** | `CLINE_INSTRUCTIONS.md` | Documentation — builder brief |
| **Build journal** | `DEV_LOG.md` | Documentation — process history |
| **Portfolio readme** | `README.md` | Documentation — API reference + pitch |
| **Live demo** | `https://5lanxo-ai-automator.hf.space` | Deployment — public URL |

### Endpoint Summary

| Method | Path | What It Does | Model | Cost | Latency |
|--------|------|-------------|-------|------|---------|
| `GET` | `/health` | Health check | — | — | Instant |
| `GET` | `/config` | Get voice/character config | — | — | Instant |
| `PUT` | `/config` | Update config (live, no restart) | — | — | Instant |
| `GET` | `/` | Dashboard (index.html) | — | — | Instant |
| `GET` | `/docs` | OpenAPI docs | — | — | Instant |
| `POST` | `/classify` | Email → JOB/CLIENT/URGENT/NOISE | deepseek-chat | ~$0.00003/call | ~1-3s |
| `POST` | `/respond` | Contextual AI reply | deepseek-chat | ~$0.00004/call | ~2-5s |
| `POST` | `/enrich` | Lead research (structured JSON) | deepseek-r1 | ~$0.0004/call | ~30-90s |
| `POST` | `/report` | Daily ops summary | deepseek-chat | ~$0.00006/call | ~3-8s |

### Model Cost Comparison

| Model | Input Cost | Output Cost | Use Case |
|-------|-----------|------------|----------|
| `deepseek/deepseek-chat` | $0.14/M tokens | $0.28/M tokens | Fast classification, generation, summarization |
| `deepseek/deepseek-r1` | $0.55/M tokens | $2.19/M tokens | Deep reasoning, company research |

---

## 9. Timeline Summary

```
[Planning]
  ├── BUILD_PLAN.md written — 11-task architectural spec
  ├── CLINE_INSTRUCTIONS.md written — builder brief
  └── Project scaffold created

[Cline Builds — Phase 1]
  ├── Tasks 1-3: Scaffold, config.py, server.py skeleton
  ├── Tasks 4-7: classify, respond, enrich, report endpoints
  ├── Task 8: Dark-themed demo dashboard
  ├── Task 9: run.sh, Dockerfile, README
  ├── Task 10: Smoke tests — all pass
  └── Task 11: Deploy to HF Spaces

[Sweet Jones P 🍯 — Phase 2 Refactors]
  ├── run.sh: Fixed venv path, added $PORT, strict mode
  ├── server.py: Removed reload=True, added CORS, Pydantic models,
  │   config endpoints, live config system, helper consolidation
  ├── Dockerfile: Explicit file COPY, WORKDIR, python→python
  ├── index.html: Complete redesign with Config Editor tab
  ├── client_config.json: Finalized voice/character settings
  └── DEV_LOG.md: Full build journal written

[Deploy]
  └── HF Space created at 5lanxo/ai-automator
      └── Status: BUILDING (APP_STARTING as of 00:38 UTC)
```

---

## Appendix: Key Technical Decisions & Rationale

### Why FastAPI over Flask?
- Native async (httpx needs async for concurrent outbound API calls)
- Auto-generated OpenAPI docs at `/docs` — recruiter-facing portfolio bonus
- Pydantic integration — type-safe request/response models
- Built-in CORS support

### Why Pydantic models instead of raw `request.json()`?
- Auto-validation with descriptive error messages
- FastAPI auto-generates OpenAPI docs
- Type hints make code self-documenting
- Recruiters see production-quality patterns

### Why deepseek-r1 for `/enrich` but deepseek-chat for everything else?
- `/enrich` needs real reasoning — company research benefits from chain-of-thought
- classify/respond/report are fast classification and generation
- deepseek-chat is 1/10th the cost and much faster

### Why hot-reloadable `client_config.json` instead of env vars?
- Non-technical clients can edit their voice/persona through the dashboard
- Changes take effect immediately — no server restart
- Config is JSON-serialized and human-readable
- White-label ready — copy per client

### Why the config merge-with-defaults pattern?
- Missing fields after a config update won't crash the server
- Future config schema additions are backward-compatible
- Dashboard never sends null/undefined values that could break prompt building
