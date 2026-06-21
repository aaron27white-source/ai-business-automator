# DEV_LOG.md — AI Business Automator

> Full build journal. Every decision, roadblock, fix.
> Project replaces 4 buggy n8n workflows with a single FastAPI server.

---

## 2026-06-20 — Complete Build & Polish

### Overview

Project rebuilt from scratch. Original concept was 4 n8n workflows that kept breaking
(n8n Respond node couldn't evaluate `{{ }}` expressions, webhook timeouts, UI bugs).
The Python-native version is stable, testable, and deployable.

### Build Order

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Scaffold + venv | ✅ | FastAPI, uvicorn, httpx, python-dotenv |
| 2 | config.py | ✅ | Loads key from `~/.hermes/.env` via dotenv |
| 3 | server.py skeleton + /health | ✅ | Minimal FastAPI, serves static files |
| 4 | POST /classify | ✅ | Email → JOB/CLIENT/URGENT/NOISE (deepseek-chat, temp=0.1) |
| 5 | POST /respond | ✅ | Context-aware reply generator (deepseek-chat, temp=0.3) |
| 6 | POST /enrich | ✅ | Lead research via DeepSeek-R1 (temp=0.2, max_tokens=800) |
| 7 | POST /report | ✅ | Daily ops summary with metrics (deepseek-chat, temp=0.2) |
| 8 | static/index.html | ✅ | Dark-themed dashboard (--bg:#0a0a0f, --accent:#6d28d9) |
| 9 | run.sh + Dockerfile + README | ✅ | Deploy-ready |

### Smoke Test Results (all passed)

```
GET  /health  → 200  {"status":"ok","config_loaded":true}
POST /classify → 200  "classification":"JOB"
POST /respond  → 200  "draft_reply":"Marcus,...Let's talk."
POST /enrich   → 200  "enriched_data":{industry,size,strategy,insights}
POST /report   → 200  "summary":"Executive summary...","recommendations":"..."
```

### Architecture Decisions

**Why Pydantic models instead of raw `request.json()`:**
- Auto-validation + descriptive error messages
- FastAPI auto-generates OpenAPI docs at `/docs`
- Type hints make the code self-documenting for recruiters

**Why deepseek-r1 for /enrich but deepseek-chat for everything else:**
- /enrich needs real reasoning — company research benefits from chain-of-thought
- classify/respond/report are fast classification and generation — deepseek-chat is cheaper (1/10th the cost) and faster

**Why hot-reloadable client_config.json instead of env vars:**
- Non-technical clients can edit their voice/persona through the dashboard
- Changes take effect immediately — no server restart
- Config is JSON-serialized and human-readable

### Files Created

```
ai-automator/
├── config.py              ← API key loading from ~/.hermes/.env
├── server.py              ← FastAPI app (5 GET + 4 POST endpoints)
├── static/index.html      ← Dark dashboard + live config editor
├── client_config.json     ← Editable voice/character per client
├── requirements.txt       ← Pinned deps
├── Dockerfile             ← HF Spaces deployment
├── run.sh                 ← Launcher (auto-creates venv)
├── .gitignore             ← Python ignores
├── BUILD_PLAN.md          ← Architectural spec (for Cline)
├── CLINE_INSTRUCTIONS.md  ← Build instructions
├── README.md              ← Portfolio docs + API reference
└── DEV_LOG.md             ← This file — build journal
```

---

### Known Issues / Future Work

| Issue | Priority | Fix |
|-------|----------|-----|
| **HF Spaces cold start** | Medium | Free tier sleeps after inactivity; first request takes ~30s |
| **R1 latency** | Low | /enrich uses DeepSeek-R1 = can take 30-90s. Switch to deepseek-chat for speed if needed |
| **Rate limiting** | Low | No concurrency gate yet. Copy the token-bucket pattern from agent-workbench if going public |
| **client_config.json on HF** | Low | Persisted in container FS only. For multi-user, swap to a DB or mounted volume |

---

## 2026-06-20 — Post-Build Refactor (Sweet Jones P 🍯)

### Changes

1. **run.sh** — Fixed `venv/` → `.venv/` path mismatch. Added `set -euo pipefail`,
   auto-creates venv if missing, uses `$PORT` env var.

2. **server.py** — Major production hardening:
   - Removed `reload=True` (was leaking uvicorn watcher processes)
   - Added `GET /config` and `PUT /config` endpoints for live voice/character editing
   - `_load_client_config()` called per-request — changes are live immediately
   - Config merges with defaults so missing fields don't crash
   - Pydantic `ClientConfigUpdate` model — partial updates only (send just changed fields)
   - Consolidated duplicate helper functions
   - Cleaned up comments + docstrings for portfolio readability

3. **Dockerfile** — Added `client_config.json` and `run.sh` to the COPY. Bumped to
   Python 3.12-slim.

4. **static/index.html** — Complete redesign:
   - Two-tab layout: **Tools** (the 4 endpoints) and **Voice Config** (live editor)
   - Config Editor auto-loads current settings from `GET /config`
   - Editable fields: business name, location, services, voice, sign-off, CTA,
     max words, "never mention" list, tone-per-category for JOB/CLIENT/URGENT/NOISE
   - "Save Config" → `PUT /config` → toast confirmation → live immediately
   - "Reload from Disk" resets form to saved state
   - Toast notifications for success/error feedback

5. **DEV_LOG.md** — Created (this file). Full build journal for portfolio context.

### Smoke Test (post-refactor)

```
GET  /config  → 200  Full config JSON
PUT  /config  → 200  {"status":"ok","config":{...}}
```

All previous endpoints unchanged — still passing.
