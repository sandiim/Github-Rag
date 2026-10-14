import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AddRepositoryForm } from "./AddRepositoryForm";

describe("AddRepositoryForm", () => {
  it("shows an import failure and allows retry", async () => {
    const onAdd = vi.fn().mockRejectedValueOnce(new Error("Ollama is unavailable")).mockResolvedValueOnce(undefined);
    render(<AddRepositoryForm onAdd={onAdd} />);

    await userEvent.type(screen.getByRole("textbox", { name: "GitHub repository URL" }), "https://github.com/acme/widgets");
    await userEvent.click(screen.getByRole("button", { name: "Add repository" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Ollama is unavailable");
    await userEvent.click(screen.getByRole("button", { name: "Add repository" }));
    expect(onAdd).toHaveBeenCalledTimes(2);
  });
});
