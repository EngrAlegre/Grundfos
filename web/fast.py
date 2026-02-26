import sys
import os

# Add parent directory to path to import src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from src.agent import lookup_pump_hybrid, answer_about_pump
import re
import time
from pathlib import Path


app = FastAPI()

frontend_dir = Path(__file__).resolve().parent / "frontend"
app.mount(
    "/ui",
    StaticFiles(directory=str(frontend_dir), html=True),
    name="frontend",
)


@app.get("/", include_in_schema=False)
async def root_redirect():
    return HTMLResponse(
        '<!doctype html><html><head><meta http-equiv="refresh" content="0; url=/ui/"></head></html>'
    )


def _parse_natural_query(query: str) -> tuple[str, str]:
    """Extract (manufacturer, product) from free text like 'TACO 0014-SF1'."""
    query = query.strip()

    known_brands = [
        "TACO",
        "WILO",
        "BIRAL",
        "EMB",
        "SMEDEGAARD",
        "DAB",
        "CIRCAL",
        "LOEWE",
        "GRUNDFOS",
        "XYLEM",
    ]

    prefixes = [
        r"(?:give\s+me\s+)?(?:the\s+)?(?:specifications?|specs?|data|info)\s+(?:for|of|on)\s+(?:a\s+)?",
        r"(?:look\s*up|search|find|get)\s+",
        r"(?:what\s+(?:are|is)\s+the\s+(?:specs?|specifications?|data)\s+(?:for|of)\s+)",
    ]
    for p in prefixes:
        query = re.sub(p, "", query, flags=re.IGNORECASE).strip()

    # 1) Brand at the very start (e.g. "TACO 0014-SF1")
    for brand in known_brands:
        pattern = rf"^{re.escape(brand)}\b\s*(.+)"
        m = re.match(pattern, query, re.IGNORECASE)
        if m:
            prod = m.group(1).strip().strip(".,;:!?")
            return brand.upper(), prod

    # 2) Brand anywhere in the sentence (e.g. "What is TACO 0014-SF1?")
    upper_q = query.upper()
    for brand in known_brands:
        idx = upper_q.find(brand)
        if idx != -1:
            after = query[idx + len(brand) :].strip().strip(".,;:!?")
            if after:
                return brand.upper(), after

    parts = query.split(None, 1)
    if len(parts) == 2:
        return parts[0].upper(), parts[1].strip().strip(".,;:!?")
    return "", query.strip().strip(".,;:!?")


_QUESTION_PATTERNS = re.compile(
    r"\?|"
    r"\b(?:what|how|why|where|when|which|who|does|is\s+it|can\s+it|"
    r"tell\s+me|explain|describe|suitable|recommend|compare)\b",
    re.IGNORECASE,
)


def _is_question(text: str) -> bool:
    return bool(_QUESTION_PATTERNS.search(text))


# Backward compatible entrypoint: keep /chat working for older links
@app.get("/chat", response_class=HTMLResponse)
async def get_chat():
    chat_path = frontend_dir / "chat_page.html"
    if not chat_path.exists():
        return HTMLResponse("chat_page.html not found", status_code=404)
    return HTMLResponse(chat_path.read_text(encoding="utf-8"))


@app.get("/chat_page.html", response_class=HTMLResponse, include_in_schema=False)
async def get_chat_page_alias():
    # Allow direct navigation to /chat_page.html (some older bookmarks)
    chat_path = frontend_dir / "chat_page.html"
    if not chat_path.exists():
        return HTMLResponse("chat_page.html not found", status_code=404)
    return HTMLResponse(chat_path.read_text(encoding="utf-8"))


@app.post("/api/ask")
async def ask_pump_question(request: Request):
    """
    Endpoint used by the HTML chat:
    - Accepts { "text": "<user input>" }.
    - Parses manufacturer + product.
    - Returns specs + confidence, and AI answer if it's a question.
    """
    data = await request.json()

    # Support both:
    # - legacy chat.html: {"text": "..."}
    # - frontend/chats.js style: {manufacturer, prodname, question} or {text}
    text = (data.get("text") or "").strip()
    manufacturer = (data.get("manufacturer") or "").strip()
    prodname = (data.get("prodname") or "").strip()
    question = (data.get("question") or "").strip()

    if text and (not manufacturer or not prodname):
        manufacturer, prodname = _parse_natural_query(text)
        question = question or text

    if not manufacturer or not prodname:
        return JSONResponse(
            {
                "ai_answer": None,
                "manufacturer": manufacturer,
                "prodname": prodname,
                "error": "Could not detect manufacturer/product from request.",
            },
            status_code=400,
        )

    start = time.time()
    hybrid = lookup_pump_hybrid(manufacturer, prodname, force_web=True)
    elapsed = time.time() - start

    web_result = hybrid.get("web_result", {}) or {}
    comparison = hybrid.get("hybrid_comparison", {}) or {}
    overall_conf = float(comparison.get("overall_confidence", 0.0))
    overall_label = str(comparison.get("overall_label", "low"))
    confidence_text = f"{overall_label} ({overall_conf * 100:.1f}%)"

    ai_answer = None
    if question and _is_question(question):
        ai_answer = answer_about_pump(manufacturer, prodname, question)

    # Return shape compatible with frontend/chats.js
    return JSONResponse(
        {
            "ai_answer": ai_answer,
            "manufacturer": manufacturer,
            "prodname": prodname,
            "web_result": web_result,
            "local_result": hybrid.get("local_result", {}) or {},
            "hybrid_comparison": hybrid.get("hybrid_comparison", None),
            "time": f"{elapsed:.1f}s",
            "confidence": confidence_text,
        }
    )


@app.post("/api/lookup")
async def api_lookup(request: Request):
    data = await request.json()
    query = (data.get("query") or data.get("text") or "").strip()
    if not query:
        return JSONResponse(
            {
                "manufacturer": "",
                "prodname": "",
                "is_question": False,
                "web_result": {"FLOWNOM56": "unknown", "HEADNOM56": "unknown", "PHASE": "unknown"},
                "local_result": {"FLOWNOM56": "unknown", "HEADNOM56": "unknown", "PHASE": "unknown"},
                "hybrid_comparison": None,
                "error": "Missing query.",
            },
            status_code=400,
        )

    manufacturer, prodname = _parse_natural_query(query)
    if not manufacturer:
        return JSONResponse(
            {
                "manufacturer": "",
                "prodname": prodname,
                "is_question": _is_question(query),
                "web_result": {"FLOWNOM56": "unknown", "HEADNOM56": "unknown", "PHASE": "unknown"},
                "local_result": {"FLOWNOM56": "unknown", "HEADNOM56": "unknown", "PHASE": "unknown"},
                "hybrid_comparison": None,
                "error": "Could not detect manufacturer from query.",
            },
            status_code=200,
        )

    hybrid = lookup_pump_hybrid(manufacturer, prodname, force_web=True)
    return JSONResponse(
        {
            "manufacturer": manufacturer,
            "prodname": prodname,
            "is_question": _is_question(query),
            "web_result": hybrid.get("web_result", {}) or {},
            "local_result": hybrid.get("local_result", {}) or {},
            "hybrid_comparison": hybrid.get("hybrid_comparison", None),
        }
    )
