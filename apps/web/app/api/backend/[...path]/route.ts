const DEMO_DOCUMENTS = new Set([
  "bonetwin-demo-dxa-2019.pdf",
  "bonetwin-demo-dxa-2022.pdf",
  "bonetwin-demo-dxa-2026.pdf",
  "bonetwin-demo-dxa-2026-08-16.pdf",
]);

const REQUEST_HEADERS = [
  "accept",
  "authorization",
  "content-type",
  "idempotency-key",
  "x-request-id",
] as const;

const RESPONSE_HEADERS = [
  "content-disposition",
  "content-type",
  "retry-after",
  "x-request-id",
] as const;

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function errorResponse(status: number, detail: string): Response {
  return Response.json(
    { detail },
    { status, headers: { "Cache-Control": "no-store" } },
  );
}

function backendBaseUrl(): URL | null {
  const configured = process.env.BONETWIN_API_URL?.trim();
  if (!configured) return null;
  try {
    const url = new URL(configured);
    const localHttp =
      url.protocol === "http:" &&
      (url.hostname === "127.0.0.1" || url.hostname === "localhost");
    if (url.protocol !== "https:" && !localHttp) return null;
    if (url.username || url.password || url.search || url.hash) return null;
    return url;
  } catch {
    return null;
  }
}

function allowedPath(path: string[]): boolean {
  const segmentsAreSafe = path.every(
    (segment) =>
      segment.length > 0 &&
      segment !== "." &&
      segment !== ".." &&
      !segment.includes("/") &&
      !segment.includes("\\"),
  );
  if (!segmentsAreSafe) return false;
  if (path[0] === "v1" && path.length > 1) return true;
  return (
    path.length === 2 &&
    path[0] === "demo-documents" &&
    DEMO_DOCUMENTS.has(path[1] ?? "")
  );
}

function copyHeaders(source: Headers, names: readonly string[]): Headers {
  const result = new Headers();
  for (const name of names) {
    const value = source.get(name);
    if (value !== null) result.set(name, value);
  }
  return result;
}

async function forward(
  request: Request,
  context: RouteContext,
): Promise<Response> {
  const { path } = await context.params;
  if (!allowedPath(path)) {
    return errorResponse(404, "BoneTwin API route not found");
  }

  const baseUrl = backendBaseUrl();
  if (baseUrl === null) {
    return errorResponse(503, "BoneTwin API is not configured");
  }

  const upstreamUrl = new URL(baseUrl);
  const basePath = upstreamUrl.pathname.replace(/\/$/, "");
  upstreamUrl.pathname = `${basePath}/${path.map(encodeURIComponent).join("/")}`;
  upstreamUrl.search = new URL(request.url).search;

  const requestBody =
    request.method === "GET" || request.method === "HEAD"
      ? undefined
      : await request.arrayBuffer();

  try {
    const upstream = await fetch(upstreamUrl, {
      method: request.method,
      headers: copyHeaders(request.headers, REQUEST_HEADERS),
      body:
        requestBody !== undefined && requestBody.byteLength > 0
          ? requestBody
          : undefined,
      cache: "no-store",
      redirect: "manual",
    });
    const responseHeaders = copyHeaders(upstream.headers, RESPONSE_HEADERS);
    responseHeaders.set("Cache-Control", "no-store");
    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    });
  } catch {
    return errorResponse(502, "BoneTwin API is temporarily unavailable");
  }
}

export const GET = forward;
export const POST = forward;
export const PUT = forward;
export const DELETE = forward;
