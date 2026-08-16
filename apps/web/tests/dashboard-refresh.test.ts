import type { Timeline, Transparency } from "@bonetwin/shared-types";
import { describe, expect, it, vi } from "vitest";

import { loadDashboardData } from "../components/product-app";

describe("dashboard startup loading", () => {
  it("loads panels sequentially and preserves later successes after one failure", async () => {
    let active = 0;
    let maximumActive = 0;
    async function tracked<T>(value: T): Promise<T> {
      active += 1;
      maximumActive = Math.max(maximumActive, active);
      await Promise.resolve();
      active -= 1;
      return value;
    }

    const api = {
      timeline: vi.fn(() => tracked({} as Timeline)),
      tasks: vi.fn(async () => {
        await tracked(null);
        throw new Error("temporary task failure");
      }),
      transparency: vi.fn(() => tracked({ mode: "AWS" } as Transparency)),
    };

    const result = await loadDashboardData(api, "subject-1");

    expect(maximumActive).toBe(1);
    expect(result.timeline.status).toBe("fulfilled");
    expect(result.tasks.status).toBe("rejected");
    expect(result.transparency.status).toBe("fulfilled");
    expect(api.timeline).toHaveBeenCalledWith("subject-1");
    expect(api.tasks).toHaveBeenCalledWith("subject-1");
    expect(api.transparency).toHaveBeenCalledOnce();
  });
});
