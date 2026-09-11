"""Дістає текст (з прив'язкою до місця — сторінка/аркуш/абзац) з матеріалів,
які скидає інвестор: PDF, DOCX, XLSX, звичайний текст, посилання, зображення.

Кожен екстрактор повертає список (location, text) — location іде в цитату
відповіді ("Джерело: файл.pdf, стор. 4"), тому для QA важливо ділити текст
на не надто великі шматки.
"""
import re

CHUNK_SIZE = 1500


def chunk_text(text, size=CHUNK_SIZE):
    text = text.strip()
    if not text:
        return []
    return [text[i:i + size].strip() for i in range(0, len(text), size) if text[i:i + size].strip()]


def extract_pdf(data):
    from pypdf import PdfReader

    reader = PdfReader(io_bytes(data))
    chunks = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            chunks.append((f"стор. {i}", text))
    return chunks


def extract_docx(data):
    from docx import Document

    doc = Document(io_bytes(data))
    full_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    parts = chunk_text(full_text)
    return [(f"частина {i}" if len(parts) > 1 else "текст документа", part) for i, part in enumerate(parts, start=1)]


def extract_xlsx(data):
    from openpyxl import load_workbook

    wb = load_workbook(io_bytes(data), data_only=True, read_only=True)
    chunks = []
    for sheet in wb.worksheets:
        lines = []
        for row in sheet.iter_rows():
            cells = [
                f"{cell.coordinate}={cell.value}"
                for cell in row
                if cell.value is not None and str(cell.value).strip() != ""
            ]
            if cells:
                lines.append(" | ".join(cells))
        if not lines:
            continue
        text = "\n".join(lines)
        # Ріжемо великий аркуш на блоки рядків, щоб цитата лишалась точною.
        rows_per_block = 40
        row_lines = text.split("\n")
        for start in range(0, len(row_lines), rows_per_block):
            block = "\n".join(row_lines[start:start + rows_per_block])
            end = min(start + rows_per_block, len(row_lines))
            chunks.append((f"аркуш «{sheet.title}», рядки {start + 1}-{end}", block))
    return chunks


def extract_txt(data):
    text = data.decode("utf-8", errors="ignore")
    parts = chunk_text(text)
    return [(f"частина {i}" if len(parts) > 1 else "текст", part) for i, part in enumerate(parts, start=1)]


def extract_url(url, timeout=15):
    """Повертає (title, [(location, text), ...])."""
    import requests
    from bs4 import BeautifulSoup

    resp = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": "Mozilla/5.0 (compatible; InvestorBot/1.0)"},
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    title = (soup.title.string.strip() if soup.title and soup.title.string else url)
    text = re.sub(r"\n{3,}", "\n\n", soup.get_text("\n"))
    text = "\n".join(line.strip() for line in text.split("\n") if line.strip())
    parts = chunk_text(text, size=2000)
    chunks = [(f"розділ {i}" if len(parts) > 1 else "сторінка", part) for i, part in enumerate(parts, start=1)]
    return title, chunks


def describe_image(data, mime_type, filename):
    """Через Claude vision дає короткий опис зображення (рендер, планування,
    скрін переписки тощо), щоб його можна було знайти в пошуку по проекту."""
    import claude_client

    system = (
        "Ти аналітик інвестиційної нерухомості. Опиши коротко (3-6 речень) "
        "українською, що на зображенні: тип (рендер, планування, скріншот, "
        "фото об'єкта, графік тощо) і всі конкретні цифри/факти, які видно "
        "(площі, ціни, ставки, терміни, адреси)."
    )
    return claude_client.ask_with_image(system, f"Файл: {filename}", data, mime_type)


def io_bytes(data):
    import io

    return io.BytesIO(data)


EXTENSION_ROUTES = {
    ".pdf": extract_pdf,
    ".docx": extract_docx,
    ".xlsx": extract_xlsx,
    ".xlsm": extract_xlsx,
    ".txt": extract_txt,
    ".csv": extract_txt,
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def extract_file(filename, data):
    """Роутер за розширенням. Повертає (kind, [(location, text), ...]) або
    (None, []) якщо формат не підтримується текстовим аналізом (тоді файл
    все одно завантажується в Drive, просто без пошуку по вмісту)."""
    lower = filename.lower()
    for ext, fn in EXTENSION_ROUTES.items():
        if lower.endswith(ext):
            return "file", fn(data)
    return None, []
