import { beforeEach, describe, expect, it, vi } from "vitest";

const { uploadReport } = vi.hoisted(() => ({ uploadReport: vi.fn() }));

vi.mock("../lib/server-upload", () => ({
  uploadLocalSyntheticReport: uploadReport,
}));

import { POST } from "../app/api/local-upload/route";

describe("hosted upload route redirects", () => {
  beforeEach(() => uploadReport.mockReset());

  it("returns a relative report redirect behind a hosting proxy", async () => {
    uploadReport.mockResolvedValue({ id: "document-123" });
    const form = new FormData();
    form.set("idempotency_key", "upload-route-test");
    form.set(
      "report",
      new File(["%PDF-1.4"], "report.pdf", { type: "application/pdf" }),
    );

    const response = await POST(
      new Request("http://localhost:3000/api/local-upload", {
        method: "POST",
        body: form,
      }) as never,
    );

    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toBe(
      "/demo?view=report&document=document-123",
    );
  });

  it("returns a relative error redirect when no file is selected", async () => {
    const response = await POST(
      new Request("http://localhost:3000/api/local-upload", {
        method: "POST",
        body: new FormData(),
      }) as never,
    );

    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toContain(
      "/demo?view=overview&upload_error=",
    );
  });
});
