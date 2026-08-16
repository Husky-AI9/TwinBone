from pathlib import Path

import pytest

from services.ingestion.parser import PARSER_NAME, PARSER_VERSION, parse_synthetic_dxa


def test_synthetic_parser_normalizes_and_preserves_provenance() -> None:
    fixture = (
        Path(__file__).resolve().parents[1] / "fixtures" / "synthetic-dxa-2026.txt"
    ).read_text(encoding="utf-8")
    report = parse_synthetic_dxa(fixture)
    assert report.parser_name == PARSER_NAME
    assert report.parser_version == PARSER_VERSION
    assert len(report.measurements) == 3
    lumbar = next(item for item in report.measurements if item.skeletal_site == "SPINE")
    assert lumbar.usable_for_longitudinal is False
    assert lumbar.source_page == 1


def test_parser_refuses_unapproved_or_failed_fixture() -> None:
    with pytest.raises(ValueError, match="approved"):
        parse_synthetic_dxa("not a fixture")
    with pytest.raises(ValueError, match="failure"):
        parse_synthetic_dxa(
            "BONETWIN SYNTHETIC DXA\nSYNTHETIC DEMO - NOT A MEDICAL RECORD\nFAIL_PARSE"
        )
