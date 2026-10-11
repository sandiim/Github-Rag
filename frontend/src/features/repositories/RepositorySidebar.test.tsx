import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { RepositorySidebar } from "./RepositorySidebar";

describe("RepositorySidebar", () => {
  it("selects a repository from the persistent library", async () => {
    const onSelect = vi.fn();
    render(
      <RepositorySidebar
        repositories={[{ id: "a", name: "widgets", status: "ready" }]}
        selectedRepositoryId={null}
        onSelect={onSelect}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: "widgets" }));

    expect(onSelect).toHaveBeenCalledWith("a");
  });
});
