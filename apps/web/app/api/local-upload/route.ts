import { randomUUID } from "node:crypto";

import { type NextRequest, NextResponse } from "next/server";

import { uploadLocalSyntheticReport } from "../../../lib/server-upload";

export const runtime = "nodejs";

function redirectWithMessage(
  request: NextRequest,
  message: string,
): NextResponse {
  const destination = new URL("/demo", request.url);
  destination.searchParams.set("view", "overview");
  destination.searchParams.set("upload_error", message);
  return NextResponse.redirect(destination, 303);
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  try {
    const form = await request.formData();
    const report = form.get("report");
    if (!(report instanceof File)) {
      return redirectWithMessage(request, "Choose a PDF before uploading.");
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
    const destination = new URL("/demo", request.url);
    destination.searchParams.set("view", "report");
    destination.searchParams.set("document", document.id);
    return NextResponse.redirect(destination, 303);
  } catch (error) {
    return redirectWithMessage(
      request,
      error instanceof Error ? error.message : "Report processing failed.",
    );
  }
}
