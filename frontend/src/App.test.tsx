import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { ApiClient } from "./api-client/client";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("streaming chat", () => {
  it("shows draft text, then a linked checkpoint, then the saved answer", async () => {
    vi.spyOn(ApiClient.prototype, "repositories").mockResolvedValue([
      { id: "repo-1", name: "widgets", status: "ready" }
    ]);
    vi.spyOn(ApiClient.prototype, "conversation").mockResolvedValue({ title: "widgets", messages: [] });
    const citation = {
      path: "src/app.py", startLine: 10, endLine: 10,
      url: "https://github.com/acme/widgets/blob/abc/src/app.py#L10-L10"
    };
    let continueStream: (() => void) | undefined;
    const askStream = vi.spyOn(ApiClient.prototype, "askStream").mockImplementation(async (_id, _question, onEvent) => {
      onEvent({ type: "status", stage: "generating" });
      onEvent({ type: "delta", text: "The app " });
      await new Promise<void>(resolve => { continueStream = resolve; });
      onEvent({ type: "checkpoint", text: "The app [src/app.py:10-10]", citations: [citation] });
      onEvent({ type: "complete", text: "The app [src/app.py:10-10]", citations: [citation] });
    });

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /widgets/ }));
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Ask about this repository" })).toBeEnabled());
    fireEvent.change(screen.getByRole("textbox", { name: "Ask about this repository" }), {
      target: { value: "Where is the app?" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(screen.getByText("The app")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
    expect(await screen.findByRole("status")).toHaveTextContent("Waiting for more");
    continueStream?.();
    await waitFor(() => expect(screen.getByRole("link", { name: "src/app.py:10-10" })).toHaveAttribute("href", citation.url));
    expect(askStream).toHaveBeenCalledOnce();
    await waitFor(() => expect(screen.getByRole("button", { name: "Send" })).toBeEnabled());
  });

  it("removes an unsaved draft and shows an error if generation fails", async () => {
    vi.spyOn(ApiClient.prototype, "repositories").mockResolvedValue([
      { id: "repo-1", name: "widgets", status: "ready" }
    ]);
    vi.spyOn(ApiClient.prototype, "conversation").mockResolvedValue({ title: "widgets", messages: [] });
    vi.spyOn(ApiClient.prototype, "askStream").mockImplementation(async (_id, _question, onEvent) => {
      onEvent({ type: "delta", text: "Unverified draft" });
      onEvent({ type: "error", message: "Answer generation failed. Please try again." });
    });

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /widgets/ }));
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Ask about this repository" })).toBeEnabled());
    fireEvent.change(screen.getByRole("textbox", { name: "Ask about this repository" }), {
      target: { value: "Where?" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Answer generation failed");
    await waitFor(() => expect(screen.queryByText("Unverified draft")).not.toBeInTheDocument());
    expect(screen.getByRole("textbox", { name: "Ask about this repository" })).toHaveValue("Where?");
  });

  it("aborts the old answer when another repository is selected", async () => {
    vi.spyOn(ApiClient.prototype, "repositories").mockResolvedValue([
      { id: "repo-1", name: "widgets", status: "ready" },
      { id: "repo-2", name: "gadgets", status: "ready" }
    ]);
    vi.spyOn(ApiClient.prototype, "conversation").mockResolvedValue({ title: "repo", messages: [] });
    let oldSignal: AbortSignal | undefined;
    vi.spyOn(ApiClient.prototype, "askStream").mockImplementation(async (_id, _question, onEvent, signal) => {
      oldSignal = signal;
      onEvent({ type: "delta", text: "Old draft" });
      await new Promise<void>((_resolve, reject) => {
        signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
      });
    });

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /widgets/ }));
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Ask about this repository" })).toBeEnabled());
    fireEvent.change(screen.getByRole("textbox", { name: "Ask about this repository" }), {
      target: { value: "Where?" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByText("Old draft");

    fireEvent.click(screen.getByRole("button", { name: /gadgets/ }));

    await waitFor(() => expect(oldSignal?.aborted).toBe(true));
    await waitFor(() => expect(screen.queryByText("Old draft")).not.toBeInTheDocument());
    expect(screen.getByRole("heading", { name: "gadgets" })).toBeInTheDocument();
  });
});
