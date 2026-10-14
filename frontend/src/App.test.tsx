import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import App from "./App";

const queued = {
  id: "repo-1", name: "widgets", status: "pending",
  ingestion: { id: "job-1", state: "queued", stage: "waiting", completed_files: 0,
    total_files: null, error_message: null },
};
const ready = { ...queued, status: "ready", ingestion: { ...queued.ingestion, state: "completed" } };
const json = (value: unknown) => new Response(JSON.stringify(value), {
  status: 200, headers: { "Content-Type": "application/json" },
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

test("add returns immediately and polling eventually enables chat", async () => {
  let listCalls = 0;
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    if (url === "/repositories" && init?.method === "POST") return json(queued);
    if (url === "/repositories") return json(++listCalls === 1 ? [] : [ready]);
    if (url.endsWith("/conversation")) return json({ title: "widgets", messages: [] });
    throw new Error(`Unexpected request: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  await waitFor(() => expect(listCalls).toBe(1));
  fireEvent.change(screen.getByRole("textbox", { name: "GitHub repository URL" }), {
    target: { value: "https://github.com/acme/widgets" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Add repository" }));
  expect(await screen.findByText(/Waiting for worker/)).toBeInTheDocument();
  expect(screen.getByRole("textbox", { name: /ask about this repository/i })).toBeDisabled();
  await act(async () => { await new Promise(resolve => setTimeout(resolve, 2100)); });
  await waitFor(() => expect(screen.getByRole("textbox", { name: /ask about this repository/i })).toBeEnabled());
});

test("a ready repository remains chat-ready while rebuilding", async () => {
  const running = { ...ready, ingestion: { ...queued.ingestion, state: "running" } };
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    if (url === "/repositories") return json([running]);
    if (url.endsWith("/conversation")) return json({ title: "widgets", messages: [] });
    throw new Error(`Unexpected request: ${url} ${init?.method}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "widgets" }));
  await waitFor(() => expect(screen.getByRole("textbox", { name: /ask about this repository/i })).toBeEnabled());
});
