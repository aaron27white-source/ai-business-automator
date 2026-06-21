# AI Business Automator — Python-Native Replacement for n8n Workflows

> **For Hermes:** Use plan skill to present this to Aaron, then Cline builds task-by-task. OpenClaw tests. 
> **Aaron teaches:** Each section has "What You're Learning" callouts so he walks away understanding, not just watching.

**Goal:** Replace 4 buggy n8n workflows with a single FastAPI server — professional, deployable, client-reusable. Same AI calls. Same sidecar logic. Zero n8n UI bugs.

**Architecture:** FastAPI server with 4 POST endpoints (+ health, + demo page). Uses the same OpenRouter key-loading pattern as agent-workbench. Serves a dark-themed demo page where recruiters can test all 4 workflows live. Deploys to HF Spaces alongside the existing agent-workbench dashboard.

**Tech Stack:** FastAPI, httpx, OpenRouter API, vanilla HTML/CSS/JS, HF Spaces (Docker)

**What this replaces:** All 4 n8n workflows. The sidecar (`sidecar.py`) gets absorbed into this server — it IS the sidecar now.

---

## 🎓 What You're Learning (Aaron)

| Concept | Where It Shows Up |
|---------|-------------------|
| **FastAPI** | The whole server. Python's modern web framework — async, fast, self-documenting. |
| **Separation of concerns** | Each endpoint does ONE job. `/classify` only classifies. `/respond` only responds. |
| **Environment variables** | API key lives in `.env`, never in code. This is how professionals handle secrets. |
| **Client reusability** | The config system lets each client use their own key. Same code, different `.env`. |
| **Deployment** | Same Docker pattern as agent-workbench. HF Spaces reads `PORT` env var. |

---

## Project Structure

```
portfolio-projects/ai-automator/
├── server.py              # FastAPI app — all 4 endpoints + demo page
├── static/
│   └── index.html         # Demo dashboard (recruiters test it here)
├── config.py              # API key loading (reusable, client-swappable)
├── requirements.txt       # Pinned deps
├── Dockerfile             # HF Spaces deployment
├── run.sh                 # One-command launcher
├── README.md              # Architecture + API docs + portfolio pitch
└── DEV_LOG.md             # Every change, roadblock, fix
```

---

## Task 1: Scaffold the Project

**Objective:** Create the project directory, venv, and dependencies.

**Files:**
- Create: `portfolio-projects/ai-automator/`
- Create: `portfolio-projects/ai-automator/requirements.txt`

**Step 1: Create directory and venv**

```bash
mkdir -p ~/workspace/portfolio-projects/ai-automator/static
cd ~/workspace/portfolio-projects/ai-automator
python3 -m venv .venv
```

**Step 2: Write requirements.txt**

```txt
fastapi>=0.115,<1
uvicorn>=0.34,<1
httpx>=0.28,<1
pydantic>=2.10,<3
```

**Step 3: Install deps**

```bash
.venv/bin/pip install -r requirements.txt
```

**Step 4: Verify**

```bash
.venv/bin/python3 -c "import fastapi, uvicorn, httpx; print('Deps OK')"
```

Expected: `Deps OK`

---

## Task 2: Create the Config Module

**🎓 What You're Learning:** Environment variables and secret management. Your API key is money. You never hardcode it. You load it from `.env` at startup, and if it's missing, the app fails LOUDLY instead of silently breaking.

**Objective:** Centralized API key loading that works locally AND on HF Spaces.

**Files:**
- Create: `portfolio-projects/ai-automator/config.py`

**Complete code:**

```python
"""Config — loads OpenRouter API key from environment or .env file."""
import os, subprocess

def load_api_key() -> str:
    """Load OPENROUTER_API_KEY. Tries env first, then ~/.hermes/.env."""
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if key and len(key) > 10:
        return key
    
    # Fallback: source the Hermes .env file
    result = subprocess.run(
        ['bash', '-c', 'source ~/.hermes/.env 2>/dev/null && echo $OPENROUTER_API_KEY'],
        capture_output=True, text=True
    )
    key = result.stdout.strip()
    if key and len(key) > 10:
        return key
    
    raise RuntimeError(
        "OPENROUTER_API_KEY not found. "
        "Set it in ~/.hermes/.env or as an environment variable."
    )

# Module-level constant — loaded once at import
OPENROUTER_API_KEY = load_api_key()
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Default AI model (clients can override per-endpoint)
DEFAULT_MODEL = "deepseek/deepseek-chat"
```

