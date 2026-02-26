import json
import re
from openai import OpenAI
from src.config import PERPLEXITY_API_KEY, PERPLEXITY_MODEL

SYSTEM_PROMPT = """You are a pump specification lookup tool. When given a pump manufacturer and model, search for its technical specs.

Return the RAW values you find, along with their units and whether they are MAX or NOMINAL values.
Do NOT do any unit conversion or nominal estimation yourself — just report what you find.

Search terms to try:
- Flow: "flow rate", "capacity", "max flow", "GPM", "volume flow", "Q", "m³/h"
- Head: "head", "max head", "total head", "feet of head", "H", "shut-off head"
- Phase: voltage, phase, electrical data

Search strategy:
- Try the exact model first, then variations (e.g., "1634B" -> "1634-B", "1634 series")
- Look at manufacturer catalog PDFs, spec sheets, product pages
- Check pump curve data if available

Return ONLY a JSON object with these fields:
{
  "flow_value": <number or "unknown">,
  "flow_unit": "GPM" | "m3/h" | "L/min" | "L/s" | "unknown",
  "flow_type": "max" | "nominal" | "rated" | "unknown",
  "head_value": <number or "unknown">,
  "head_unit": "feet" | "meters" | "PSI" | "kPa" | "unknown",
  "head_type": "max" | "nominal" | "rated" | "unknown",
  "phase": <1 or 3 or "unknown">
}

Rules:
- Report the EXACT numbers and units from the source. Do NOT convert.
- For flow_type/head_type: "max" if labeled max/maximum, "nominal" or "rated" if labeled nominal/rated/duty/design point, "unknown" if unclear.
- 115V/120V/208V/230V = phase 1. 400V/460V/575V = phase 3.
- Return ONLY the JSON, no other text."""

USER_PROMPT = """Find the pump specifications for: {manufacturer} {prodname}

Return ONLY the JSON with raw values, units, and types."""

QA_SYSTEM_PROMPT = """You are a pump expert. Given a pump brand and model, answer the user's question \
in clear, practical language (3-5 sentences). Focus on:
- What the pump is designed for (e.g., hydronic heating, domestic hot water recirculation, chilled water).
- Typical applications and systems where it is used.
- Notable features (materials, motor type, speed settings, etc.).

You may reference the known specs provided as context, but do NOT invent specific numbers. \
If you don't know, say so honestly. Keep it concise and useful for an engineer evaluating the pump."""

QA_USER_PROMPT = """Pump: {manufacturer} {prodname}
Known specs: Flow = {flow} m³/h, Head = {head} m, Phase = {phase}

User question: {question}"""


def extract_via_perplexity(manufacturer: str, prodname: str) -> dict:
    if not PERPLEXITY_API_KEY:
        raise RuntimeError("PERPLEXITY_API_KEY env var must be set")

    client = OpenAI(
        api_key=PERPLEXITY_API_KEY,
        base_url="https://api.perplexity.ai",
    )

    response = client.chat.completions.create(
        model=PERPLEXITY_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT.format(manufacturer=manufacturer, prodname=prodname)},
        ],
    )

    raw = response.choices[0].message.content
    parsed = _parse_raw_response(raw)
    return _convert_to_nominal_metric(parsed)


def _parse_raw_response(raw: str) -> dict:
    text = (raw or "").strip()
    if not text:
        return {}

    # 1) Best case: hassistant already returned pure JSON.
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # 2) Common case: JSON is wrapped in ```json ... ``` fences.
    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, re.IGNORECASE)
    if fenced:
        try:
            obj = json.loads(fenced.group(1))
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

    # 3) Fallback: try each JSON-looking object and pick one with expected keys.
    expected_keys = {"flow_value", "flow_unit", "flow_type", "head_value", "head_unit", "head_type", "phase"}
    for candidate in re.findall(r"\{[\s\S]*?\}", text):
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict) and expected_keys.intersection(obj.keys()):
                return obj
        except json.JSONDecodeError:
            continue
    return {}


