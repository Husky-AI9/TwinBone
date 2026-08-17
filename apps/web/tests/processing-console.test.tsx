import type { DocumentStatus, ProcessingEvent } from "@bonetwin/shared-types";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ProcessingConsole, ProductApp } from "../components/product-app";

const events: ProcessingEvent[] = [
  {
    id: "bedrock",
    service: "Amazon Bedrock",
    operation: "Trusted-memory embedding",
    status: "COMPLETED",
    detail: "Generated a validated 1,024-dimensional vector.",
  },
  {
    id: "cockroach",
    service: "CockroachDB Cloud",
    operation: "Serializable evidence commit",
    status: "COMPLETED",
    detail: "Stored report evidence atomically.",
  },
];

describe("backend processing console", () => {
  it("renders actual service events in the terminal-style panel", () => {
    const markup = renderToStaticMarkup(
      <ProcessingConsole events={events} busy={false} />,
    );

    expect(markup).toContain("Backend processing trace");
    expect(markup).toContain("Amazon Bedrock");
    expect(markup).toContain("CockroachDB Cloud");
    expect(markup).toContain("Serializable evidence commit");
    expect(markup).toContain('aria-label="Backend processing events"');
    expect(markup).toContain('role="log"');
    expect(markup).toContain('tabindex="0"');
    expect(markup).toContain("h-[290px]");
    expect(markup).toContain("overflow-y-auto");
    expect(markup).not.toContain("min-h-[290px]");
    expect(markup).not.toContain("Accessible longitudinal view");
  });

  it("uses the newly completed report for the anatomical preview immediately", () => {
    const document = {
      id: "document-today",
      subject_id: "subject-1",
      status: "READY",
      original_filename: "bonetwin-demo-dxa-2026-08-16.pdf",
      content_type: "application/pdf",
      byte_size: 3000,
      sha256: "a".repeat(64),
      progress: 100,
      status_message: "Report is ready",
      report: {
        id: "report-today",
        document_id: "document-today",
        scan_date: "2026-08-16",
        report_type: "DXA_BMD",
        facility_pseudonym: "Demo Center C",
        scanner_manufacturer: "GE Healthcare",
        scanner_model: "Lunar iDXA",
        parser_name: "bonetwin-synthetic-parser",
        parser_version: "1.0",
        extraction_confidence: 0.99,
        review_required: true,
        measurements: [
          {
            id: "measurement-today",
            report_id: "report-today",
            skeletal_site: "HIP",
            region: "TOTAL_HIP",
            side: "LEFT",
            bmd_g_cm2: 0.735,
            t_score: -1.7,
            z_score: -0.5,
            confidence: 0.99,
            source_page: 1,
            source_text: "Left Total Hip BMD 0.735 g/cm2",
            usable_for_longitudinal: true,
            verification_status: "AWAITING_REVIEW",
          },
        ],
      },
      failure_code: null,
      failure_message: null,
      processing_events: events,
      created_at: "2026-08-16T12:00:00Z",
    } satisfies DocumentStatus;

    const markup = renderToStaticMarkup(
      <ProductApp initialDocument={document} uploadKey="upload-test" />,
    );

    expect(markup).toContain("0.735");
    expect(markup).toContain("-1.7");
    expect(markup).toContain("Source-backed measurement from 2026-08-16");
  });
});
