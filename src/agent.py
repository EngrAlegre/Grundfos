from src.perplexity import extract_via_perplexity, answer_pump_question
from src.normalizer import normalize_result
from src.pump_dictionary import get_from_db
import src.pump_dictionary as pump_dictionary
import math
import sys
import difflib

TARGET_KEYS = ["FLOWNOM56", "HEADNOM56", "PHASE"]

MAX_DEVIATION = 0.50


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _confidence_label(score: float) -> str:
    if score >= 0.85:
        return "high"
    if score >= 0.60:
        return "medium"
    return "low"


def _numeric_similarity(a, b) -> float:
    """Return a similarity score in [0,1] for two numeric‑like values."""
    af = _safe_float(a)
    bf = _safe_float(b)
    if af is None or bf is None:
        return 1.0 if str(a).strip().lower() == str(b).strip().lower() else 0.0
    if bf == 0:
        return 1.0 if af == 0 else 0.0
    pct_delta = abs(af - bf) / abs(bf)
    if pct_delta >= 1.0:
        return 0.0
    return max(0.0, 1.0 - pct_delta)


def _pump_similarity(web_result: dict, local_result: dict) -> float:
    """
    Compute a simple similarity score between web result and one local pump.
    Used for retrieval quality metrics (not for production ranking).
    """
    weights = {"FLOWNOM56": 0.4, "HEADNOM56": 0.4, "PHASE": 0.2}
    total = 0.0
    weight_sum = 0.0

    for key, w in weights.items():
        web_val = web_result.get(key, "unknown")
        local_val = local_result.get(key, "unknown")
        if key in ("FLOWNOM56", "HEADNOM56"):
            sim = _numeric_similarity(web_val, local_val)
        else:
            sim = 1.0 if str(web_val).strip().lower() == str(local_val).strip().lower() else 0.0
        total += sim * w
        weight_sum += w

    return total / weight_sum if weight_sum else 0.0


def _name_similarity(query_prod: str, candidate_prod: str) -> float:
    """
    String similarity between the queried product name and a local product name.
    Used as a secondary signal for ranking, especially when specs are missing.
    """
    q = str(query_prod or "").upper().strip()
    c = str(candidate_prod or "").upper().strip()
    if not q or not c:
        return 0.0
    return difflib.SequenceMatcher(None, q, c).ratio()


def _top_k_local_candidates(manufacturer: str, k: int = 5) -> list[dict]:
    """
    Very simple retrieval over the local JSON 'DB':
    filter by manufacturer and return all candidates.
    Retrieval ranking is applied later.
    """
    manu_norm = str(manufacturer).strip().upper()
    get_all = getattr(pump_dictionary, "get_all_pumps", None)
    if get_all is None:
        return []

    candidates = []
    for row in get_all():
        if str(row.get("MANUFACTURER", "")).strip().upper() != manu_norm:
            continue
        candidates.append(row)

    return candidates

