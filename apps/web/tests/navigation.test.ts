import { describe, expect, it } from "vitest";

import { normalizeAppView, viewHref } from "../lib/navigation";

describe("progressively enhanced navigation", () => {
  it("creates real URLs for interactive product views", () => {
    expect(viewHref("overview")).toBe("/demo?view=overview");
    expect(viewHref("report")).toBe("/demo?view=report");
  });

  it("renders a requested view after a full page navigation", () => {
    expect(normalizeAppView("upload")).toBe("overview");
    expect(normalizeAppView(["report", "overview"])).toBe("report");
  });

  it("falls back safely for unknown URLs", () => {
    expect(normalizeAppView("diagnosis")).toBe("overview");
    expect(normalizeAppView(undefined)).toBe("overview");
  });
});
