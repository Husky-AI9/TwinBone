import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { NativePdfPicker } from "../components/product-app";

describe("native PDF picker", () => {
  it("renders a visible native file input instead of a hidden label target", () => {
    const markup = renderToStaticMarkup(
      <NativePdfPicker
        inputId="test-pdf"
        uploadKey="upload-test-key"
        selectedFile={null}
        busy={false}
        onFileChange={vi.fn()}
      />,
    );

    expect(markup).toContain('type="file"');
    expect(markup).toContain('accept="application/pdf,.pdf"');
    expect(markup).toContain('action="/api/local-upload"');
    expect(markup).toContain('type="submit"');
    expect(markup).toContain("required");
    expect(markup).not.toContain("sr-only");
    expect(markup).not.toMatch(/<button[^>]*\sdisabled(?:=|>)/);
    expect(markup).toContain("Upload and process");
  });
});
