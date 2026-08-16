import type { Transparency } from "@bonetwin/shared-types";
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
});
