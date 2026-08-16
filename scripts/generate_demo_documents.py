"""Generate deterministic, visibly synthetic DXA PDFs for local upload testing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen.canvas import Canvas

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIRECTORY = ROOT / "output" / "pdf"


@dataclass(frozen=True, slots=True)
class Measurement:
    label: str
    bmd: float
    t_score: float
    z_score: float
    confidence: float
    longitudinal: bool


@dataclass(frozen=True, slots=True)
class DemoReport:
    year: int
    scan_date: str
    facility: str
    manufacturer: str
    model: str
    measurements: tuple[Measurement, ...]
    note: str


REPORTS = (
    DemoReport(
        year=2019,
        scan_date="2019-05-03",
        facility="Synthetic Imaging Center A",
        manufacturer="Hologic",
        model="Discovery A (synthetic)",
        measurements=(
            Measurement("Left Total Hip", 0.781, -1.3, -0.2, 0.99, True),
            Measurement("Left Femoral Neck", 0.701, -1.5, -0.3, 0.97, True),
            Measurement("Lumbar Spine L1-L4", 0.838, -1.8, -0.6, 0.94, True),
        ),
        note="Baseline synthetic study. Preserve source values for later review.",
    ),
    DemoReport(
        year=2022,
        scan_date="2022-06-08",
        facility="Synthetic Imaging Center A",
        manufacturer="Hologic",
        model="Discovery A (synthetic)",
        measurements=(
            Measurement("Left Total Hip", 0.756, -1.5, -0.4, 0.99, True),
            Measurement("Left Femoral Neck", 0.683, -1.6, -0.5, 0.96, True),
            Measurement("Lumbar Spine L1-L4", 0.822, -2.0, -0.8, 0.78, False),
        ),
        note="Synthetic positioning artifact flagged at the lumbar site for human review.",
    ),
    DemoReport(
        year=2026,
        scan_date="2026-04-12",
        facility="Synthetic Imaging Center B",
        manufacturer="Hologic",
        model="Horizon A (synthetic)",
        measurements=(
            Measurement("Left Total Hip", 0.742, -1.6, -0.4, 0.98, True),
            Measurement("Left Femoral Neck", 0.668, -1.7, -0.5, 0.88, True),
            Measurement("Lumbar Spine L1-L4", 0.811, -2.1, -0.8, 0.97, False),
        ),
        note="Scanner metadata differs from the prior synthetic study; clinician review requested.",
    ),
)


def _text(canvas: Canvas, x: float, y: float, value: str, *, size: int = 9) -> None:
    canvas.setFont("Helvetica", size)
    canvas.setFillColor(HexColor("#334155"))
    canvas.drawString(x, y, value)


def generate_report(report: DemoReport, destination: Path) -> None:
    canvas = Canvas(str(destination), pagesize=letter, invariant=1, pageCompression=1)
    width, height = letter
    teal = HexColor("#123d3a")
    pale_teal = HexColor("#e8f4f1")
    red = HexColor("#9f1239")
    slate = HexColor("#475569")

    canvas.setFillColor(teal)
    canvas.rect(0, height - 92, width, 92, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.setFont("Helvetica-Bold", 22)
    canvas.drawString(44, height - 48, "Bone Density (DXA) Report")
    canvas.setFont("Helvetica", 9)
    canvas.drawString(44, height - 68, "BONETWIN SYNTHETIC DXA")

    canvas.setFillColor(HexColor("#fff1f2"))
    canvas.roundRect(44, height - 128, width - 88, 25, 5, fill=1, stroke=0)
    canvas.setFillColor(red)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawCentredString(
        width / 2,
        height - 119,
        "SYNTHETIC DEMO - NOT A MEDICAL RECORD",
    )

    metadata_y = height - 163
    canvas.setFillColor(slate)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(44, metadata_y, "Study details")
    _text(canvas, 44, metadata_y - 22, "Subject pseudonym: SYNTH-BONE-001")
    _text(canvas, 44, metadata_y - 39, f"Scan date: {report.scan_date}")
    _text(canvas, 44, metadata_y - 56, f"Facility: {report.facility}")
    _text(canvas, 310, metadata_y - 22, f"Scanner manufacturer: {report.manufacturer}")
    _text(canvas, 310, metadata_y - 39, f"Scanner model: {report.model}")
    _text(canvas, 310, metadata_y - 56, "Report type: DXA BMD")

    table_top = height - 262
    canvas.setFillColor(pale_teal)
    canvas.roundRect(44, table_top - 24, width - 88, 25, 5, fill=1, stroke=0)
    headings = (("Site", 52), ("BMD g/cm2", 252), ("T-score", 340), ("Z-score", 410), ("Use", 485))
    canvas.setFillColor(teal)
    canvas.setFont("Helvetica-Bold", 9)
    for label, x in headings:
        canvas.drawString(x, table_top - 15, label)

    row_y = table_top - 50
    for measurement in report.measurements:
        canvas.setFillColor(HexColor("#e2e8f0"))
        canvas.line(44, row_y - 8, width - 44, row_y - 8)
        _text(canvas, 52, row_y, measurement.label, size=9)
        _text(canvas, 252, row_y, f"{measurement.bmd:.3f}", size=9)
        _text(canvas, 340, row_y, f"{measurement.t_score:.1f}", size=9)
        _text(canvas, 410, row_y, f"{measurement.z_score:.1f}", size=9)
        _text(canvas, 485, row_y, "YES" if measurement.longitudinal else "REVIEW", size=9)
        row_y -= 34

    canvas.setFillColor(slate)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(44, row_y - 10, "Source evidence text")
    evidence_y = row_y - 30
    for measurement in report.measurements:
        evidence = (
            f"{measurement.label} BMD {measurement.bmd:.3f} g/cm2; "
            f"T-score {measurement.t_score:.1f}; Z-score {measurement.z_score:.1f}; "
            f"Confidence {measurement.confidence:.2f}; "
            f"Longitudinal {'YES' if measurement.longitudinal else 'NO'}"
        )
        _text(canvas, 52, evidence_y, evidence, size=7)
        evidence_y -= 16

    canvas.setFillColor(HexColor("#f8fafc"))
    canvas.roundRect(44, evidence_y - 56, width - 88, 50, 6, fill=1, stroke=0)
    canvas.setFillColor(slate)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(54, evidence_y - 23, "Review note")
    canvas.setFont("Helvetica", 8)
    canvas.drawString(54, evidence_y - 40, report.note)

    canvas.setFillColor(HexColor("#64748b"))
    canvas.setFont("Helvetica", 7)
    canvas.drawString(
        44,
        36,
        "Generated solely for BoneTwin local software testing. Contains no real person "
        "or clinical interpretation.",
    )
    canvas.drawRightString(width - 44, 36, f"Demo report {report.year} - page 1 of 1")
    canvas.save()


def main() -> int:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for report in REPORTS:
        path = OUTPUT_DIRECTORY / f"bonetwin-demo-dxa-{report.year}.pdf"
        generate_report(report, path)
        print(f"Generated {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
