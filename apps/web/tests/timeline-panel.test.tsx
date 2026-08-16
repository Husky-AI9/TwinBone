import type { Measurement, Report, Timeline } from "@bonetwin/shared-types";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { TimelinePanel } from "../components/product-app";

function measurement(
  id: string,
  reportId: string,
  side: "LEFT" | "RIGHT",
  bmd: number,
): Measurement {
  return {
    id,
    report_id: reportId,
    skeletal_site: "HIP",
    region: "TOTAL_HIP",
    side,
    bmd_g_cm2: bmd,
    t_score: -1.3,
    z_score: null,
    confidence: 0.99,
    source_page: 1,
    source_text: `Synthetic ${side.toLowerCase()} total hip measurement`,
    usable_for_longitudinal: true,
    verification_status: "VERIFIED",
  };
}

function report(id: string, measurements: Measurement[]): Report {
  return {
    id,
    document_id: `document-${id}`,
    scan_date: "2022-06-08",
    report_type: "DXA",
    facility_pseudonym: "Synthetic Imaging Center",
    scanner_manufacturer: "Synthetic",
    scanner_model: "Demo",
    parser_name: "synthetic-test",
    parser_version: "1.0",
    extraction_confidence: 0.99,
    review_required: false,
    measurements,
  };
}

describe("longitudinal hip timeline", () => {
  it("uses unique measurement identities for same-date left hip values", () => {
    const firstReportId = "report-one";
    const secondReportId = "report-two";
    const timeline = {
      reports: [
        report(firstReportId, [
          measurement("left-one", firstReportId, "LEFT", 0.781),
          measurement("right-one", firstReportId, "RIGHT", 0.912),
        ]),
        report(secondReportId, [
          measurement("left-two", secondReportId, "LEFT", 0.756),
        ]),
      ],
      memories: [],
      tasks: [],
      treatment_events: [],
    } as unknown as Timeline;
    const consoleError = vi
      .spyOn(console, "error")
      .mockImplementation(() => undefined);

    const markup = renderToStaticMarkup(<TimelinePanel timeline={timeline} />);

    expect(consoleError).not.toHaveBeenCalled();
    expect(markup).toContain("0.781");
    expect(markup).toContain("0.756");
    expect(markup).not.toContain("0.912");
    consoleError.mockRestore();
  });
});
