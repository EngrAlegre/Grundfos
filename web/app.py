from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
import re
from typing import Any

from src.agent import lookup_pump_hybrid, answer_about_pump


app = FastAPI()


def _clean_prodname(text: str) -> str:
    s = (text or "").strip()
    if not s:
        return ""

    s = re.split(r"[?]", s, maxsplit=1)[0].strip()
    s = re.split(r"\b(?:and|how|what|why|where|when|which|who)\b", s, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    s = s.strip().strip(".,;:!\"'()[]{}")
    return s


def parse_natural_query(query: str) -> tuple[str, str]:
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
        r"(?:what\s+is|what's|whats)\s+",
        r"(?:tell\s+me\s+about)\s+",
    ]
    for p in prefixes:
        query = re.sub(p, "", query, flags=re.IGNORECASE).strip()

    for brand in known_brands:
        m = re.search(rf"\b{re.escape(brand)}\b", query, flags=re.IGNORECASE)
        if not m:
            continue
        prod = _clean_prodname(query[m.end() :])
        return brand.upper(), prod

    parts = query.split(None, 1)
    if len(parts) == 2:
        maybe_mfr = parts[0].upper()
        if maybe_mfr in known_brands:
            return maybe_mfr, _clean_prodname(parts[1])
        return "", query.strip().strip(".,;:!?")
    return "", query.strip().strip(".,;:!?")


_QUESTION_PATTERNS = re.compile(
    r"\?|"
    r"\b(?:what|how|why|where|when|which|who|does|is\s+it|can\s+it|"
    r"tell\s+me|explain|describe|suitable|recommend|compare)\b",
    re.IGNORECASE,
)


def is_question(query: str) -> bool:
    return bool(_QUESTION_PATTERNS.search(query))


class LookupRequest(BaseModel):
    query: str


class AskRequest(BaseModel):
    manufacturer: str | None = None
    prodname: str | None = None
    question: str | None = None
    text: str | None = None


def _fallback_ai_answer(manufacturer: str, prodname: str, question: str) -> str:
    from src.config import PERPLEXITY_API_KEY
    from src.pump_dictionary import get_from_db

    local = get_from_db(manufacturer, prodname) if manufacturer and prodname else None
    flow = (local or {}).get("FLOWNOM56", "unknown")
    head = (local or {}).get("HEADNOM56", "unknown")
    phase = (local or {}).get("PHASE", "unknown")

    why = (
        "PERPLEXITY_API_KEY is not set, so AI explanations are disabled."
        if not PERPLEXITY_API_KEY
        else "The AI explanation service failed for this request."
    )

    specs_bits = []
    if flow != "unknown":
        specs_bits.append(f"flow {flow} m3/h")
    if head != "unknown":
        specs_bits.append(f"head {head} m")
    if phase != "unknown":
        specs_bits.append(f"phase {phase}")
    specs = f"Known specs: {', '.join(specs_bits)}." if specs_bits else "No verified specs available yet."

    name = " ".join(x for x in [manufacturer, prodname] if x).strip() or "this pump"

    return (
        f"I can’t generate the AI explanation right now ({why}) "
        f"For {name}: {specs} "
        "If you want accurate usage guidance, I need the AI key enabled or a local spec dataset. "
        "General selection steps: confirm system duty point (flow/head), match voltage/phase, "
        "check fluid/temperature limits, and follow manufacturer installation guidance."
    )


@app.post("/api/lookup")
async def api_lookup(payload: LookupRequest):
    query = (payload.query or "").strip()
    manufacturer, prodname = parse_natural_query(query)
    looks_like_question = is_question(query)

    if not manufacturer:
        return JSONResponse(
            {
                "manufacturer": "",
                "prodname": prodname,
                "is_question": looks_like_question,
                "web_result": {"FLOWNOM56": "unknown", "HEADNOM56": "unknown", "PHASE": "unknown"},
                "local_result": {"FLOWNOM56": "unknown", "HEADNOM56": "unknown", "PHASE": "unknown"},
                "hybrid_comparison": None,
                "error": "Could not detect manufacturer from query.",
            }
        )

    hybrid = lookup_pump_hybrid(manufacturer, prodname, force_web=True)
    web_result = hybrid.get("web_result", {})
    local_result = hybrid.get("local_result", {})
    hybrid_comparison = hybrid.get("hybrid_comparison", None)

    return JSONResponse(
        {
            "manufacturer": manufacturer,
            "prodname": prodname,
            "is_question": looks_like_question,
            "web_result": web_result,
            "local_result": local_result,
            "hybrid_comparison": hybrid_comparison,
        }
    )


@app.get("/api/lookup")
async def api_lookup_get(q: str = ""):
    query = (q or "").strip()
    manufacturer, prodname = parse_natural_query(query)
    looks_like_question = is_question(query)

    if not manufacturer:
        return JSONResponse(
            {
                "manufacturer": "",
                "prodname": prodname,
                "is_question": looks_like_question,
                "web_result": {"FLOWNOM56": "unknown", "HEADNOM56": "unknown", "PHASE": "unknown"},
                "local_result": {"FLOWNOM56": "unknown", "HEADNOM56": "unknown", "PHASE": "unknown"},
                "hybrid_comparison": None,
                "error": "Could not detect manufacturer from query.",
            }
        )

    hybrid = lookup_pump_hybrid(manufacturer, prodname, force_web=True)
    web_result = hybrid.get("web_result", {})
    local_result = hybrid.get("local_result", {})
    hybrid_comparison = hybrid.get("hybrid_comparison", None)

    return JSONResponse(
        {
            "manufacturer": manufacturer,
            "prodname": prodname,
            "is_question": looks_like_question,
            "web_result": web_result,
            "local_result": local_result,
            "hybrid_comparison": hybrid_comparison,
        }
    )


@app.post("/api/ask")
async def api_ask(payload: AskRequest):
    text = (payload.text or "").strip()
    manufacturer = (payload.manufacturer or "").strip()
    prodname = (payload.prodname or "").strip()
    question = (payload.question or "").strip()

    if text and (not manufacturer or not prodname):
        manufacturer, prodname = parse_natural_query(text)
        question = question or text

    ai_answer = None
    if manufacturer and prodname and question and is_question(question):
        ai_answer = answer_about_pump(manufacturer, prodname, question)
        if not ai_answer:
            ai_answer = _fallback_ai_answer(manufacturer, prodname, question)

    return JSONResponse({"ai_answer": ai_answer, "manufacturer": manufacturer, "prodname": prodname})


@app.get("/api/ask")
async def api_ask_get(q: str = ""):
    text = (q or "").strip()
    manufacturer, prodname = parse_natural_query(text)
    ai_answer = None
    if manufacturer and prodname and text and is_question(text):
        ai_answer = answer_about_pump(manufacturer, prodname, text)
        if not ai_answer:
            ai_answer = _fallback_ai_answer(manufacturer, prodname, text)
    return JSONResponse({"ai_answer": ai_answer, "manufacturer": manufacturer, "prodname": prodname})


frontend_dir = Path(__file__).resolve().parent / "frontend"
main_page = frontend_dir / "main_page.html"
index_page = frontend_dir / "index.html"

if main_page.exists() and not index_page.exists():
    main_page.rename(index_page)
app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
