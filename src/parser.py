from bs4 import BeautifulSoup


def parse_html(html: str, max_chars: int = 4000) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return "\n".join(lines)[:max_chars]


def parse_pdf_bytes(content: bytes, max_chars: int = 4000) -> str | None:
    try:
        import pdfplumber, io

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
        return "\n".join(texts)[:max_chars]
    except Exception:
        return None
