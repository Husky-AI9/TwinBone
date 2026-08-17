import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DELETE, GET, POST, PUT } from "../app/api/backend/[...path]/route";

const BACKEND_URL = "https://api.example.test/";

function context(path: string[]) {
  return { params: Promise.resolve({ path }) };
}

describe("hosted same-origin API proxy", () => {
  beforeEach(() => {
    process.env.BONETWIN_API_URL = BACKEND_URL;
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    delete process.env.BONETWIN_API_URL;
  });

  it("forwards an authenticated v1 GET without browser-only headers", async () => {
    const request = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ mode: "AWS" }), {
        status: 200,
        headers: {
          "Access-Control-Allow-Origin": "https://unexpected.example",
          "Content-Type": "application/json",
          "Set-Cookie": "secret=value",
          "X-Request-ID": "request-123",
        },
      }),
    );
    vi.stubGlobal("fetch", request);

    const response = await GET(
      new Request(
        "https://app.example.test/api/backend/v1/transparency?detail=1",
        {
          headers: {
            Accept: "application/json",
            Authorization: "Bearer demo-clinician",
            Cookie: "session=private",
            Origin: "https://app.example.test",
            "X-Not-Forwarded": "private",
          },
        },
      ),
      context(["v1", "transparency"]),
    );

    const [url, init] = request.mock.calls[0] as [URL, RequestInit];
    expect(url.toString()).toBe(
      "https://api.example.test/v1/transparency?detail=1",
    );
    const headers = new Headers(init.headers);
    expect(headers.get("authorization")).toBe("Bearer demo-clinician");
    expect(headers.get("accept")).toBe("application/json");
    expect(headers.has("cookie")).toBe(false);
    expect(headers.has("origin")).toBe(false);
    expect(headers.has("x-not-forwarded")).toBe(false);
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toContain("application/json");
    expect(response.headers.get("x-request-id")).toBe("request-123");
    expect(response.headers.has("access-control-allow-origin")).toBe(false);
    expect(response.headers.has("set-cookie")).toBe(false);
  });

  it("preserves an authenticated idempotent state-changing request", async () => {
    const request = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ document_id: "document-123" }), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", request);
    const body = JSON.stringify({ original_filename: "report.pdf" });

    const response = await POST(
      new Request(
        "https://app.example.test/api/backend/v1/subjects/subject-1/documents/upload-intent",
        {
          method: "POST",
          headers: {
            Authorization: "Bearer demo-clinician",
            "Content-Type": "application/json",
            "Idempotency-Key": "upload-test-123",
          },
          body,
        },
      ),
      context(["v1", "subjects", "subject-1", "documents", "upload-intent"]),
    );

    const [, init] = request.mock.calls[0] as [URL, RequestInit];
    expect(init.method).toBe("POST");
    expect(new TextDecoder().decode(init.body as ArrayBuffer)).toBe(body);
    const headers = new Headers(init.headers);
    expect(headers.get("authorization")).toBe("Bearer demo-clinician");
    expect(headers.get("content-type")).toBe("application/json");
    expect(headers.get("idempotency-key")).toBe("upload-test-123");
    expect(response.status).toBe(201);
    expect(await response.json()).toEqual({ document_id: "document-123" });
  });

  it("preserves approved demo PDF bytes and download headers", async () => {
    const pdf = new Uint8Array([37, 80, 68, 70, 45, 49, 46, 52]);
    const request = vi.fn().mockResolvedValue(
      new Response(pdf, {
        headers: {
          "Content-Disposition":
            'attachment; filename="bonetwin-demo-dxa-2026.pdf"',
          "Content-Type": "application/pdf",
        },
      }),
    );
    vi.stubGlobal("fetch", request);

    const response = await GET(
      new Request(
        "https://app.example.test/api/backend/demo-documents/bonetwin-demo-dxa-2026.pdf",
      ),
      context(["demo-documents", "bonetwin-demo-dxa-2026.pdf"]),
    );

    const [url] = request.mock.calls[0] as [URL];
    expect(url.toString()).toBe(
      "https://api.example.test/demo-documents/bonetwin-demo-dxa-2026.pdf",
    );
    expect(new Uint8Array(await response.arrayBuffer())).toEqual(pdf);
    expect(response.headers.get("content-type")).toBe("application/pdf");
    expect(response.headers.get("content-disposition")).toContain(
      "bonetwin-demo-dxa-2026.pdf",
    );
  });

  it("allows the current-date generated demo report", async () => {
    const request = vi.fn().mockResolvedValue(
      new Response("%PDF-today", {
        headers: { "Content-Type": "application/pdf" },
      }),
    );
    vi.stubGlobal("fetch", request);

    const response = await GET(
      new Request(
        "https://app.example.test/api/backend/demo-documents/bonetwin-demo-dxa-2026-08-16.pdf",
      ),
      context(["demo-documents", "bonetwin-demo-dxa-2026-08-16.pdf"]),
    );

    const [url] = request.mock.calls[0] as [URL];
    expect(url.toString()).toBe(
      "https://api.example.test/demo-documents/bonetwin-demo-dxa-2026-08-16.pdf",
    );
    expect(response.status).toBe(200);
  });

  it("blocks every route outside the narrow allowlist", async () => {
    const request = vi.fn();
    vi.stubGlobal("fetch", request);

    const responses = await Promise.all([
      GET(
        new Request("https://app.example.test/api/backend/health/ready"),
        context(["health", "ready"]),
      ),
      GET(
        new Request(
          "https://app.example.test/api/backend/demo-documents/private.pdf",
        ),
        context(["demo-documents", "private.pdf"]),
      ),
      GET(
        new Request("https://app.example.test/api/backend/v1/../admin"),
        context(["v1", "..", "admin"]),
      ),
    ]);

    expect(responses.map((response) => response.status)).toEqual([
      404, 404, 404,
    ]);
    expect(request).not.toHaveBeenCalled();
  });

  it("fails safely for missing configuration and an unreachable upstream", async () => {
    delete process.env.BONETWIN_API_URL;
    const missing = await GET(
      new Request("https://app.example.test/api/backend/v1/transparency"),
      context(["v1", "transparency"]),
    );

    process.env.BONETWIN_API_URL = BACKEND_URL;
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("internal host details")),
    );
    const unavailable = await GET(
      new Request("https://app.example.test/api/backend/v1/transparency"),
      context(["v1", "transparency"]),
    );

    expect(missing.status).toBe(503);
    expect(unavailable.status).toBe(502);
    expect(await missing.text()).not.toContain(BACKEND_URL);
    expect(await unavailable.text()).not.toContain("internal host details");
  });

  it("exports every method required by the current browser client", () => {
    expect([GET, POST, PUT, DELETE]).toHaveLength(4);
  });
});
