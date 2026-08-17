import { ApiError, BoneTwinClient } from "@bonetwin/api-client";
import { afterEach, describe, expect, it, vi } from "vitest";

const readyDocument = {
  id: "40000000-0000-4000-8000-000000000001",
  subject_id: "30000000-0000-4000-8000-000000000001",
  status: "READY",
  original_filename: "bonetwin-demo-dxa-2026.pdf",
  content_type: "application/pdf",
  byte_size: 12,
  sha256: "0".repeat(64),
  progress: 100,
  status_message: "Parsed report is ready",
  report: null,
  failure_code: null,
  failure_message: null,
  processing_events: [
    {
      id: "backend-cockroach-commit",
      service: "CockroachDB Cloud",
      operation: "Serializable evidence commit",
      status: "COMPLETED" as const,
      detail: "Stored report evidence atomically.",
    },
  ],
  created_at: "2026-08-02T00:00:00Z",
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("browser upload flow", () => {
  it("retries transient Lambda throttling for read-only requests", async () => {
    const request = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ message: "Rate Exceeded" }), {
          status: 429,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            subject: {},
            reports: [],
            memories: [],
            tasks: [],
            treatment_events: [],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    vi.stubGlobal("fetch", request);
    const client = new BoneTwinClient({
      baseUrl: "http://api.test",
      retryDelayMs: 0,
    });

    const timeline = await client.timeline(readyDocument.subject_id);

    expect(timeline.reports).toEqual([]);
    expect(request).toHaveBeenCalledTimes(2);
  });

  it("does not automatically retry a state-changing request", async () => {
    const request = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ message: "Rate Exceeded" }), {
        status: 429,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", request);
    const client = new BoneTwinClient({
      baseUrl: "http://api.test",
      retryDelayMs: 0,
    });

    await expect(
      client.runComparison(readyDocument.subject_id),
    ).rejects.toEqual(new ApiError("Rate Exceeded", 429));
    expect(request).toHaveBeenCalledTimes(1);
  });

  it("downloads an actual generated PDF instead of substituting preview data", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          new Blob(["%PDF-synthetic"], { type: "application/pdf" }),
          {
            status: 200,
          },
        ),
      ),
    );

    const client = new BoneTwinClient({ baseUrl: "http://api.test" });
    const file = await client.demoDocument("2026-08-16");

    expect(file.name).toBe("bonetwin-demo-dxa-2026-08-16.pdf");
    expect(file.type).toBe("application/pdf");
    expect(file.size).toBeGreaterThan(0);
    expect(fetch).toHaveBeenCalledWith(
      "http://api.test/demo-documents/bonetwin-demo-dxa-2026-08-16.pdf",
    );
  });

  it("sends selected bytes through intent, upload, and completion requests", async () => {
    const request = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            document_id: readyDocument.id,
            upload_url: `/v1/local-uploads/${readyDocument.id}`,
            duplicate: false,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ...readyDocument, status: "UPLOADED" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            ...readyDocument,
            status_message: "Synthetic report is ready",
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        ),
      );
    vi.stubGlobal("fetch", request);
    const client = new BoneTwinClient({ baseUrl: "http://api.test" });
    const file = new File(["%PDF-upload"], readyDocument.original_filename, {
      type: "application/pdf",
    });
    const progress = vi.fn();

    const result = await client.uploadDocument(
      readyDocument.subject_id,
      file,
      progress,
    );

    expect(result.status).toBe("READY");
    expect(result.status_message).toBe("report is ready");
    expect(request).toHaveBeenCalledTimes(3);
    expect(request.mock.calls[0]?.[0]).toContain("/documents/upload-intent");
    expect(request.mock.calls[1]?.[0]).toContain("/v1/local-uploads/");
    expect(request.mock.calls[2]?.[0]).toContain("/complete-upload");
    expect(progress).toHaveBeenCalledWith(
      expect.objectContaining({
        id: "backend-cockroach-commit",
        service: "CockroachDB Cloud",
      }),
    );
    for (const [, init] of request.mock.calls) {
      const headers = new Headers(init?.headers);
      expect(headers.get("Authorization")).toBe("Bearer demo-clinician");
      expect(headers.get("Idempotency-Key")).toBeTruthy();
    }
  });

  it("uploads to a signed S3 URL without leaking app authentication", async () => {
    const signedUrl =
      "https://synthetic-bucket.s3.us-west-2.amazonaws.com/object?X-Amz-Signature=test";
    const request = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            document_id: readyDocument.id,
            upload_url: signedUrl,
            upload_headers: {
              "Content-Type": "application/pdf",
              "x-amz-checksum-sha256": "signed-checksum",
              "x-amz-server-side-encryption": "aws:kms",
            },
            duplicate: false,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(new Response(null, { status: 200 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify(readyDocument), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", request);
    const client = new BoneTwinClient({ baseUrl: "http://api.test" });
    const file = new File(["%PDF-upload"], readyDocument.original_filename, {
      type: "application/pdf",
    });

    await client.uploadDocument(readyDocument.subject_id, file);

    expect(request.mock.calls[1]?.[0]).toBe(signedUrl);
    const uploadHeaders = new Headers(request.mock.calls[1]?.[1]?.headers);
    expect(uploadHeaders.get("x-amz-checksum-sha256")).toBe("signed-checksum");
    expect(uploadHeaders.get("x-amz-server-side-encryption")).toBe("aws:kms");
    expect(uploadHeaders.has("Authorization")).toBe(false);
    expect(uploadHeaders.has("Idempotency-Key")).toBe(false);
  });
});
