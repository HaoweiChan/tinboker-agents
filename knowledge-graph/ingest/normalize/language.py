try:
    import langdetect
except ImportError:
    langdetect = None


def detect_language(text: str) -> str | None:
    if langdetect is None:
        return None

    try:
        return langdetect.detect(text)
    except Exception:
        return None


def filter_by_language(docs: list, target_language: str = "en") -> list:
    if langdetect is None:
        return docs

    filtered = []
    for doc in docs:
        text = f"{doc.title} {doc.text}"
        lang = detect_language(text)
        if lang == target_language:
            filtered.append(doc)

    return filtered