def _build_hybrid_comparison(web_result: dict, local_result: dict | None) -> dict:
    """Build trust/confidence metadata for web results using local DB as anchor."""
    comparison = {
        "mode": "hybrid_web_local",
        "fields": {},
        "summary": {"high": 0, "medium": 0, "low": 0, "no_local_reference": False},
        "overall_confidence": 0.0,
        "overall_label": "low",
    }
    field_weights = {"FLOWNOM56": 0.4, "HEADNOM56": 0.4, "PHASE": 0.2}
    weighted_total = 0.0
    weight_sum = 0.0

    if not local_result:
        comparison["summary"]["no_local_reference"] = True
        for key in TARGET_KEYS:
            w = web_result.get(key, "unknown")
            if w != "unknown":
                confidence = 0.45
                reason = "No local reference found; confidence based on web-only extraction."
            else:
                confidence = 0.15
                reason = "No local reference and web result is unknown."
            label = _confidence_label(confidence)
            comparison["summary"][label] += 1
            comparison["fields"][key] = {
                "confidence": round(confidence, 3),
                "confidence_label": label,
                "reason": reason,
            }
            weighted_total += confidence * field_weights.get(key, 0.0)
            weight_sum += field_weights.get(key, 0.0)
        comparison["overall_confidence"] = round(weighted_total / weight_sum, 3) if weight_sum else 0.0
        comparison["overall_label"] = _confidence_label(comparison["overall_confidence"])
        return comparison

    for key in TARGET_KEYS:
        w = web_result.get(key, "unknown")
        l = local_result.get(key, "unknown")
        confidence = 0.20
        reason = "Insufficient evidence."

        if w == "unknown" and l == "unknown":
            confidence = 0.10
            reason = "Both web and local are unknown."
        elif w == "unknown":
            confidence = 0.15
            reason = "Web value missing while local has data."
        elif l == "unknown":
            confidence = 0.45
            reason = "No local value for this field; web-only confidence."
        elif key in ("FLOWNOM56", "HEADNOM56"):
            wf = _safe_float(w)
            lf = _safe_float(l)
            if wf is None or lf is None:
                if str(w).strip().lower() == str(l).strip().lower():
                    confidence = 0.80
                    reason = "Values match textually."
                else:
                    confidence = 0.30
                    reason = "Non-numeric mismatch between web and local."
            else:
                if lf == 0:
                    pct_delta = 0.0 if wf == 0 else 1.0
                else:
                    pct_delta = abs(wf - lf) / abs(lf)

                if pct_delta <= MAX_DEVIATION:
                    ratio = pct_delta / MAX_DEVIATION if MAX_DEVIATION > 0 else 1.0
                    confidence = 0.95 - (0.45 * ratio)
                    reason = f"Numeric delta is within tolerance ({pct_delta:.1%} vs {MAX_DEVIATION:.0%} max)."
                else:
                    overflow = min((pct_delta - MAX_DEVIATION) / MAX_DEVIATION, 1.0) if MAX_DEVIATION > 0 else 1.0
                    confidence = 0.50 - (0.30 * overflow)
                    reason = f"Numeric delta exceeds tolerance ({pct_delta:.1%} vs {MAX_DEVIATION:.0%} max)."
        else:
            if str(w).strip().lower() == str(l).strip().lower():
                confidence = 0.95
                reason = "Categorical field matches local data."
            else:
                confidence = 0.25
                reason = "Categorical mismatch against local data."

        confidence = max(0.0, min(confidence, 1.0))
        label = _confidence_label(confidence)
        comparison["summary"][label] += 1
        comparison["fields"][key] = {"confidence": round(confidence, 3), "confidence_label": label, "reason": reason}
        weighted_total += confidence * field_weights.get(key, 0.0)
        weight_sum += field_weights.get(key, 0.0)

    comparison["overall_confidence"] = round(weighted_total / weight_sum, 3) if weight_sum else 0.0
    comparison["overall_label"] = _confidence_label(comparison["overall_confidence"])

    return comparison

    
