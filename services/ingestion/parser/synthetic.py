"""Parser for plainly labeled, generated BoneTwin DXA demo documents."""

from __future__ import annotations

import re
from datetime import date

from services.ingestion.parser.models import ParsedMeasurement, ParsedReport
from services.ingestion.parser.safety import sanitize_untrusted_evidence

PARSER_NAME = "bonetwin-compatible-synthetic-parser"
PARSER_VERSION = "2.0.0"

FIELD_PATTERNS = {
    "scan_date": re.compile(r"^Scan date:\s*(\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE),
    "facility": re.compile(r"^Facility:\s*(.+?)\s*$", re.MULTILINE),
    "manufacturer": re.compile(r"^Scanner manufacturer:\s*(.+?)\s*$", re.MULTILINE),
    "model": re.compile(r"^Scanner model:\s*(.+?)\s*$", re.MULTILINE),
}
MEASUREMENT_PATTERN = re.compile(
    r"^(?P<label>Left Total Hip|Left Femoral Neck|Lumbar Spine L1-L4)\s+"
    r"BMD\s+(?P<bmd>\d+\.\d{3})\s+g/cm2;\s*"
    r"T-score\s+(?P<t_score>-?\d+\.\d);\s*"
    r"Z-score\s+(?P<z_score>-?\d+\.\d);\s*"
    r"Confidence\s+(?P<confidence>0\.\d{2}|1\.00);\s*"
    r"Longitudinal\s+(?P<longitudinal>YES|NO)\s*$",
    re.MULTILINE,
)
SITE_MAP = {
    "Left Total Hip": ("HIP", "TOTAL_HIP", "LEFT"),
    "Left Femoral Neck": ("HIP", "FEMORAL_NECK", "LEFT"),
    "Lumbar Spine L1-L4": ("SPINE", "L1_L4", None),
}


def _required_field(text: str, field: str) -> str:
    match = FIELD_PATTERNS[field].search(text)
    if match is None:
        raise ValueError(f"synthetic report is missing {field.replace('_', ' ')}")
    return match.group(1).strip()


def parse_synthetic_dxa(text: str) -> ParsedReport:
    """Parse a generated demo report while refusing unlabeled or malformed input."""
    normalized = "\n".join(line.strip() for line in text.splitlines())
    if (
        "BONETWIN SYNTHETIC DXA" not in normalized
        or "SYNTHETIC DEMO - NOT A MEDICAL RECORD" not in normalized
    ):
        raise ValueError("fixture is not an approved BoneTwin synthetic report")
    if "FAIL_PARSE" in normalized:
        raise ValueError("synthetic parser failure requested by fixture")

    screened = sanitize_untrusted_evidence(text)
    measurements: list[ParsedMeasurement] = []
    for match in MEASUREMENT_PATTERN.finditer(normalized):
        label = match.group("label")
        skeletal_site, region, side = SITE_MAP[label]
        measurements.append(
            ParsedMeasurement(
                skeletal_site=skeletal_site,
                region=region,
                side=side,
                bmd_g_cm2=float(match.group("bmd")),
                t_score=float(match.group("t_score")),
                z_score=float(match.group("z_score")),
                extraction_confidence=float(match.group("confidence")),
                source_page=1,
                source_text=match.group(0),
                usable_for_longitudinal=match.group("longitudinal") == "YES",
            )
        )
    if not measurements:
        raise ValueError("synthetic report contains no supported measurements")

    return ParsedReport(
        scan_date=date.fromisoformat(_required_field(normalized, "scan_date")),
        facility_pseudonym=_required_field(normalized, "facility"),
        scanner_manufacturer=_required_field(normalized, "manufacturer"),
        scanner_model=_required_field(normalized, "model"),
        parser_name=PARSER_NAME,
        parser_version=PARSER_VERSION,
        extraction_confidence=round(
            sum(item.extraction_confidence for item in measurements) / len(measurements), 2
        ),
        review_required=any(
            item.extraction_confidence < 0.9 or not item.usable_for_longitudinal
            for item in measurements
        ),
        sanitized_evidence=screened.text,
        prompt_injection_detected=screened.prompt_injection_detected,
        active_markup_detected=screened.active_markup_detected,
        phi_findings=[],
        measurements=measurements,
    )
