#!/usr/bin/env python3
"""
AI Business Automator — FastAPI Server
Port 8770 locally, uses $PORT env var on Hugging Face

4 AI-powered business endpoints + live config editor.
Replaces buggy n8n workflows with clean Python.
"""
import os
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import httpx

from config import CONFIG

# ── Hot-Reloadable Client Config ──────────────────────────────────────────

CLIENT_CONFIG_PATH = Path(__file__).parent / "client_config.json"

_DEFAULT_CONFIG = {
    "business_name": "AI Automation Services",
    "voice": "Professional and direct",
    "location": "Houston, Texas",
    "services": "AI automation, business infrastructure, workflow optimization",
    "sign_off": "Best regards",
    "call_to_action": "Let's schedule a call.",
    "never_mention": [],
    "max_words_per_reply": 120,
    "tone_by_category": {}
}


def _load_client_config() -> dict:
    """Load client config from disk — called per-request for hot-reload."""
    try:
        raw = CLIENT_CONFIG_PATH.read_text()
        cfg = json.loads(raw)
        # Merge with defaults so missing fields don't crash
        merged = _DEFAULT_CONFIG.copy()
        merged.update(cfg)
        return merged
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(_DEFAULT_CONFIG)


def _save_client_config(cfg: dict) -> None:
    """Persist client config to disk."""
    CLIENT_CONFIG_PATH.write_text(json.dumps(cfg, indent=2) + "\n")


# ── Request / Response Models ─────────────────────────────────────────────

class EmailClassifyRequest(BaseModel):
    from_email: str
    subject: str
    body: str


class EmailClassifyResponse(BaseModel):
    classification: str
    from_email: str
    subject: str


class InquiryRespondRequest(BaseModel):
    classification: str
    from_email: str
    subject: str
    body: str


class InquiryRespondResponse(BaseModel):
    draft_reply: str
    classification: str


class LeadEnrichRequest(BaseModel):
    company_name: str
    contact_email: str
    additional_context: str = ""


class LeadEnrichResponse(BaseModel):
    enriched_data: dict
    company_name: str


class DailyReportRequest(BaseModel):
    date: str
    emails_processed: int
    leads_generated: int
    tasks_completed: int
    additional_notes: str = ""


class DailyReportResponse(BaseModel):
    summary: str
    key_metrics: dict
    recommendations: str


class ClientConfigUpdate(BaseModel):
    business_name: str | None = None
    voice: str | None = None
    location: str | None = None
    services: str | None = None
    sign_off: str | None = None
    call_to_action: str | None = None
    never_mention: list[str] | None = None
    max_words_per_reply: int | None = None
    tone_by_category: dict[str, str] | None = None


# ── FastAPI App ───────────────────────────────────────────────────────────

app = FastAPI(
    title="AI Business Automator",
    description="AI-powered business automation — email classification, inquiry responses, lead enrichment, daily reporting.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Config Endpoints (live-editable voice / character) ────────────────────

@app.get("/config")
async def get_config():
    """
    Get the current client voice/character configuration.
    Returns everything — use this to populate the Config Editor UI.
    """
    return _load_client_config()


@app.put("/config")
async def update_config(update: ClientConfigUpdate):
    """
    Update specific fields of the client voice/character config.
    Only sends changed fields — unset fields keep their current value.
    Changes persist to disk immediately and apply to the next request.
    """
    cfg = _load_client_config()
    update_dict = update.model_dump(exclude_none=True)
    cfg.update(update_dict)
    _save_client_config(cfg)
    return {"status": "ok", "config": cfg}


# ── Helper: Build voice-aware system prompt from live config ──────────────

def _build_voice_prompt(cfg: dict, category: str = "") -> str:
    """Build a system prompt string from the given config dict."""
    tone = cfg.get("tone_by_category", {}).get(
        category, cfg.get("voice", "Professional and direct")
    )
    never = cfg.get("never_mention", [])
    never_str = f" NEVER mention: {', '.join(never)}." if never else ""
    return (
        f"You are {cfg.get('business_name', 'AI Automation Services')}. "
        f"{tone}. "
        f"Keep replies under {cfg.get('max_words_per_reply', 120)} words. "
        f"Close with: {cfg.get('sign_off', 'Best regards')}"
        f"{never_str}"
    )


# ── Health Check ──────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "ai-business-automator",
        "version": "1.0.0",
        "config_loaded": CONFIG is not None
    }


@app.get("/")
async def root():
    return FileResponse(str(STATIC_DIR / "index.html"))


# ── Email Classifier ──────────────────────────────────────────────────────

@app.post("/classify", response_model=EmailClassifyResponse)
async def classify_email(request: EmailClassifyRequest):
    messages = [
        {
            "role": "system",
            "content": (
                "Classify this email into ONE word only: "
                "JOB, CLIENT, URGENT, or NOISE. No other text. No punctuation."
            )
        },
        {
            "role": "user",
            "content": (
                f"From: {request.from_email} | "
                f"Subject: {request.subject} | "
                f"Body: {request.body}"
            )
        }
    ]
    classification = await _call_openrouter(
        messages=messages,
        model="deepseek/deepseek-chat",
        temperature=0.1,
        max_tokens=30
    )
    return EmailClassifyResponse(
        classification=classification,
        from_email=request.from_email,
        subject=request.subject
    )


