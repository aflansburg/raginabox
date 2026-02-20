import pymupdf


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file. Raises ValueError if no text found."""
    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    pages = []
    for page in doc:
        text = page.get_text()
        if text.strip():
            pages.append(text.strip())
    doc.close()

    if not pages:
        raise ValueError("PDF contains no extractable text (may be scanned/image-only)")

    return "\n\n".join(pages)
