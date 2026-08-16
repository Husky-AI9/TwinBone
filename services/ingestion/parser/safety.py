"""Sanitize untrusted report evidence before prompting or embedding."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

ACTIVE_MARKUP = re.compile(r"<[^>]+>|javascript:|data:text/html", re.IGNORECASE)
INSTRUCTION_ATTACKS = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior|system)\s+instructions?", re.IGNORECASE),
    re.compile(r"(reveal|print|return)\s+(the\s+)?system\s+prompt", re.IGNORECASE),
    re.compile(r"(call|execute|invoke|run)\s+(a\s+)?tool", re.IGNORECASE),
    re.compile(r"(insert|update|delete|drop)\s+(into|from|table|database)", re.IGNORECASE),
)
UNTRUSTED_MARKER = "[UNTRUSTED INSTRUCTION REDACTED]"


@dataclass(frozen=True, slots=True)
class SanitizedEvidence:
    text: str
    prompt_injection_detected: bool
    active_markup_detected: bool
    finding_count: int


def sanitize_untrusted_evidence(value: str) -> SanitizedEvidence:
    """Remove active markup and instruction attacks from downstream model context.

    The original source remains append-only in its evidence record. This sanitized copy is
    the only version eligible for prompt context or embedding.
    """
    normalized = html.unescape(value).replace("\x00", "")
    active_markup_detected = bool(ACTIVE_MARKUP.search(normalized))
    sanitized = ACTIVE_MARKUP.sub(" ", normalized)
    findings = 0
    for pattern in INSTRUCTION_ATTACKS:
        sanitized, count = pattern.subn(UNTRUSTED_MARKER, sanitized)
        findings += count
    sanitized = " ".join(sanitized.split())
    return SanitizedEvidence(
        text=sanitized,
        prompt_injection_detected=findings > 0,
        active_markup_detected=active_markup_detected,
        finding_count=findings + int(active_markup_detected),
    )
