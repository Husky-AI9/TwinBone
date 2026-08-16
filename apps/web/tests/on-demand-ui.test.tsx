import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { ProductApp } from "../components/product-app";

describe("on-demand demo shell", () => {
  it("renders without an API request and exposes load and logout controls", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const markup = renderToStaticMarkup(<ProductApp uploadKey="test-upload" />);

    expect(fetchSpy).not.toHaveBeenCalled();
    expect(markup).toContain("Load record");
    expect(markup).toContain("Ready on demand");
    expect(markup).toContain("Log out");
    fetchSpy.mockRestore();
  });
});
