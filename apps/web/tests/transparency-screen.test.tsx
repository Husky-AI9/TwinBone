import type { Timeline, Transparency } from "@bonetwin/shared-types";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { TransparencyScreen } from "../components/product-app";

const hostedTransparency: Transparency = {
  mode: "AWS",
  database: {
    service: "CockroachDB Cloud",
    role: "Durable system of record",
  },
  document_pipeline: [
    { step: "Storage", service: "Amazon S3 with AWS KMS encryption" },
    { step: "Workflow", service: "AWS Lambda Function URL" },
  ],
  memory_engine: [
    { step: "Embedding", service: "Amazon Bedrock Titan Embeddings" },
    { step: "MCP gate", service: "LangChain MCP retrieval" },
  ],
  agent: {
    runtime: "Amazon Bedrock Converse",
    output: "Strict validated JSON",
  },
  audit_event_count: 23,
  safety_boundary: "Document organization only",
};

const timeline: Timeline = {
  subject: {
    id: "30000000-0000-4000-8000-000000000001",
    pseudonym: "DEMO-001",
    year_of_birth: 1965,
    status: "ACTIVE",
    report_count: 1,
    open_task_count: 0,
    latest_scan_date: "2026-08-16",
  },
  reports: [
    {
      id: "41000000-0000-4000-8000-000000000001",
      document_id: "42000000-0000-4000-8000-000000000001",
      scan_date: "2026-08-16",
      report_type: "DXA_BMD",
      facility_pseudonym: "Demo facility",
      scanner_manufacturer: "GE Healthcare",
      scanner_model: "Lunar iDXA",
      parser_name: "bonetwin",
      parser_version: "1",
      extraction_confidence: 0.98,
      review_required: false,
      measurements: [],
    },
  ],
  memories: [],
  tasks: [],
  treatment_events: [],
};

describe("runtime transparency panel", () => {
  it("describes the active hosted AWS integrations", () => {
    const markup = renderToStaticMarkup(
      <TransparencyScreen data={hostedTransparency} />,
    );

    expect(markup).toContain("What is running in this demo");
    expect(markup).toContain(">AWS<");
    expect(markup).toContain("AWS Lambda");
    expect(markup).toContain("Amazon S3");
    expect(markup).toContain("Amazon Bedrock");
    expect(markup).toContain("CockroachDB Cloud");
    expect(markup).not.toContain("LOCAL MOCK");
  });

  it("does not infer local mock mode when the API is unavailable", () => {
    const markup = renderToStaticMarkup(<TransparencyScreen data={null} />);

    expect(markup).toContain("STATUS UNAVAILABLE");
    expect(markup).toContain("API could not be reached");
    expect(markup).toContain("Audit count unavailable");
    expect(markup).not.toContain("LOCAL MOCK");
    expect(markup).not.toContain("deterministic offline adapters");
    expect(markup).not.toContain("0 structured API audit events");
  });

  it("lists individually deletable demo records only after they are loaded", () => {
    const unloaded = renderToStaticMarkup(
      <TransparencyScreen data={hostedTransparency} />,
    );
    const loaded = renderToStaticMarkup(
      <TransparencyScreen data={hostedTransparency} timeline={timeline} />,
    );

    expect(unloaded).toContain("Load report records");
    expect(unloaded).not.toContain("Delete record");
    expect(loaded).toContain("August 16, 2026");
    expect(loaded).toContain("GE Healthcare");
    expect(loaded).toContain("Delete record");
    expect(loaded).toContain("audit tombstone");
  });
});
