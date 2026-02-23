import requests
from bs4 import BeautifulSoup
from src.config import FETCH_TIMEOUT, MAX_TEXT_CHARS

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_page(url: str) -> str | None:
    try:
        resp = requests.get(url, timeout=FETCH_TIMEOUT, headers=HEADERS, allow_redirects=True)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        if "pdf" in content_type.lower():
            return _handle_pdf(resp.content)
        text = _parse_html(resp.text)
        if len(text) > 50:
            return text
        return None
    except Exception:
        return None


def _parse_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    clean = "\n".join(lines)
    return clean[:MAX_TEXT_CHARS]


def _handle_pdf(content: bytes) -> str | None:
    try:
        import pdfplumber
        import io

        pdf = pdfplumber.open(io.BytesIO(content))
        texts = []
        for page in pdf.pages[:5]:
            t = page.extract_text()
            if t:
                texts.append(t)
            for table in page.extract_tables():
                for row in table:
                    texts.append(" | ".join(str(c) for c in row if c))
        pdf.close()
        text = "\n".join(texts)[:MAX_TEXT_CHARS]
        return text if text else None
    except Exception:
        return None
