import { randomUUID } from "node:crypto";

import { type NextRequest, NextResponse } from "next/server";

import { uploadLocalSyntheticReport } from "../../../lib/server-upload";

export const runtime = "nodejs";

function redirectWithMessage(message: string): NextResponse {
  const search = new URLSearchParams({
    view: "overview",
    upload_error: message,
  });
  return new NextResponse(null, {
    status: 303,
    headers: { Location: `/demo?${search.toString()}` },
  });
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  try {
    const form = await request.formData();
    const report = form.get("report");
    if (!(report instanceof File)) {
      return redirectWithMessage("Choose a PDF before uploading.");
    }
    const submittedKey = form.get("idempotency_key");
    const idempotencyKey =
      typeof submittedKey === "string" && submittedKey.length >= 8
        ? submittedKey
        : randomUUID();
    const document = await uploadLocalSyntheticReport(report, {
      baseUrl:
        process.env.BONETWIN_API_URL ??
        process.env.NEXT_PUBLIC_BONETWIN_API_URL ??
        "http://127.0.0.1:8000",
      idempotencyKey,
    });
    const search = new URLSearchParams({
      view: "report",
      document: document.id,
    });
    return new NextResponse(null, {
      status: 303,
      headers: { Location: `/demo?${search.toString()}` },
    });
  } catch (error) {
    return redirectWithMessage(
      error instanceof Error ? error.message : "Report processing failed.",
    );
  }
}
