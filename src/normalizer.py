import re


def normalize_phase(val) -> int | str:
    if val == "unknown":
        return "unknown"
    s = str(val).strip()
    if s in ("1", "1.0"):
        return 1
    if s in ("3", "3.0"):
        return 3
    if re.match(r"1[/-]3|3[/-]1", s):
        return 3
    try:
        v = int(float(s))
        if v in (1, 3):
            return v
    except (ValueError, TypeError):
        pass
    return "unknown"


def normalize_numeric(val, field: str) -> float | str:
    if val == "unknown" or val is None:
        return "unknown"
    try:
        v = float(val)
    except (ValueError, TypeError):
        cleaned = re.sub(r"[^\d.\-]", "", str(val))
        try:
            v = float(cleaned)
        except (ValueError, TypeError):
            return "unknown"
    if v <= 0:
        return "unknown"
    if field == "FLOWNOM56" and v > 200:
        return "unknown"
    if field == "HEADNOM56" and v > 100:
        return "unknown"
    return round(v, 2)


def normalize_result(result: dict) -> dict:
    return {
        "FLOWNOM56": normalize_numeric(result.get("FLOWNOM56", "unknown"), "FLOWNOM56"),
        "HEADNOM56": normalize_numeric(result.get("HEADNOM56", "unknown"), "HEADNOM56"),
        "PHASE": normalize_phase(result.get("PHASE", "unknown")),
    }
