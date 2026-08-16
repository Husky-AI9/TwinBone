import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AnatomicalSkeleton } from "../components/anatomical-skeleton";

describe("anatomical skeleton", () => {
  it("renders the major axial and appendicular structures", () => {
    const markup = renderToStaticMarkup(
      <AnatomicalSkeleton selected="lumbar-spine" />,
    );

    for (const structure of [
      "skull",
      "vertebral-column",
      "thoracic-cage",
      "pelvis",
      "upper-limbs",
      "hands",
      "lower-limbs",
      "femur",
      "patella",
      "tibia",
      "fibula",
      "feet",
      "tarsals",
    ]) {
      expect(markup).toContain(`data-anatomy="${structure}"`);
    }
  });

  it("keeps every supported DXA site highlightable and accessible", () => {
    const markup = renderToStaticMarkup(
      <AnatomicalSkeleton selected="femoral-neck" />,
    );

    for (const site of [
      "left-total-hip",
      "lumbar-spine",
      "femoral-neck",
      "forearm",
    ]) {
      expect(markup).toContain(`data-site="${site}"`);
    }
    expect(markup).toContain("Anterior human skeletal site map");
    expect(markup).toContain("Selected bone density sites are highlighted");
  });
});
