"""Stable normalized parser interface shared by local and AWS adapters."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ParsedMeasurement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skeletal_site: str
    region: str
    side: str | None = None
    bmd_g_cm2: float
    t_score: float
    z_score: float | None = None
    extraction_confidence: float = Field(ge=0, le=1)
    source_page: int = Field(ge=1)
    source_text: str
    usable_for_longitudinal: bool = True


class ParsedReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scan_date: date
    report_type: str = "DXA_BMD"
    facility_pseudonym: str
    scanner_manufacturer: str
    scanner_model: str
    parser_name: str
    parser_version: str
    extraction_confidence: float = Field(ge=0, le=1)
    review_required: bool
    measurements: list[ParsedMeasurement] = Field(min_length=1)
    sanitized_evidence: str
    prompt_injection_detected: bool = False
    active_markup_detected: bool = False
    phi_findings: list[str] = Field(default_factory=list)