**Verify:**

```bash
cd ~/workspace/portfolio-projects/ai-automator
.venv/bin/python3 -c "from config import OPENROUTER_API_KEY; print(f'Key loaded: {len(OPENROUTER_API_KEY)} chars')"
```

Expected: `Key loaded: 44 chars`

---

## Task 3: Create the Server Skeleton + Health Endpoint

**🎓 What You're Learning:** FastAPI basics. A FastAPI app is just a Python object (`app = FastAPI()`). You attach functions to it with decorators (`@app.get("/health")`). FastAPI automatically generates docs at `/docs` — try it when the server's running.

**Objective:** Minimal FastAPI server that starts, serves a health check, and loads the API key.

**Files:**
- Create: `portfolio-projects/ai-automator/server.py`

**Complete code:**

```python
#!/usr/bin/env python3
"""
AI Business Automator — Python-native automation server.
Replaces n8n workflows with FastAPI endpoints.
4 AI-powered business tools: classify, respond, report, enrich.
"""
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os

from config import OPENROUTER_API_KEY, OPENROUTER_URL, DEFAULT_MODEL

app = FastAPI(title="AI Business Automator", version="1.0.0")

THIS_DIR = Path(__file__).parent

# ═══ Health Check ═══

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "api_key_configured": len(OPENROUTER_API_KEY) > 10,
        "endpoints": ["/classify", "/respond", "/report", "/enrich"]
    }

# ═══ Startup ═══

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8770"))
    print(f"  🤖 AI Business Automator — http://0.0.0.0:{port}")
    print(f"  📋 /docs  — Interactive API documentation")
    print(f"  🩺 /health — Health check")
    uvicorn.run(app, host="0.0.0.0", port=port)
```

**Verify:**

```bash
cd ~/workspace/portfolio-projects/ai-automator
.venv/bin/python3 server.py &
sleep 2
curl -s http://localhost:8770/health | python3 -m json.tool
kill %1
```

Expected: `{"status": "ok", "api_key_configured": true, ...}`

---

## Task 4: Add the Email Classifier Endpoint (WF1)

**🎓 What You're Learning:** POST endpoints and AI prompt engineering. The `@app.post()` decorator marks this as a POST route. The function receives JSON automatically (FastAPI + Pydantic). The prompt engineering is the real skill — notice how `temperature: 0.1` (nearly deterministic) and `max_tokens: 30` (forced brevity) make the classification reliable.

**Objective:** `POST /classify` — receives an email, returns JOB/CLIENT/URGENT/NOISE.

**Files:**
- Modify: `portfolio-projects/ai-automator/server.py` — add the endpoint

**Add this code (above `if __name__` block):**

```python
# ═══ Email Classifier (ex-WF1) ═══

@app.post("/classify")
async def classify(request: Request):
    """
    Classify an email as JOB, CLIENT, URGENT, or NOISE.
    
    Body: {"from": "...", "subject": "...", "body": "..."}
    Returns: {"classification": "JOB", "from": "...", "subject": "..."}
    """
    data = await request.json()
    email_from = data.get("from", "unknown")
    subject = data.get("subject", "")
    body = data.get("body", "")
    
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(OPENROUTER_URL, json={
            "model": DEFAULT_MODEL,
            "temperature": 0.1,
            "max_tokens": 30,
            "messages": [
                {
                    "role": "system",
                    "content": "Classify this email into ONE word only: JOB, CLIENT, URGENT, or NOISE. No other text. No punctuation."
                },
                {
                    "role": "user",
                    "content": f"From: {email_from} | Subject: {subject} | Body: {body}"
                }
            ]
        }, headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        })
        
        if r.status_code == 429:
            return JSONResponse({"error": "Rate limited. Wait and retry."}, status_code=429)
        if r.status_code == 401:
            return JSONResponse({"error": "Invalid API key."}, status_code=401)
        
        r.raise_for_status()
        result = r.json()
        classification = result["choices"][0]["message"]["content"].strip()
    
    return {
        "classification": classification,
        "from": email_from,
        "subject": subject
    }
```

**Verify:**

