# NeuralFlow - Pump Researcher Agent

AI-powered agent that searches the web and retrieves pump specifications (nominal flow, head, electrical phase) given a manufacturer and product name.

## How It Works

1. **Search** - Queries SerpAPI (Google) with multiple search variants for the target pump
2. **Fetch** - Downloads and parses HTML pages and PDF datasheets from top-ranked sources
3. **Extract** - Uses Mistral 7B (local LLM via Ollama) to extract structured data from unstructured text
4. **Normalize** - Converts units (GPM to m3/h, feet to meters) and applies nominal correction factors
5. **Output** - Returns JSON with FLOWNOM56, HEADNOM56, and PHASE

## Tools & Technologies

| Layer | Tool | Purpose |
|---|---|---|
| Language | Python 3.12 | Core runtime |
| Web Search | SerpAPI (Google Search) | Find pump spec pages online |
| LLM | Mistral 7B via Ollama | Extract structured data from text |
| Web Scraping | Requests + BeautifulSoup | Fetch and parse HTML pages |
| PDF Parsing | pdfplumber | Extract text/tables from datasheets |
| Data Processing | Pandas + openpyxl | Load/profile Excel dataset |
| Evaluation | scikit-learn | Train/val split, metrics |
| Web UI | Streamlit | NeuralFlow browser interface |
| Config | python-dotenv | Environment variable management |