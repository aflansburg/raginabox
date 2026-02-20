def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    separators: list[str] | None = None,
) -> list[dict]:
    """Split text into overlapping chunks using recursive character splitting."""
    if separators is None:
        separators = ["\n\n", "\n", ". ", " ", ""]

    chunks = _recursive_split(text, chunk_size, separators)
    result = []
    offset = 0

    for i, chunk in enumerate(chunks):
        start = text.find(chunk[:50], max(0, offset - chunk_overlap))
        if start == -1:
            start = offset
        end = start + len(chunk)
        result.append({
            "index": i,
            "text": chunk,
            "start_char": start,
            "end_char": end,
        })
        offset = end - chunk_overlap

    return result


def _recursive_split(text: str, chunk_size: int, separators: list[str]) -> list[str]:
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    sep = separators[0] if separators else ""
    remaining_separators = separators[1:] if len(separators) > 1 else [""]

    if sep == "":
        # Hard split at chunk_size
        chunks = []
        for i in range(0, len(text), chunk_size):
            piece = text[i : i + chunk_size]
            if piece.strip():
                chunks.append(piece)
        return chunks

    parts = text.split(sep)
    chunks = []
    current = ""

    for part in parts:
        candidate = current + sep + part if current else part
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current.strip():
                chunks.append(current)
            if len(part) > chunk_size:
                chunks.extend(_recursive_split(part, chunk_size, remaining_separators))
                current = ""
            else:
                current = part

    if current.strip():
        chunks.append(current)

    return chunks
