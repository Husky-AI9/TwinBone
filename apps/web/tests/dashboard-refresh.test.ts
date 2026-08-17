import type { DashboardSnapshot } from "@bonetwin/shared-types";
import { BoneTwinClient } from "@bonetwin/api-client";
import { describe, expect, it, vi } from "vitest";

import { loadDashboardData } from "../components/product-app";

describe("on-demand dashboard loading", () => {
  it("loads the complete record with one API request", async () => {
    const snapshot = {
      timeline: { reports: [], memories: [], tasks: [] },
      tasks: [],
      transparency: { mode: "AWS" },
    } as unknown as DashboardSnapshot;
    const api = { dashboard: vi.fn(async () => snapshot) };

    await expect(loadDashboardData(api, "subject-1")).resolves.toBe(snapshot);
    expect(api.dashboard).toHaveBeenCalledOnce();
    expect(api.dashboard).toHaveBeenCalledWith("subject-1");
  });

  it("sends one authenticated request to the bundled endpoint", async () => {
    const snapshot = {
      timeline: {},
      tasks: [],
      transparency: {},
    } as unknown as DashboardSnapshot;
    const fetchMock = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        void input;
        void init;
        return new Response(JSON.stringify(snapshot), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      },
    );
    vi.stubGlobal("fetch", fetchMock);

    const client = new BoneTwinClient({
      baseUrl: "/api/backend",
      token: "demo-clinician",
    });
    await expect(client.dashboard("subject-1")).resolves.toEqual(snapshot);

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe("/api/backend/v1/subjects/subject-1/dashboard");
    expect(new Headers(init?.headers).get("Authorization")).toBe(
      "Bearer demo-clinician",
    );
    vi.unstubAllGlobals();
  });
});