```bash
cd ~/workspace/portfolio-projects/ai-automator
.venv/bin/python3 server.py &
sleep 2
curl -s -X POST http://localhost:8770/classify \
  -H "Content-Type: application/json" \
  -d '{"from":"recruiter@techcorp.com","subject":"Interview Request","body":"Hi Aaron, we reviewed your portfolio and want to interview you."}'
kill %1
```

Expected: `{"classification":"JOB","from":"recruiter@techcorp.com","subject":"Interview Request"}`

---

## Task 5: Add the Inquiry Router Endpoint (WF2)

**🎓 What You're Learning:** Why WF2 broke in n8n but works here. n8n's Respond node couldn't evaluate `{{ }}` expressions. FastAPI's `return {...}` is just Python — no templating language, no sandbox, no mystery. The code does exactly what it looks like it does.

**Objective:** `POST /respond` — receives a client inquiry, returns an AI-drafted reply in Aaron's voice.

**Add this code (after the classify endpoint):**

```python
# ═══ Inquiry Router (ex-WF2) ═══

@app.post("/respond")
async def respond(request: Request):
    """
    Draft a professional reply to a client inquiry.
    
    Body: {"name": "...", "company": "...", "contact": "...", "message": "..."}
    Returns: {"response": "AI-drafted reply text", "name": "...", "company": "..."}
    """
    data = await request.json()
    name = data.get("name", "")
    company = data.get("company", "")
    contact = data.get("contact", "")
    message = data.get("message", "")
    
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(OPENROUTER_URL, json={
            "model": DEFAULT_MODEL,
            "temperature": 0.7,
            "max_tokens": 250,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Aaron White, an AI automation and business infrastructure "
                        "developer based in Houston, Texas. A potential client reached out. "
                        "Write a direct, concise reply. No corporate fluff. "
                        "Be specific to their message. Include a clear next step (suggest a call). "
                        "Keep it under 120 words. Close with your name. Houston energy. "
                        "NEVER make up contact info or pricing unless mentioned."
                    )
                },
                {
                    "role": "user",
                    "content": f"Client: {name} ({company})\nContact: {contact}\nMessage: {message}"
                }
            ]
        }, headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        })
        
        if r.status_code == 429:
            return JSONResponse({"error": "Rate limited."}, status_code=429)
        if r.status_code == 401:
            return JSONResponse({"error": "Invalid API key."}, status_code=401)
        r.raise_for_status()
        response_text = r.json()["choices"][0]["message"]["content"].strip()
    
    return {
        "response": response_text,
        "name": name,
        "company": company
    }
```

**Verify:**

```bash
curl -s -X POST http://localhost:8770/respond \
  -H "Content-Type: application/json" \
  -d '{"name":"Marcus Thompson","company":"Gulf Coast Logistics","contact":"marcus@gulfcoast.com","message":"We process 150 shipments a month. Need this automated."}'
```

Expected: JSON with `response` field containing a real AI-drafted reply.

---

## Task 6: Add the Lead Enricher Endpoint (WF4)

**🎓 What You're Learning:** Structured outputs from AI. The prompt told the AI to output in a specific format (INDUSTRY:, SIZE:, etc.). This is called "constrained generation" — you tell the AI exactly what format to use, and it follows. More reliable than hoping it gets creative.

**Objective:** `POST /enrich` — receives a company name, returns a structured research profile.

**Add this code:**

```python
# ═══ Lead Enricher (ex-WF4) ═══

@app.post("/enrich")
async def enrich(request: Request):
    """
    Research a company and return a structured profile.
    
    Body: {"company": "...", "website": "..."}
    Returns: {"company": "...", "profile": "structured research text"}
    """
    data = await request.json()
    company = data.get("company", "")
    website = data.get("website", "")
    
    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(OPENROUTER_URL, json={
            "model": "deepseek/deepseek-r1",
            "temperature": 0.3,
            "max_tokens": 400,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Research this company. Output exactly in this format:\n"
                        "INDUSTRY: [primary]\n"
                        "SIZE: [estimated employees]\n"
                        "LOCATION: [HQ]\n"
                        "KEY PRODUCTS: [what they do]\n"
                        "POTENTIAL NEEDS: [automation/AI services they might need]\n"
                        "OUTREACH ANGLE: [best way to approach]\n"
                        "CONFIDENCE: [HIGH/MEDIUM/LOW]"
                    )
                },
                {
                    "role": "user",
                    "content": f"Company: {company}\nWebsite: {website}"
                }
            ]
        }, headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        })
        
        if r.status_code == 429:
            return JSONResponse({"error": "Rate limited."}, status_code=429)
        if r.status_code == 401:
            return JSONResponse({"error": "Invalid API key."}, status_code=401)
        r.raise_for_status()
        profile = r.json()["choices"][0]["message"]["content"].strip()
    
    return {
        "company": company,
        "profile": profile
    }
```

