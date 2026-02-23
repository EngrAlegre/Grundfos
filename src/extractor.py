import json
import re
import requests
from src.config import OLLAMA_BASE_URL, OLLAMA_MODEL

EXTRACTION_PROMPT = """You are a pump data extractor. Given the text below, extract values for pump: {manufacturer} {prodname}

Text:
{text}

Extract these fields from the text. Report the RAW numbers exactly as stated — do NOT convert units:
- flow: the flow rate number and its unit (GPM, m3/h, L/s, L/min). Prefer nominal/rated flow over maximum.
- head: the head number and its unit (ft, m, kPa). Prefer nominal/rated head over maximum.
- flow_is_max: true if the flow is labeled "max" or "maximum", false if nominal/rated
- head_is_max: true if the head is labeled "max" or "maximum", false if nominal/rated
- phase: 1 or 3. Single-phase / 115V / 120V / 230V = 1. Three-phase / 400V / 460V = 3.
- If a value cannot be found, use "unknown".

Return ONLY JSON:
{{"flow": <number>, "flow_unit": "<unit>", "flow_is_max": <true/false>, "head": <number>, "head_unit": "<unit>", "head_is_max": <true/false>, "phase": <number>}}"""

FLOW_CONVERSIONS = {"gpm": 0.2271, "m3/h": 1.0, "l/s": 3.6, "l/min": 0.06}
HEAD_CONVERSIONS = {"ft": 0.3048, "feet": 0.3048, "m": 1.0, "kpa": 0.10197}

NOMINAL_FLOW_RATIO = 0.55
NOMINAL_HEAD_RATIO = 0.70


def extract_fields(text: str, manufacturer: str, prodname: str) -> dict:
    prompt = EXTRACTION_PROMPT.format(
        manufacturer=manufacturer, prodname=prodname, text=text[:3000]
    )
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "options": {"temperature": 0}},
            timeout=180,
        )
        resp.raise_for_status()
        raw = resp.json().get("response", "")
        parsed = _parse_llm_json(raw)
        return _convert_to_target(parsed)
    except Exception as e:
        return {"FLOWNOM56": "unknown", "HEADNOM56": "unknown", "PHASE": "unknown", "_error": str(e)}


def _convert_to_target(parsed: dict) -> dict:
    result = {}

    flow_val = parsed.get("flow", "unknown")
    flow_unit = str(parsed.get("flow_unit", "")).lower().strip()
    flow_is_max = parsed.get("flow_is_max", True)
    if flow_val != "unknown":
        try:
            flow_num = float(flow_val)
            factor = FLOW_CONVERSIONS.get(flow_unit, None)
            if factor is None:
                for key, f in FLOW_CONVERSIONS.items():
                    if key in flow_unit:
                        factor = f
                        break
            if factor:
                flow_m3h = flow_num * factor
                flow_m3h *= NOMINAL_FLOW_RATIO
                result["FLOWNOM56"] = round(flow_m3h, 1)
            else:
                result["FLOWNOM56"] = "unknown"
        except (ValueError, TypeError):
            result["FLOWNOM56"] = "unknown"
    else:
        result["FLOWNOM56"] = "unknown"

    head_val = parsed.get("head", "unknown")
    head_unit = str(parsed.get("head_unit", "")).lower().strip()
    head_is_max = parsed.get("head_is_max", True)
    if head_val != "unknown":
        try:
            head_num = float(head_val)
            factor = HEAD_CONVERSIONS.get(head_unit, None)
            if factor is None:
                for key, f in HEAD_CONVERSIONS.items():
                    if key in head_unit:
                        factor = f
                        break
            if factor:
                head_m = head_num * factor
                head_m *= NOMINAL_HEAD_RATIO
                result["HEADNOM56"] = round(head_m, 1)
            else:
                result["HEADNOM56"] = "unknown"
        except (ValueError, TypeError):
            result["HEADNOM56"] = "unknown"
    else:
        result["HEADNOM56"] = "unknown"

    phase = parsed.get("phase", "unknown")
    if phase != "unknown":
        try:
            result["PHASE"] = int(phase)
        except (ValueError, TypeError):
            result["PHASE"] = "unknown"
    else:
        result["PHASE"] = "unknown"

    return result


def _eval_math_expr(s: str):
    s = s.strip()
    match = re.match(r"^([\d.]+)\s*\*\s*([\d.]+)$", s)
    if match:
        return float(match.group(1)) * float(match.group(2))
    try:
        return float(s)
    except (ValueError, TypeError):
        return s


def _parse_llm_json(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {}

    json_str = match.group()
    json_str = re.sub(
        r":\s*([\d.]+\s*\*\s*[\d.]+)",
        lambda m: f": {_eval_math_expr(m.group(1))}",
        json_str,
    )

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return {}
