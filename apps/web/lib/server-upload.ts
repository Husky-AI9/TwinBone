import { createHash } from "node:crypto";

import { removeSyntheticWord } from "@bonetwin/api-client";
import type { DocumentStatus } from "@bonetwin/shared-types";

const SUBJECT_ID = "30000000-0000-4000-8000-000000000001";
const MAX_UPLOAD_BYTES = 10_000_000;

type FetchImplementation = typeof fetch;

async function readApiError(response: Response): Promise<string> {
  const body = (await response.json().catch(() => null)) as {
    detail?: string;
  } | null;
  return removeSyntheticWord(
    body?.detail ?? `BoneTwin API returned ${response.status}`,
  );
}

async function requireSuccess(response: Response): Promise<Response> {
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return response;
}

export async function uploadLocalSyntheticReport(
  file: File,
  options: {
    baseUrl: string;
    idempotencyKey: string;
    fetchImplementation?: FetchImplementation;
  },
): Promise<DocumentStatus> {
  if (file.size <= 0 || file.size > MAX_UPLOAD_BYTES) {
    throw new Error("Choose a non-empty PDF no larger than 10 MB.");
  }
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    throw new Error("Local demo uploads must be PDF files.");
  }
  if (options.idempotencyKey.length < 8) {
    throw new Error("Upload idempotency key is invalid.");
  }

  const request = options.fetchImplementation ?? fetch;
  const bytes = Buffer.from(await file.arrayBuffer());
  const baseUrl = options.baseUrl.replace(/\/$/, "");
  const authenticated = {
    Authorization: "Bearer demo-clinician",
  };
  const intentResponse = await requireSuccess(
    await request(
      `${baseUrl}/v1/subjects/${SUBJECT_ID}/documents/upload-intent`,
      {
        method: "POST",
        headers: {
          ...authenticated,
          "Content-Type": "application/json",
          "Idempotency-Key": options.idempotencyKey,
        },
        body: JSON.stringify({
          original_filename: file.name,
          content_type: "application/pdf",
          byte_size: file.size,
          sha256: createHash("sha256").update(bytes).digest("hex"),
        }),
      },
    ),
  );
  const intent = (await intentResponse.json()) as {
    document_id: string;
    upload_url: string;
    upload_headers?: Record<string, string>;
    duplicate: boolean;
  };

  if (!intent.duplicate) {
    const uploadHeaders = new Headers(intent.upload_headers);
    if (!uploadHeaders.has("Content-Type")) {
      uploadHeaders.set("Content-Type", "application/pdf");
    }
    const directToS3 = /^https?:\/\//i.test(intent.upload_url);
    if (!directToS3) {
      uploadHeaders.set("Authorization", authenticated.Authorization);
      uploadHeaders.set("Idempotency-Key", `bytes-${options.idempotencyKey}`);
    }
    await requireSuccess(
      await request(new URL(intent.upload_url, `${baseUrl}/`).toString(), {
        method: "PUT",
        headers: uploadHeaders,
        body: bytes,
      }),
    );
  }

  const completeResponse = await requireSuccess(
    await request(
      `${baseUrl}/v1/documents/${intent.document_id}/complete-upload`,
      {
        method: "POST",
        headers: {
          ...authenticated,
          "Content-Type": "application/json",
          "Idempotency-Key": `complete-${options.idempotencyKey}`,
        },
        body: JSON.stringify({ acknowledge_synthetic_only: true }),
      },
    ),
  );
  return removeSyntheticWord((await completeResponse.json()) as DocumentStatus);
}