def _convert_to_nominal_metric(data: dict) -> dict:
    flow = _convert_flow(data)
    head = _convert_head(data)
    phase = data.get("phase", "unknown")
    if phase not in (1, 3):
        try:
            phase = int(phase)
            if phase not in (1, 3):
                phase = "unknown"
        except (ValueError, TypeError):
            phase = "unknown"
    return {"FLOWNOM56": flow, "HEADNOM56": head, "PHASE": phase}


FLOW_CONVERSIONS = {
    "gpm": 0.2271,
    "l/min": 1 / 16.67,
    "l/s": 3.6,
    "m3/h": 1.0,
    "m³/h": 1.0,
}

HEAD_CONVERSIONS = {
    "feet": 0.3048,
    "ft": 0.3048,
    "psi": 0.703,
    "kpa": 1 / 9.81,
    "meters": 1.0,
    "m": 1.0,
}

NOMINAL_FACTOR_FLOW = 0.55
NOMINAL_FACTOR_HEAD = 0.70

DATASET_MAX_FLOW = 93.0
DATASET_MAX_HEAD = 19.8


def _convert_flow(data: dict):
    val = data.get("flow_value", "unknown")
    if val == "unknown" or val is None:
        return "unknown"
    try:
        v = float(val)
    except (ValueError, TypeError):
        return "unknown"
    if v <= 0:
        return "unknown"

    unit = str(data.get("flow_unit", "unknown")).lower().strip()
    factor = FLOW_CONVERSIONS.get(unit)
    if factor is None:
        if v > 100:
            factor = 0.2271
        else:
            factor = 1.0
    v_metric = v * factor

    flow_type = str(data.get("flow_type", "unknown")).lower().strip()
    if flow_type == "max":
        v_metric *= NOMINAL_FACTOR_FLOW
    elif flow_type == "nominal":
        pass
    elif v_metric > DATASET_MAX_FLOW:
        v_metric *= NOMINAL_FACTOR_FLOW

    if v_metric > 200:
        return "unknown"

    return round(v_metric, 1)


def _convert_head(data: dict):
    val = data.get("head_value", "unknown")
    if val == "unknown" or val is None:
        return "unknown"
    try:
        v = float(val)
    except (ValueError, TypeError):
        return "unknown"
    if v <= 0:
        return "unknown"

    unit = str(data.get("head_unit", "unknown")).lower().strip()
    factor = HEAD_CONVERSIONS.get(unit)
    if factor is None:
        if v > 30:
            factor = 0.3048
        else:
            factor = 1.0
    v_metric = v * factor

    head_type = str(data.get("head_type", "unknown")).lower().strip()
    if head_type == "max":
        v_metric *= NOMINAL_FACTOR_HEAD
    elif head_type == "nominal":
        pass
    elif v_metric > DATASET_MAX_HEAD:
        v_metric *= NOMINAL_FACTOR_HEAD

    if v_metric > 100:
        return "unknown"

    return round(v_metric, 1)


def answer_pump_question(
    manufacturer: str,
    prodname: str,
    question: str,
    flow: str = "unknown",
    head: str = "unknown",
    phase: str = "unknown",
) -> str:
    """Ask Perplexity a free-form question about a specific pump."""
    if not PERPLEXITY_API_KEY:
        raise RuntimeError("PERPLEXITY_API_KEY env var must be set")

    client = OpenAI(
        api_key=PERPLEXITY_API_KEY,
        base_url="https://api.perplexity.ai",
    )

    response = client.chat.completions.create(
        model=PERPLEXITY_MODEL,
        messages=[
            {"role": "system", "content": QA_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": QA_USER_PROMPT.format(
                    manufacturer=manufacturer,
                    prodname=prodname,
                    flow=flow,
                    head=head,
                    phase=phase,
                    question=question,
                ),
            },
        ],
    )
    text = response.choices[0].message.content.strip()
    text = re.sub(r"\[\d+\]", "", text)
    # Strip common markdown emphasis that shows up in answers (**, *, _, `)
    text = re.sub(r"[*_`]+", "", text)
    return text.strip()