**Verify:**

```bash
curl -s -X POST http://localhost:8770/enrich \
  -H "Content-Type: application/json" \
  -d '{"company":"Notion","website":"notion.so"}' | python3 -m json.tool
```

Expected: Structured profile with INDUSTRY, SIZE, LOCATION, etc.

---

## Task 7: Add the Auto Reporter Endpoint (WF3)

**🎓 What You're Learning:** AI summarization. This endpoint doesn't need a webhook trigger — it's designed to be called by a cron job (every morning at 9am, every evening at 5pm). The prompt includes emoji sections because the output goes to Discord.

**Objective:** `POST /report` — generates an operations summary from provided data.

**Add this code:**

```python
# ═══ Auto Reporter (ex-WF3) ═══

@app.post("/report")
async def report(request: Request):
    """
    Generate an operations summary. Designed for cron/daily triggers.
    
    Body: {"data": "today's numbers and context..."}
    Returns: {"report": "formatted markdown summary"}
    """
    data = await request.json()
    context = data.get("data", data.get("context", ""))
    
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(OPENROUTER_URL, json={
            "model": DEFAULT_MODEL,
            "temperature": 0.3,
            "max_tokens": 400,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Generate a daily operations summary as a Discord message with "
                        "emoji sections: 📊 Today's Numbers, ⚠️ Urgent Items, 📈 Trends, "
                        "🎯 Action Items. Direct. No fluff. Aaron's voice — Houston energy."
                    )
                },
                {
                    "role": "user",
                    "content": f"Today's data:\n{context}\n\nGenerate the report."
                }
            ]
        }, headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        })
        
        if r.status_code == 429:
            return JSONResponse({"error": "Rate limited."}, status_code=429)
        if r.status_code == 401:
            return JSONResponse({"error": "Invalid API key."}, status_code=401)
        r.raise_for_status()
        report_text = r.json()["choices"][0]["message"]["content"].strip()
    
    return {"report": report_text}
```

**Verify:**

```bash
curl -s -X POST http://localhost:8770/report \
  -H "Content-Type: application/json" \
  -d '{"data":"12 inquiries, 47 emails, 8 leads, 2 urgent items. Closed 3 deals. Pipeline growing."}'
```

Expected: Formatted markdown with emoji sections.

---

## Task 8: Add the Demo Frontend

**🎓 What You're Learning:** Serving static files. FastAPI's `StaticFiles` mount makes a whole folder available at a URL path. The demo page is pure HTML/CSS/JS — no framework. Every recruiter can open this page and test ALL 4 tools live. This is your portfolio's front door.

**Objective:** Dark-themed demo page where visitors can test all 4 endpoints.

**Files:**
- Create: `portfolio-projects/ai-automator/static/index.html`

**Mount static files (add near top of server.py, after `app = FastAPI(...)`):**

```python
# Serve demo frontend
app.mount("/static", StaticFiles(directory=str(THIS_DIR / "static")), name="static")

@app.get("/")
async def index():
    """Serve the demo dashboard."""
    return HTMLResponse((THIS_DIR / "static" / "index.html").read_text())
```

**The demo page (`static/index.html`) should have:**

1. Dark-themed layout matching agent-workbench style
2. 4 tabs or sections — one per tool
3. Each section: input fields + "Test" button + live result display
4. `/classify` section: pre-filled email example, classification badge result
5. `/respond` section: name/company/message fields, AI reply displayed
6. `/enrich` section: company name + website, structured profile output
7. `/report` section: data input, formatted markdown output
8. "Powered by OpenRouter + DeepSeek" footer
9. Link to GitHub / HF Space

*(Cline builds the full HTML. ~200 lines. Use the existing demo.html as a style reference.)*

---

## Task 9: Add run.sh, Dockerfile, README

