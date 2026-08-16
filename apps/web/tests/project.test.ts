import { describe, expect, it } from "vitest";

import { boneSites, statusTone, timelinePoints } from "../lib/preview-data";
import { dataPolicy, phaseLabel, productName } from "../lib/project";

describe("BoneTwin UI preview", () => {
  it("identifies the product and synthetic-only policy", () => {
    expect(productName).toBe("BoneTwin");
    expect(dataPolicy).toBe("synthetic-only");
    expect(phaseLabel).toContain("Local runnable demo");
  });

  it("provides synthetic, selectable bone sites and a timeline", () => {
    expect(boneSites).toHaveLength(4);
    expect(boneSites.every((site) => site.statusDetail.length > 0)).toBe(true);
    expect(timelinePoints.map((point) => point.year)).toEqual([
      "2019",
      "2022",
      "2026",
    ]);
    expect(statusTone("Verified")).toContain("emerald");
  });
});