# ── Inquiry Responder (uses live voice config) ────────────────────────────

@app.post("/respond", response_model=InquiryRespondResponse)
async def respond_to_inquiry(request: InquiryRespondRequest):
    cfg = _load_client_config()                        # ← hot-reloaded
    category = request.classification.upper()
    system_prompt = _build_voice_prompt(cfg, category)

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"From: {request.from_email}\n"
                f"Subject: {request.subject}\n\n"
                f"Original message:\n{request.body}\n\nDraft a reply:"
            )
        }
    ]
    draft_reply = await _call_openrouter(
        messages=messages,
        model="deepseek/deepseek-chat",
        temperature=0.3,
        max_tokens=300
    )
    return InquiryRespondResponse(
        draft_reply=draft_reply,
        classification=request.classification
    )


# ── Lead Enricher (DeepSeek-R1) ──────────────────────────────────────────

@app.post("/enrich", response_model=LeadEnrichResponse)
async def enrich_lead(request: LeadEnrichRequest):
    user_message = f"""Analyze this lead and provide enrichment data:

Company: {request.company_name}
Contact Email: {request.contact_email}
Additional Context: {request.additional_context or 'None provided'}

Provide a JSON response with the following fields:
- industry: likely industry sector
- company_size: estimated company size (startup/small/medium/enterprise)
- potential_value: estimated business potential (low/medium/high)
- engagement_strategy: recommended approach for engagement
- key_insights: 2-3 bullet points of insights

Return ONLY valid JSON, no markdown formatting."""

    messages = [
        {
            "role": "system",
            "content": (
                "You are a business intelligence analyst. "
                "Analyze the lead information and return structured JSON "
                "data with enrichment insights."
            )
        },
        {"role": "user", "content": user_message}
    ]

    enrichment_result = await _call_openrouter(
        messages=messages,
        model="deepseek/deepseek-r1",
        temperature=0.2,
        max_tokens=800
    )

    try:
        enriched_data = json.loads(enrichment_result)
    except json.JSONDecodeError:
        enriched_data = {
            "raw_analysis": enrichment_result,
            "industry": "Unknown",
            "company_size": "Unknown",
            "potential_value": "medium",
            "engagement_strategy": "Standard outreach",
            "key_insights": ["Analysis available in raw_analysis field"]
        }

    return LeadEnrichResponse(
        enriched_data=enriched_data,
        company_name=request.company_name
    )


# ── Daily Report ──────────────────────────────────────────────────────────

@app.post("/report", response_model=DailyReportResponse)
async def generate_daily_report(request: DailyReportRequest):
    user_message = f"""Generate a daily operations summary report:

Date: {request.date}
Emails Processed: {request.emails_processed}
Leads Generated: {request.leads_generated}
Tasks Completed: {request.tasks_completed}
Additional Notes: {request.additional_notes or 'None'}

Provide:
1. A brief executive summary (2-3 sentences)
2. Recommendations for tomorrow (2-3 actionable items)
Keep it concise and actionable."""

    messages = [
        {
            "role": "system",
            "content": (
                "You are a business operations analyst. "
                "Create concise, actionable daily reports with "
                "clear insights and recommendations."
            )
        },
        {"role": "user", "content": user_message}
    ]

    report_content = await _call_openrouter(
        messages=messages,
        model="deepseek/deepseek-chat",
        temperature=0.2,
        max_tokens=400
    )

    parts = report_content.split("\n\n", 1)
    summary = parts[0] if parts else report_content
    recommendations = parts[1] if len(parts) > 1 else "Continue current operations."

    key_metrics = {
        "emails_processed": request.emails_processed,
        "leads_generated": request.leads_generated,
        "tasks_completed": request.tasks_completed,
        "conversion_rate": (
            f"{(request.leads_generated / max(request.emails_processed, 1) * 100):.1f}%"
        )
    }

    return DailyReportResponse(
        summary=summary,
        key_metrics=key_metrics,
        recommendations=recommendations
    )


# ── OpenRouter Helper ─────────────────────────────────────────────────────

async def _call_openrouter(
    messages: list,
    model: str = "deepseek/deepseek-chat",
    temperature: float = 0.1,
    max_tokens: int = 500,
) -> str:
    if not CONFIG:
        raise HTTPException(
            status_code=500,
            detail="Configuration not loaded. "
                   "Check OPENROUTER_API_KEY in ~/.hermes/.env"
        )

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                CONFIG["openrouter_url"],
                headers={
                    "Authorization": f"Bearer {CONFIG['openrouter_api_key']}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "messages": messages,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=500, detail=f"OpenRouter API error: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Unexpected error: {str(e)}"
            )


# ── Entrypoint ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8770))
    print(f"🚀 AI Business Automator — http://0.0.0.0:{port}")
    print(f"📊 Dashboard — http://localhost:{port}")
    print(f"📋 /docs     — Interactive API docs")
    print(f"⚙️  /config   — Live voice/character config editor")

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=port,
        reload=False,                # ← production: no hot-reload server restart
    )