**Objective:** Production-ready launcher, deployment config, and documentation.

**Files:**
- Create: `portfolio-projects/ai-automator/run.sh`
- Create: `portfolio-projects/ai-automator/Dockerfile`  
- Create: `portfolio-projects/ai-automator/README.md`

**run.sh:**

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

**Dockerfile:**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 7860
CMD ["python3", "server.py"]
```

**README.md** — let Cline write this. Must include:
- What it is (1 sentence)
- Architecture (4 endpoints explained)
- API docs (each endpoint: method, body, response)
- How to run locally
- How to deploy to HF Spaces
- How clients swap in their own API key
- Link to live demo

---

## Task 10: Smoke Test All 4 Endpoints

**Objective:** Every endpoint returns correct AI output.

**Commands:**

```bash
cd ~/workspace/portfolio-projects/ai-automator
.venv/bin/python3 server.py &
sleep 2

# Test 1: Classify
echo "=== CLASSIFY ==="
curl -s -X POST http://localhost:8770/classify \
  -H "Content-Type: application/json" \
  -d '{"from":"jobs@company.com","subject":"Software Engineer Position","body":"We would like to interview you."}'

# Test 2: Respond  
echo -e "\n=== RESPOND ==="
curl -s -X POST http://localhost:8770/respond \
  -H "Content-Type: application/json" \
  -d '{"name":"Sarah Chen","company":"TechNova","contact":"sarah@technova.io","message":"Need AI automation for our 50-person team. What can you build?"}'

# Test 3: Report
echo -e "\n=== REPORT ==="
curl -s -X POST http://localhost:8770/report \
  -H "Content-Type: application/json" \
  -d '{"data":"15 new leads, 3 closed, 8 in pipeline. Website traffic up 40%."}'

# Test 4: Enrich
echo -e "\n=== ENRICH ==="
curl -s -X POST http://localhost:8770/enrich \
  -H "Content-Type: application/json" \
  -d '{"company":"Linear","website":"linear.app"}'

kill %1
```

**Expected:** All 4 return valid JSON with AI-generated content.

---

## Task 11: Deploy to HF Spaces (alongside agent-workbench)

**🎓 What You're Learning:** Multi-app HF Spaces. Your `5lanxo` namespace can host multiple Spaces. The agent-workbench is at `5lanxo/agent-workbench`. This goes to `5lanxo/ai-automator`. Each Space is independent — separate Docker container, separate URL.

**Steps (Cline executes):**

1. Install: `.venv/bin/pip install huggingface_hub`
2. Create Space: `api.create_repo("5lanxo/ai-automator", repo_type="space", space_sdk="docker")`
3. Add secret: `api.add_space_secret("5lanxo/ai-automator", key="OPENROUTER_API_KEY", value=...)`
4. Upload all files
5. Wait for build (free tier: 5-15 min first deploy)
6. Verify: `curl https://5lanxo-ai-automator.hf.space/health`

**Result:** `https://5lanxo-ai-automator.hf.space` — live demo, recruiter-ready.

---

## What Aaron Gets At The End

| Asset | Value |
|-------|-------|
| `5lanxo-ai-automator.hf.space` | Public demo — recruiters test it live |
| `server.py` (~200 lines) | Clean FastAPI code — portfolio piece |
| 4 AI endpoints | Classify, respond, report, enrich — all working |
| Demo page | Dark-themed, professional, no login needed |
| Client-ready architecture | Swap `.env` = new client deployment |
| DEV_LOG.md | Complete build history — shows your process |

---

## Risks & Open Questions

1. **R1 model latency** — `/enrich` uses deepseek-r1 which can take 30-90s. Consider switching to deepseek-chat for speed.
2. **Rate limiting** — No concurrency gate yet. Add one before public launch (copy from agent-workbench pattern).
3. **HF Spaces cold start** — Free tier sleeps after inactivity. First request may take 30s to wake.

---

## Build Order (for Cline)

1. Task 1-3: Scaffold + config + skeleton (foundation)
2. Task 4-7: All 4 endpoints (the meat)
3. Task 8: Demo frontend (the showpiece)
4. Task 9: run.sh + Dockerfile + README (production polish)
5. Task 10: Smoke test all 4 (verification)
6. Task 11: Deploy to HF (go live)

**Cline builds each task. OpenClaw tests. Aaron learns.**
