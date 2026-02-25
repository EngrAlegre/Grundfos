from src.query_builder import build_queries, rank_sources
from src.search import search_for_pump
from src.fetcher import fetch_page
from src.extractor import extract_fields
from src.normalizer import normalize_result
from src.pump_dictionary import get_from_db, save_to_db

TARGET_KEYS = ["FLOWNOM56", "HEADNOM56", "PHASE"]


def lookup_pump(manufacturer: str, prodname: str, force_web: bool = False) -> dict:
    # 1. Check Local Dictionary (if we are NOT forcing web)
    if not force_web:
        cached_result = get_from_db(manufacturer, prodname)
        if cached_result:
            return cached_result

    # 2. Perform Web Search
    queries = build_queries(manufacturer, prodname)
    raw_results = search_for_pump(queries)
    ranked = rank_sources(raw_results, manufacturer)

    snippet_text = _combine_snippets(ranked)
    best = {"FLOWNOM56": "unknown", "HEADNOM56": "unknown", "PHASE": "unknown", "DESCRIPTION": ""}

    if snippet_text:
        fields = extract_fields(snippet_text, manufacturer, prodname)
        best = _merge(best, fields)
        if _is_complete(best):
            return _finalize_and_store(best, manufacturer, prodname)

    for source in ranked[:2]:
        text = fetch_page(source["link"])
        if not text or len(text) < 100:
            continue
        fields = extract_fields(text, manufacturer, prodname)
        best = _merge(best, fields)
        if _is_complete(best):
            break

    # 3. Finalize and Return
    # If force_web is True, we do NOT fall back to local DB here.
    # We return exactly what the web found (even if it is 'unknown').
    # This ensures the "Web" column is truly from the web.
    return _finalize_and_store(best, manufacturer, prodname)


def _finalize_and_store(result: dict, manufacturer: str, prodname: str) -> dict:
    result = normalize_result(result)
    result["MANUFACTURER"] = manufacturer
    result["PRODNAME"] = prodname
    
    # Mark as web search result
    result["_source"] = "web_search"
    
    # Save to our local dictionary for next time
    #save_to_db(manufacturer, prodname, result)
    
    return result


def _is_complete(result: dict) -> bool:
    return all(result.get(k) != "unknown" for k in TARGET_KEYS)


def _merge(current: dict, new: dict) -> dict:
    merged = dict(current)
    
    # 1. Merge standard target keys
    for k in TARGET_KEYS:
        if merged.get(k) == "unknown" and new.get(k) != "unknown":
            merged[k] = new[k]
            
    # 2. Merge Description (if we don't have one yet, take the new one)
    # We prefer a description over "unknown", so we take the first valid one we find.
    if not merged.get("DESCRIPTION") and new.get("DESCRIPTION"):
        merged["DESCRIPTION"] = new["DESCRIPTION"]
        
    return merged


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