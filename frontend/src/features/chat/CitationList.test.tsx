import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CitationList } from "./CitationList";

describe("CitationList", () => {
  it("renders a citation as a commit-pinned external link", () => {
    render(
      <CitationList
        citations={[
          {
            path: "src/app.py",
            startLine: 10,
            endLine: 14,
            url: "https://github.com/acme/widgets/blob/abc/src/app.py#L10-L14"
          }
        ]}
      />
    );

    expect(screen.getByRole("link", { name: "src/app.py:10-14" })).toHaveAttribute(
      "href",
      expect.stringContaining("/blob/abc/")
    );
  });
});
