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
});
