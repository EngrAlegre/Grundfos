from serpapi import GoogleSearch
from src.config import SERPAPI_KEY, MAX_SOURCES_PER_PUMP


def google_search(query: str, num_results: int = 5) -> list[dict]:
    if not SERPAPI_KEY:
        raise RuntimeError("SERPAPI_KEY env var must be set")

    params = {
        "q": query,
        "api_key": SERPAPI_KEY,
        "engine": "google",
        "num": num_results,
    }
    search = GoogleSearch(params)
    data = search.get_dict()

    organic = data.get("organic_results", [])
    results = []
    for r in organic:
        rich_text = _extract_rich_text(r)
        results.append({
            "title": r.get("title", ""),
            "link": r.get("link", ""),
            "snippet": r.get("snippet", ""),
            "rich_text": rich_text,
        })

    return results


def _extract_rich_text(result: dict) -> str:
    parts = []
    if result.get("title"):
        parts.append(result["title"])
    if result.get("snippet"):
        parts.append(result["snippet"])
    rich = result.get("rich_snippet", {})
    if isinstance(rich, dict):
        top = rich.get("top", {})
        if isinstance(top, dict):
            for k, v in top.items():
                if isinstance(v, str):
                    parts.append(f"{k}: {v}")
                elif isinstance(v, list):
                    parts.extend(str(i) for i in v)
        bottom = rich.get("bottom", {})
        if isinstance(bottom, dict):
            for k, v in bottom.items():
                if isinstance(v, str):
                    parts.append(f"{k}: {v}")
    table = result.get("table", [])
    if isinstance(table, list):
        for row in table:
            if isinstance(row, dict):
                parts.append(" | ".join(f"{k}: {v}" for k, v in row.items()))
            elif isinstance(row, list):
                parts.append(" | ".join(str(c) for c in row))
    about = result.get("about_this_result", {})
    if isinstance(about, dict) and about.get("description"):
        parts.append(about["description"])
    return "\n".join(parts)


def search_for_pump(queries: list[str], max_total: int = MAX_SOURCES_PER_PUMP) -> list[dict]:
    seen_links = set()
    all_results = []
    for q in queries:
        try:
            results = google_search(q, num_results=5)
        except Exception:
            continue
        for r in results:
            if r["link"] not in seen_links:
                seen_links.add(r["link"])
                all_results.append(r)
            if len(all_results) >= max_total:
                return all_results
    return all_results
