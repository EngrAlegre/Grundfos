from src.perplexity import extract_via_perplexity, answer_pump_question
from src.normalizer import normalize_result
from src.pump_dictionary import get_from_db

TARGET_KEYS = ["FLOWNOM56", "HEADNOM56", "PHASE"]

MAX_DEVIATION = 0.50


def _refine_with_local(web_result: dict, local_result: dict) -> dict:
    """Use local DB as anchor: backfill unknowns and clamp outliers to ±MAX_DEVIATION."""
    for key in ("FLOWNOM56", "HEADNOM56"):
        w = web_result.get(key)
        l = local_result.get(key)
        if l in (None, "unknown"):
            continue
        try:
            lf = float(l)
        except (ValueError, TypeError):
            continue
        if lf <= 0:
            continue

        if w == "unknown":
            web_result[key] = round(lf, 1)
            continue

        try:
            wf = float(w)
        except (ValueError, TypeError):
            web_result[key] = round(lf, 1)
            continue

        lo = lf * (1 - MAX_DEVIATION)
        hi = lf * (1 + MAX_DEVIATION)
        if wf < lo:
            web_result[key] = round(lo, 1)
        elif wf > hi:
            web_result[key] = round(hi, 1)
    return web_result


def lookup_pump(manufacturer: str, prodname: str, force_web: bool = False) -> dict:
    if not force_web:
        cached_result = get_from_db(manufacturer, prodname)
        if cached_result:
            return cached_result

    try:
        fields = extract_via_perplexity(manufacturer, prodname)
    except Exception as e:
        fields = {"FLOWNOM56": "unknown", "HEADNOM56": "unknown", "PHASE": "unknown", "_error": str(e)}

    result = normalize_result(fields)

    local = get_from_db(manufacturer, prodname)
    if local:
        if result.get("PHASE") == "unknown" and local.get("PHASE") not in (None, "unknown"):
            result["PHASE"] = local["PHASE"]
        result = _refine_with_local(result, local)

    result["MANUFACTURER"] = manufacturer
    result["PRODNAME"] = prodname
    result["_source"] = "web_search"
    return result


def answer_about_pump(manufacturer: str, prodname: str, question: str) -> str | None:
    """Ask a free-form question about a pump, using local DB specs as context."""
    local = get_from_db(manufacturer, prodname)
    flow = str(local.get("FLOWNOM56", "unknown")) if local else "unknown"
    head = str(local.get("HEADNOM56", "unknown")) if local else "unknown"
    phase = str(local.get("PHASE", "unknown")) if local else "unknown"

    try:
        return answer_pump_question(manufacturer, prodname, question, flow, head, phase)
    except Exception:
        return None
