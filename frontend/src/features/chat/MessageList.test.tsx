import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { MessageList } from "./MessageList";

const citation = {
  path: "stat.Rmd",
  startLine: 141,
  endLine: 220,
  url: "https://github.com/sandiim/R_analyse_multivari-e/blob/abc/stat.Rmd#L141-L220"
};

afterEach(cleanup);

describe("MessageList", () => {
  it("places a verified source link inside its answer section without a trailing citation list", () => {
    render(<MessageList messages={[{
      role: "assistant",
      content: "Preparation [stat.Rmd:141-220].\n\nAnalysis [stat.Rmd:141-220]. Unknown [other.Rmd:1-2].",
      citations: [citation]
    }]} />);

    const answer = screen.getByRole("article");
    const links = within(answer).getAllByRole("link", { name: "stat.Rmd:141-220" });
    expect(links).toHaveLength(2);
    expect(links[0]).toHaveAttribute("href", citation.url);
    expect(answer).toHaveTextContent("Unknown [other.Rmd:1-2].");
    expect(within(answer).queryByRole("list")).not.toBeInTheDocument();
  });

  it("keeps the source list for an older answer without inline markers", () => {
    render(<MessageList messages={[{
      role: "assistant", content: "An older answer.", citations: [citation]
    }]} />);

    expect(screen.getByRole("list")).toContainElement(screen.getByRole("link", { name: "stat.Rmd:141-220" }));
  });

  it("shows a calm waiting status beside a provisional answer", () => {
    const { container, rerender } = render(<MessageList messages={[{
      role: "assistant", content: "", citations: []
    }]} streaming={{ stage: "retrieving", waiting: true }} />);

    expect(screen.getByRole("status")).toHaveTextContent("Searching repository");
    rerender(<MessageList messages={[{
      role: "assistant", content: "A draft", citations: []
    }]} streaming={{ stage: "generating", waiting: true }} />);
    expect(screen.getByRole("status")).toHaveTextContent("Waiting for more");
    rerender(<MessageList messages={[{
      role: "assistant", content: "A draft", citations: []
    }]} streaming={{ stage: "generating", waiting: false }} />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(container.querySelector(".stream-status")).toBeInTheDocument();
    rerender(<MessageList messages={[{
      role: "assistant", content: "A draft", citations: []
    }]} streaming={null} />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
