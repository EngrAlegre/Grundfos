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


app = FastAPI()

# Serve static files (JS, CSS, images)
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
    name="static",
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


# Serve landing page
@app.get("/", response_class=HTMLResponse)
async def get_landing():
    with open(
        os.path.join(os.path.dirname(__file__), "landing_page.html"), encoding="utf-8"
    ) as f:
        return f.read()


# Serve chat page
@app.get("/chat", response_class=HTMLResponse)
async def get_chat():
    with open(
        os.path.join(os.path.dirname(__file__), "chat.html"), encoding="utf-8"
    ) as f:
        return f.read()


@app.post("/api/ask")
async def ask_pump_question(request: Request):
    """
    Endpoint used by the HTML chat:
    - Accepts { "text": "<user input>" }.
    - Parses manufacturer + product.
    - Returns specs + confidence, and AI answer if it's a question.
    """
    data = await request.json()
    text = (data.get("text") or "").strip()
    if not text:
        return JSONResponse(
            {
                "flow": None,
                "head": None,
                "phase": None,
                "time": None,
                "confidence": None,
                "ai_answer": None,
            }
        )

    manufacturer, prodname = _parse_natural_query(text)

    start = time.time()
    hybrid = lookup_pump_hybrid(manufacturer, prodname, force_web=True)
    elapsed = time.time() - start

    web_result = hybrid.get("web_result", {}) or {}
    comparison = hybrid.get("hybrid_comparison", {}) or {}
    overall_conf = float(comparison.get("overall_confidence", 0.0))
    overall_label = str(comparison.get("overall_label", "low"))
    confidence_text = f"{overall_label} ({overall_conf * 100:.1f}%)"

    ai_answer = None
    if _is_question(text):
        ai_answer = answer_about_pump(manufacturer, prodname, text)

    return JSONResponse(
        {
            "flow": web_result.get("FLOWNOM56"),
            "head": web_result.get("HEADNOM56"),
            "phase": web_result.get("PHASE"),
            "time": f"{elapsed:.1f}s",
            "confidence": confidence_text,
            "ai_answer": ai_answer,
        }
    )
