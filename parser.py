import io
import pymupdf
from docx import Document

def extract_text(file_bytes, extension):
    ext = extension.lower()
    if ext == ".pdf":
        return pdf(file_bytes)
    elif ext == ".docx":
        return docx(file_bytes)
    elif ext == ".txt":
        return txt(file_bytes)
    return ""

def pdf(file_bytes):
    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text.strip()

def docx(file_bytes):
    doc = Document(io.BytesIO(file_bytes))
    paragraphs = []
    for paragraph in doc.paragraphs:
        text = paragraph.text
        if text.strip():
            paragraphs.append(text)
    return "\n".join(paragraphs)

def txt(file_bytes):
    for enc in ("utf-8", "latin-1"):
        try:
            return file_bytes.decode(enc).strip()
        except UnicodeDecodeError:
            continue
    return ""