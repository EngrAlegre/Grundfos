from src.config import MANUFACTURER_DOMAINS


def build_queries(manufacturer: str, prodname: str) -> list[str]:
    queries = [
        f'"{manufacturer} {prodname}" pump specifications flow head',
        f'"{manufacturer} {prodname}" datasheet PDF',
        f'{manufacturer} {prodname} pump GPM feet head',
        f'"{prodname}" pump specifications nominal flow',
        f'{manufacturer} {prodname} technical data circulator',
    ]
    return queries


def rank_sources(results: list[dict], manufacturer: str) -> list[dict]:
    mfr_domains = MANUFACTURER_DOMAINS.get(manufacturer, [])
    from src.config import DISTRIBUTOR_DOMAINS

    def score(r):
        link = r.get("link", "").lower()
        snippet = r.get("snippet", "").lower()
        base = 0.3
        for d in mfr_domains:
            if d in link:
                base = 1.0
                break
        for d in DISTRIBUTOR_DOMAINS:
            if d in link:
                base = max(base, 0.7)
                break
        if any(kw in snippet for kw in ["gpm", "flow", "head", "m3/h", "feet", "ft"]):
            base += 0.2
        return base

    for r in results:
        r["_tier_score"] = score(r)
    results.sort(key=lambda r: r["_tier_score"], reverse=True)
    return results
