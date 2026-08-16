import { describe, expect, it, vi } from "vitest";

import { uploadLocalSyntheticReport } from "../lib/server-upload";

const documentResponse = {
  id: "40000000-0000-4000-8000-000000000099",
  subject_id: "30000000-0000-4000-8000-000000000001",
  status: "READY",
  original_filename: "selected.pdf",
  content_type: "application/pdf",
  byte_size: 11,
  sha256: "0".repeat(64),
  progress: 100,
  status_message: "Parsed report is ready",
  report: null,
  failure_code: null,
  failure_message: null,
  created_at: "2026-08-02T00:00:00Z",
};

describe("no-JavaScript upload fallback", () => {
  it("forwards selected bytes through the authenticated idempotent API workflow", async () => {
    const request = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            document_id: documentResponse.id,
            upload_url: `/v1/local-uploads/${documentResponse.id}`,
            duplicate: false,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ ...documentResponse, status: "UPLOADED" }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(documentResponse), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    const file = new File(["%PDF-form"], "selected.pdf", {
      type: "application/pdf",
    });

    const result = await uploadLocalSyntheticReport(file, {
      baseUrl: "http://api.test",
      idempotencyKey: "form-upload-test",
      fetchImplementation: request,
    });

    expect(result.status).toBe("READY");
    expect(request).toHaveBeenCalledTimes(3);
    for (const [, init] of request.mock.calls) {
      const headers = new Headers(init?.headers);
      expect(headers.get("Authorization")).toBe("Bearer demo-clinician");
      expect(headers.get("Idempotency-Key")).toBeTruthy();
    }
  });

  it("keeps API credentials off a direct signed S3 upload", async () => {
    const signedUrl =
      "https://synthetic-bucket.s3.us-west-2.amazonaws.com/object?X-Amz-Signature=test";
    const request = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            document_id: documentResponse.id,
            upload_url: signedUrl,
            upload_headers: {
              "Content-Type": "application/pdf",
              "x-amz-server-side-encryption": "aws:kms",
            },
            duplicate: false,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(new Response(null, { status: 200 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify(documentResponse), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    const file = new File(["%PDF-form"], "selected.pdf", {
      type: "application/pdf",
    });

    await uploadLocalSyntheticReport(file, {
      baseUrl: "http://api.test",
      idempotencyKey: "form-s3-upload-test",
      fetchImplementation: request,
    });

    expect(request.mock.calls[1]?.[0]).toBe(signedUrl);
    const headers = new Headers(request.mock.calls[1]?.[1]?.headers);
    expect(headers.get("x-amz-server-side-encryption")).toBe("aws:kms");
    expect(headers.has("Authorization")).toBe(false);
    expect(headers.has("Idempotency-Key")).toBe(false);
  });

  it("removes the word from fallback API errors before display", async () => {
    const request = vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({ detail: "Synthetic reports are unavailable" }),
          { status: 503, headers: { "Content-Type": "application/json" } },
        ),
      );
    const file = new File(["%PDF-form"], "selected.pdf", {
      type: "application/pdf",
    });

    await expect(
      uploadLocalSyntheticReport(file, {
        baseUrl: "http://api.test",
        idempotencyKey: "form-error-test",
        fetchImplementation: request,
      }),
    ).rejects.toThrow("reports are unavailable");
  });
});
