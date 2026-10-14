import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiClient } from "./client";

afterEach(() => vi.unstubAllGlobals());

describe("ApiClient", () => {
  it("shows URL validation details instead of an object string", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ detail: [{ loc: ["body", "url"], msg: "Input should be a valid URL" }] }),
      { status: 422, headers: { "Content-Type": "application/json" } },
    )));

    await expect(new ApiClient().addRepository("https://github.com/acme/widgets"))
      .rejects.toThrow("Input should be a valid URL");
  });

  it("decodes fragmented UTF-8 and NDJSON chat events in order", async () => {
    const bytes = new TextEncoder().encode(
      '{"type":"delta","text":"Café"}\n' +
      '{"type":"complete","text":"Café","citations":[]}\n'
    );
    const accent = bytes.indexOf(0xc3);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(new ReadableStream({
      start(controller) {
        controller.enqueue(bytes.slice(0, accent + 1));
        controller.enqueue(bytes.slice(accent + 1, accent + 3));
        controller.enqueue(bytes.slice(accent + 3));
        controller.close();
      }
    }), { headers: { "Content-Type": "application/x-ndjson" } })));

    const events: unknown[] = [];
    await new ApiClient().askStream("repo-1", "What?", event => events.push(event));

    expect(events).toEqual([
      { type: "delta", text: "Café" },
      { type: "complete", text: "Café", citations: [] }
    ]);
    expect(fetch).toHaveBeenCalledWith("/repositories/repo-1/chat/stream", expect.objectContaining({
      method: "POST", body: JSON.stringify({ question: "What?" })
    }));
  });

  it("rejects a stream that ends before a complete event", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(
      '{"type":"delta","text":"partial"}\n', { headers: { "Content-Type": "application/x-ndjson" } }
    )));

    await expect(new ApiClient().askStream("repo-1", "What?", () => {}))
      .rejects.toThrow("The answer stream ended early");
  });

  it("closes the network reader after a streamed server error", async () => {
    let cancelled = false;
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode('{"type":"error","message":"Try again"}\n'));
      },
      cancel() { cancelled = true; }
    });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(body)));

    await expect(new ApiClient().askStream("repo-1", "What?", () => {}))
      .rejects.toThrow("Try again");
    expect(cancelled).toBe(true);
  });
});
