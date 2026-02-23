from src.query_builder import build_queries, rank_sources
from src.search import search_for_pump
from src.fetcher import fetch_page
from src.extractor import extract_fields
from src.normalizer import normalize_result

TARGET_KEYS = ["FLOWNOM56", "HEADNOM56", "PHASE"]


def lookup_pump(manufacturer: str, prodname: str) -> dict:
    queries = build_queries(manufacturer, prodname)
    raw_results = search_for_pump(queries)
    ranked = rank_sources(raw_results, manufacturer)

    snippet_text = _combine_snippets(ranked)
    best = {"FLOWNOM56": "unknown", "HEADNOM56": "unknown", "PHASE": "unknown"}

    if snippet_text:
        fields = extract_fields(snippet_text, manufacturer, prodname)
        best = _merge(best, fields)
        if _is_complete(best):
            return _finalize(best, manufacturer, prodname)

    for source in ranked[:2]:
        text = fetch_page(source["link"])
        if not text or len(text) < 100:
            continue
        fields = extract_fields(text, manufacturer, prodname)
        best = _merge(best, fields)
        if _is_complete(best):
            break

    return _finalize(best, manufacturer, prodname)


def _is_complete(result: dict) -> bool:
    return all(result.get(k) != "unknown" for k in TARGET_KEYS)


def _merge(current: dict, new: dict) -> dict:
    merged = dict(current)
    for k in TARGET_KEYS:
        if merged.get(k) == "unknown" and new.get(k) != "unknown":
            merged[k] = new[k]
    return merged


def _finalize(result: dict, manufacturer: str, prodname: str) -> dict:
    result = normalize_result(result)
    result["MANUFACTURER"] = manufacturer
    result["PRODNAME"] = prodname
    return result


def _combine_snippets(results: list[dict]) -> str:
    parts = []
    for r in results:
        rich = r.get("rich_text", "")
        if rich:
            parts.append(rich)
        elif r.get("snippet"):
            parts.append(f"{r['title']}\n{r['snippet']}")
    combined = "\n---\n".join(parts)
    combined = combined.replace("\u00b7", ":").replace(" ; ", "\n").replace(" \u00b7 ", ": ")
    return combined[:4000] if combined else ""
