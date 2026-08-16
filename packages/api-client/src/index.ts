/**
 * Typed client generated from BoneTwin's Phase 2 OpenAPI surface.
 *
 * Regenerate the checked-in OpenAPI artifact with:
 * `python -m uv run python -m scripts.export_openapi`.
 */
import type {
  AgentRun,
  DashboardSnapshot,
  DemoDataReset,
  DocumentStatus,
  Me,
  ReviewTask,
  SubjectSummary,
  Timeline,
  Transparency,
} from "@bonetwin/shared-types";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

export type ClientOptions = {
  baseUrl?: string;
  token?: string;
  retryDelayMs?: number;
};

export type DemoReportYear = 2019 | 2022 | 2026;

export function removeSyntheticWord<T>(value: T): T {
  if (typeof value === "string") {
    if (/^https?:\/\//i.test(value)) return value;
    return value.replace(/\bsynthetic\b[ -]?/gi, "") as T;
  }
  if (Array.isArray(value)) {
    return value.map((item) => removeSyntheticWord(item)) as T;
  }
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [
        key,
        removeSyntheticWord(item),
      ]),
    ) as T;
  }
  return value;
}

export class BoneTwinClient {
  readonly baseUrl: string;
  private token: string;
  private readonly retryDelayMs: number;

  constructor(options: ClientOptions = {}) {
    this.baseUrl = options.baseUrl ?? "http://127.0.0.1:8000";
    this.token = options.token ?? "demo-clinician";
    this.retryDelayMs = Math.max(0, options.retryDelayMs ?? 250);
  }

  setToken(token: string): void {
    this.token = token;
  }

  private async request<T>(
    path: string,
    init: RequestInit = {},
    idempotencyKey?: string,
  ): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set("Authorization", `Bearer ${this.token}`);
    if (typeof init.body === "string" && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    if (idempotencyKey) headers.set("Idempotency-Key", idempotencyKey);
    const readOnly = (init.method ?? "GET").toUpperCase() === "GET";
    const attempts = readOnly ? 3 : 1;
    for (let attempt = 0; attempt < attempts; attempt += 1) {
      let response: Response;
      try {
        response = await fetch(`${this.baseUrl}${path}`, {
          ...init,
          headers,
        });
      } catch (error) {
        if (attempt + 1 < attempts) {
          await this.waitBeforeRetry(attempt);
          continue;
        }
        throw error;
      }
      if (
        !response.ok &&
        [429, 502, 503, 504].includes(response.status) &&
        attempt + 1 < attempts
      ) {
        await response.body?.cancel().catch(() => undefined);
        await this.waitBeforeRetry(attempt);
        continue;
      }
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as {
          detail?: string;
          message?: string;
        } | null;
        throw new ApiError(
          removeSyntheticWord(
            body?.detail ?? body?.message ?? "BoneTwin API request failed",
          ),
          response.status,
        );
      }
      return removeSyntheticWord((await response.json()) as T);
    }
    throw new ApiError("BoneTwin API request failed", 503);
  }

  private async waitBeforeRetry(attempt: number): Promise<void> {
    await new Promise((resolve) =>
      setTimeout(resolve, this.retryDelayMs * (attempt + 1)),
    );
  }

  me(): Promise<Me> {
    return this.request("/v1/me");
  }

  subjects(): Promise<SubjectSummary[]> {
    return this.request("/v1/subjects");
  }

  timeline(subjectId: string): Promise<Timeline> {
    return this.request(`/v1/subjects/${subjectId}/timeline`);
  }

  dashboard(subjectId: string): Promise<DashboardSnapshot> {
    return this.request(`/v1/subjects/${subjectId}/dashboard`);
  }

  clearDemoData(subjectId: string): Promise<DemoDataReset> {
    return this.request(
      `/v1/subjects/${subjectId}/demo-data`,
      { method: "DELETE" },
      crypto.randomUUID(),
    );
  }

  async demoDocument(year: DemoReportYear): Promise<File> {
    const filename = `bonetwin-demo-dxa-${year}.pdf`;
    const response = await fetch(`${this.baseUrl}/demo-documents/${filename}`);
    if (!response.ok) {
      throw new ApiError("Demo report is unavailable", response.status);
    }
    const content = await response.blob();
    if (content.size === 0) {
      throw new ApiError("Demo report is empty", 502);
    }
    return new File([content], filename, { type: "application/pdf" });
  }

  async uploadDocument(subjectId: string, file: File): Promise<DocumentStatus> {
    const key = crypto.randomUUID();
    const sha256 = await digestSha256(file);
    const intent = await this.request<{
      document_id: string;
      upload_url: string;
      upload_headers?: Record<string, string>;
      duplicate: boolean;
    }>(
      `/v1/subjects/${subjectId}/documents/upload-intent`,
      {
        method: "POST",
        body: JSON.stringify({
          original_filename: file.name,
          content_type: file.type || "application/pdf",
          byte_size: file.size,
          sha256,
        }),
      },
      key,
    );
    if (!intent.duplicate) {
      const uploadHeaders = new Headers(intent.upload_headers);
      if (!uploadHeaders.has("Content-Type")) {
        uploadHeaders.set("Content-Type", file.type || "application/pdf");
      }
      if (/^https?:\/\//i.test(intent.upload_url)) {
        const uploadResponse = await fetch(intent.upload_url, {
          method: "PUT",
          headers: uploadHeaders,
          body: file,
        });
        if (!uploadResponse.ok) {
          throw new ApiError(
            "Encrypted S3 upload failed",
            uploadResponse.status,
          );
        }
      } else {
        await this.request(
          intent.upload_url,
          {
            method: "PUT",
            headers: uploadHeaders,
            body: file,
          },
          `bytes-${key}`,
        );
      }
    }
    return this.request(
      `/v1/documents/${intent.document_id}/complete-upload`,
      {
        method: "POST",
        body: JSON.stringify({ acknowledge_synthetic_only: true }),
      },
      `complete-${key}`,
    );
  }

  runComparison(subjectId: string): Promise<AgentRun> {
    return this.request(
      `/v1/subjects/${subjectId}/agent/runs`,
      {
        method: "POST",
        body: JSON.stringify({
          request_type: "COMPARE_REPORTS",
          query: "Compare the latest report with the trusted timeline.",
        }),
      },
      crypto.randomUUID(),
    );
  }

  tasks(subjectId: string): Promise<ReviewTask[]> {
    return this.request(`/v1/subjects/${subjectId}/tasks`);
  }

  resolveTask(
    taskId: string,
    action: "approve" | "correct" | "reject",
    payload: {
      note: string;
      corrected_title?: string;
      corrected_content?: string;
    },
  ): Promise<ReviewTask> {
    return this.request(
      `/v1/tasks/${taskId}/${action}`,
      { method: "POST", body: JSON.stringify(payload) },
      crypto.randomUUID(),
    );
  }

  transparency(): Promise<Transparency> {
    return this.request("/v1/transparency");
  }
}

async function digestSha256(file: File): Promise<string> {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    await file.arrayBuffer(),
  );
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
}

export const clientStatus = "openapi-typed-phase-7" as const;
