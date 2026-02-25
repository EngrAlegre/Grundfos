# Challenge 2: Pump Researcher Agent — Notes & Ideas (So far)

## Competition details (from prompt/slides)
### Objective
Develop an agent that can search the web and retrieve a number of pre-defined data points for a specific pump, given the brand and model/variant or product number. [file:18]

### Dataset task (ground truth format)
Given **`MANUFACTURER`** and **`PRODNAME`**, find/predict the following target fields:
- **`FLOWNOM56`**
- **`HEADNOM56`**
- **`PHASE`** [file:18]

Fields that **can be ignored**:
- `PUMP_DESIGN`
- `PORTPORT` [file:18]

### Dataset file
`Replacement_pumps.xlsx` contains (at least) these columns:
`MANUFACTURER, FLOWNOM56, HEADNOM56, PHASE, PORTPORT, PRODNAME, PUMPDESIGN` [file:17]

---

## What the dataset implies
- The dataset already includes the “correct answers” for `FLOWNOM56`, `HEADNOM56`, `PHASE`, which makes it usable for **validation/testing** of your system (compare your agent’s extracted values vs. labels). [file:17][file:18]
- Because the final evaluation may include unseen pumps, the agent should not rely only on lookup; it should be able to **retrieve specs from the web** and generalize. [file:18]

---

## Proposed architecture (Retrieval + Extraction)
### 1) API/UI layer (input/output)
Input examples:
- `{ manufacturer, model_variant }`
- `{ product_number }` (if provided in test) [file:18]

Output:
- Structured JSON (fields required by the challenge) plus optional metadata like confidence and sources. [file:18]

### 2) Orchestrator (agent controller)
Responsibilities:
- Plan steps: search → choose sources → parse → extract → normalize → validate → output.
- Retry with alternate queries if missing fields or low confidence. [file:18]

### 3) Retrieval layer (web search)
Components:
- **Query builder**: generate several web queries using `MANUFACTURER` + `PRODNAME` variants (spacing, hyphens, suffixes).
- **Source ranking**: prioritize manufacturer datasheets/manual PDFs; de-prioritize random reseller pages.
- **Fetcher + cache**: download HTML/PDF, store content hash to avoid repeated work.

### 4) Parsing layer (docs → text/tables)
Components:
- HTML cleaner (strip nav/ads).
- PDF text extraction + table extraction.
- OCR fallback when PDFs are scanned images.

### 5) Extraction layer (text/tables → structured fields)
Approach:
- **Hybrid extraction**:
  - Rules/regex for common patterns.
  - LLM-based structured extraction into a strict schema when layouts vary a lot.
- Capture evidence snippets + source URLs per field for traceability.

### 6) Normalization & validation
- Unit normalization (convert to canonical units used by dataset targets).
- Range checks (values should be positive; PHASE must map to allowed categories).
- Cross-source reconciliation: if multiple sources disagree, prefer highest-authority source or take consensus.

### 7) Evaluation loop using the provided dataset
- Run the agent on each row using only inputs (`MANUFACTURER`, `PRODNAME`).
- Compare predicted outputs to labels (`FLOWNOM56`, `HEADNOM56`, `PHASE`) and compute accuracy/error metrics. [file:17][file:18]

---

## Suggested output schema (practical)
Minimum (competition-required):
```json
{
  "MANUFACTURER": "...",
  "PRODNAME": "...",
  "FLOWNOM56": ...,
  "HEADNOM56": ...,
  "PHASE": ...
}
