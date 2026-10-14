"""Reference-compatible paragraph boundaries, without changing spoken words (v1 passages.py)."""
import re

PARSER = "reference-paragraphs-v1"


def spans(text):
    start = 0
    for separator in re.finditer(r"\n\s*\n", text):
        if text[start:separator.start()].strip():
            yield start, separator.start()
        start = separator.end()
    if text[start:].strip():
        yield start, len(text)


def paragraphs(text):
    return {f"P{i:03d}": text[a:b].strip() for i, (a, b) in enumerate(spans(text), 1)}
