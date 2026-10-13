"""Hybrid regex and optional Presidio PII scrubbing."""

import re
from typing import Any

from src.ingest.chunkers import DocumentChunk


# Baseline patterns for common PII and the assignment's custom identifiers.
# Recognize long sequences of spelled-out digits in phone numbers.
WORD_PHONE_PATTERN = re.compile(
    r"(?<!\w)(?:(?:zero|one|two|three|four|five|six|seven|eight|nine)"
    r"\s+){6,}(?:zero|one|two|three|four|five|six|seven|eight|nine)"
    r"(?!\w)",
    re.IGNORECASE,
)

PII_PATTERNS = {
    "EMAIL": re.compile(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        re.IGNORECASE,
    ),
    "PHONE": re.compile(
        r"(?<!\w)(?:\+\d{1,3}[\s().-]*)?(?:\d[\s().-]*){7,14}\d(?!\w)"
    ),
    "EMPLOYEE_ID": re.compile(
        r"\b(?:EMP-\d{4,6}|Staff\s*#\s*\d{3,6}|"
        r"[A-Z]{2,3}/\d{4}/\d{3,5}|"
        r"[A-Z]\.M\.-\d{4}-[A-Z]{2,5}-\d{3}|"
        r"Badge:\s*[A-Z]{2}\d{4,8})\b",
        re.IGNORECASE,
    ),
    "IBAN": re.compile(
        r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]){11,30}\b",
        re.IGNORECASE,
    ),
    "CARD_NUMBER": re.compile(
        r"(?:\*{4}[- ]?){3}\*{0,4}\d{4}\b"
    ),
}

OBFUSCATED_EMAIL_PATTERNS = [
    (
        re.compile(
            r"\b([A-Z0-9._%+-]+)\s*\[\s*at\s*\]\s*"
            r"([A-Z0-9.-]+)\s*\[\s*dot\s*\]\s*([A-Z]{2,})\b",
            re.IGNORECASE,
        ),
        "OBFUSCATED_EMAIL",
    ),
    (
        re.compile(
            r"\b([A-Z0-9._%+-]+)\s*@\s*([A-Z0-9.-]+)"
            r"\s*[.．]\s*([A-Z]{2,})\b",
            re.IGNORECASE,
        ),
        "OBFUSCATED_EMAIL",
    ),
    (
        re.compile(
            r"\b([A-Z0-9._%+-]+)\s*＠\s*([A-Z0-9.-]+)"
            r"\s*．\s*([A-Z]{2,})\b",
            re.IGNORECASE,
        ),
        "OBFUSCATED_EMAIL",
    ),
    (
        re.compile(
            r"\b([A-Z0-9._%+-]+)\s*\(\s*at\s*\)\s*"
            r"([A-Z0-9.-]+)\s*\(\s*dot\s*\)\s*([A-Z]{2,})\b",
            re.IGNORECASE,
        ),
        "OBFUSCATED_EMAIL",
    ),
]


def scrub_pii_regex(text: str) -> tuple[str, list[dict[str, Any]]]:
    """Scrub baseline and common obfuscated PII patterns."""
    flags: list[dict[str, Any]] = []
    scrubbed = text

    # Normalize full-width email punctuation for detection.
    # The original text is retained in the source document.
    for pattern, entity_type in OBFUSCATED_EMAIL_PATTERNS:
        def replace_obfuscated(match: re.Match) -> str:
            flags.append({
                "source": "regex",
                "entity_type": entity_type,
                "matched_text": match.group(0),
                "score": 1.0,
            })
            return f"[{entity_type}]"

        scrubbed = pattern.sub(replace_obfuscated, scrubbed)

    # Detect IBANs before phone numbers so digits inside an IBAN
    # are not incorrectly reported as a phone number.
    ordered_patterns = [
        ("IBAN", PII_PATTERNS["IBAN"]),
        ("WORD_PHONE", WORD_PHONE_PATTERN),
        *[(name, pattern) for name, pattern in PII_PATTERNS.items()
          if name != "IBAN"],
    ]

    for entity_type, pattern in ordered_patterns:
        def replace_match(match: re.Match, kind: str = entity_type) -> str:
            flags.append({
                "source": "regex",
                "entity_type": kind,
                "matched_text": match.group(0),
                "score": 1.0,
            })
            return f"[{kind}]"

        scrubbed = pattern.sub(replace_match, scrubbed)

    return scrubbed, flags


def scrub_chunks(
    chunks: list[DocumentChunk],
    use_presidio: bool = True,
) -> tuple[list[DocumentChunk], list[dict[str, Any]]]:
    """Scrub chunks using original-text offsets."""
    analyzer = None
    presidio_status = "disabled"
    if use_presidio:
        try:
            from presidio_analyzer import AnalyzerEngine
            analyzer = AnalyzerEngine()
            presidio_status = "available"
        except (ImportError, OSError, RuntimeError) as exc:
            presidio_status = f"unavailable: {type(exc).__name__}"
    scrubbed_chunks = []
    reports = []
    for chunk in chunks:
        original = chunk.text
        _, regex_flags = scrub_pii_regex(original)
        spans = []
        for flag in regex_flags:
            value = flag["matched_text"]
            position = original.find(value)
            if position >= 0:
                spans.append({
                    "start": position,
                    "end": position + len(value),
                    "entity_type": flag["entity_type"],
                    "source": "regex",
                    "score": flag["score"],
                    "matched_text": value,
                })
        if analyzer is not None:
            try:
                #results = analyzer.analyze(text=original, language="en")
                results = analyzer.analyze(
                text=original,
                language="en",
                score_threshold=0.5,
               )

                for result in results:
                    spans.append({
                        "start": result.start,
                        "end": result.end,
                        "entity_type": result.entity_type,
                        "source": "presidio",
                        "score": float(result.score),
                        "matched_text": original[result.start:result.end],
                    })
            except Exception as exc:
                presidio_status = f"error: {type(exc).__name__}"
        # Keep non-overlapping spans; prefer regex at equal starts.
        spans.sort(key=lambda s: (
            s["start"],
            s["source"] != "regex",
            -(s["end"] - s["start"]),
        ))
        selected = []
        for span in spans:
            if span["start"] < 0 or span["end"] > len(original):
                continue
            if span["start"] >= span["end"]:
                continue
            if any(span['start'] < item['end'] and
                   span['end'] > item['start'] for item in selected):
                continue
            selected.append(span)
        output = original
        for span in sorted(selected, key=lambda s: s["start"], reverse=True):
            output = output[:span["start"]] + "[" + span["entity_type"] + "]" + output[span["end"]:]
        scrubbed_chunks.append(DocumentChunk(
            text=output, metadata=dict(chunk.metadata)))
        reports.append({
            "detected_types": sorted({s["entity_type"] for s in selected}),
            "n_redactions": len(selected),
            "flags": selected,
            "presidio_status": presidio_status,
        })
    return scrubbed_chunks, reports