def evaluate_retrieval_metric(manufacturer: str, prodname: str, k: int = 5) -> dict:
    """
    RAG‑style retrieval validation:
    - get 1 web result for the pump
    - retrieve up to k close candidates from local JSON DB
    - compute similarity scores and derive a confidence / accuracy percentage
    """
    web_result = lookup_pump(manufacturer, prodname, force_web=True)
    local_candidates = _top_k_local_candidates(manufacturer, k=k)

    scored_candidates: list[dict] = []

    # Detect if web specs are mostly missing; then lean more on name similarity
    web_flow_unknown = web_result.get("FLOWNOM56", "unknown") in (None, "", "unknown")
    web_head_unknown = web_result.get("HEADNOM56", "unknown") in (None, "", "unknown")

    best_score = 0.0

    for cand in local_candidates:
        spec_score = _pump_similarity(web_result, cand)
        name_score = _name_similarity(prodname, cand.get("PRODNAME", ""))

        if web_flow_unknown and web_head_unknown:
            final_score = 0.3 * spec_score + 0.7 * name_score
        else:
            final_score = 0.7 * spec_score + 0.3 * name_score

        best_score = max(best_score, final_score)
        scored_candidates.append(
            {
                "MANUFACTURER": cand.get("MANUFACTURER"),
                "PRODNAME": cand.get("PRODNAME"),
                "FLOWNOM56": cand.get("FLOWNOM56"),
                "HEADNOM56": cand.get("HEADNOM56"),
                "PHASE": cand.get("PHASE"),
                "similarity": round(final_score, 3),
                "spec_similarity": round(spec_score, 3),
                "name_similarity": round(name_score, 3),
            }
        )

    # Rank by final similarity so that #1 is the most similar
    scored_candidates.sort(key=lambda c: c["similarity"], reverse=True)

    # Ground-truth: exact manufacturer+prodname exists in local JSON.
    true_local = get_from_db(manufacturer, prodname)
    true_key = None
    if true_local:
        true_key = (
            str(true_local.get("MANUFACTURER", "")).strip().upper(),
            str(true_local.get("PRODNAME", "")).strip().upper(),
        )

    rank_of_true_local = None
    if true_key:
        for i, row in enumerate(scored_candidates):
            cand_key = (
                str(row.get("MANUFACTURER", "")).strip().upper(),
                str(row.get("PRODNAME", "")).strip().upper(),
            )
            if cand_key == true_key:
                rank_of_true_local = i
                break

    hit_at_k = None
    mrr = None
    ndcg_at_k = None

    if rank_of_true_local is not None:
        k_eff = k if (k is not None and k > 0) else len(scored_candidates)
        hit_at_k = 1.0 if rank_of_true_local < k_eff else 0.0
        mrr = 1.0 / float(rank_of_true_local + 1)

        # Binary relevance nDCG@k: only the true item is relevant.
        if rank_of_true_local < k_eff:
            dcg = 1.0 / math.log2(float(rank_of_true_local + 2))
        else:
            dcg = 0.0
        idcg = 1.0 / math.log2(2.0)
        ndcg_at_k = dcg / idcg if idcg else 0.0

    # This is a validation threshold flag, not a real accuracy metric.
    passes_threshold = bool(best_score >= 0.8)

    # Keep only top-k rows for display/validation.
    if k is not None and k > 0:
        scored_candidates = scored_candidates[:k]

    return {
        "manufacturer": manufacturer,
        "prodname": prodname,
        "k": k,
        "web_result": web_result,
        "candidates": scored_candidates,
        "best_similarity": round(best_score, 3),
        "confidence_pct": round(best_score * 100.0, 1),
        "passes_threshold": passes_threshold,
        "rank_of_true_local": rank_of_true_local,
        "hit_at_k": hit_at_k,
        "mrr": mrr,
        "ndcg_at_k": ndcg_at_k,
    }


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

    result["MANUFACTURER"] = manufacturer
    result["PRODNAME"] = prodname
    result["_source"] = "web_search"
    return result


def lookup_pump_hybrid(manufacturer: str, prodname: str, force_web: bool = True) -> dict:
    """
    Hybrid retrieval: fetch web, compare against local JSON DB, and return comparison metadata.
    """
    local_result = get_from_db(manufacturer, prodname)
    web_result = lookup_pump(manufacturer, prodname, force_web=force_web)

    comparison = _build_hybrid_comparison(web_result, local_result)

    return {
        "MANUFACTURER": manufacturer,
        "PRODNAME": prodname,
        "web_result": web_result,
        "local_result": local_result or {"FLOWNOM56": "unknown", "HEADNOM56": "unknown", "PHASE": "unknown"},
        "hybrid_comparison": comparison,
    }


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


if __name__ == "__main__":
    """
    Example CLI usage:
        python -m src.agent "Grundfos" "MAGNA1 25-80"
    Prints retrieval confidence / accuracy metrics for this pump.
    """
    if len(sys.argv) < 3:
        print("Usage: python -m src.agent <MANUFACTURER> <PRODNAME>")
        sys.exit(1)

    manufacturer_arg = sys.argv[1]
    prodname_arg = " ".join(sys.argv[2:])

    metrics = evaluate_retrieval_metric(manufacturer_arg, prodname_arg, k=5)
    print(f"Retrieval metric for {manufacturer_arg} / {prodname_arg}")
    print(f"- Best similarity: {metrics['best_similarity']:.3f}")
    print(f"- Confidence: {metrics['confidence_pct']:.1f}%")
    print(f"- Passes threshold (0.8): {int(metrics['passes_threshold'])}")
