import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { ChatComposer } from "./ChatComposer";

afterEach(cleanup);

it("keeps the question available for retry when sending fails", async () => {
  const onSend = vi.fn().mockRejectedValue(new Error("Temporary failure"));
  render(<ChatComposer disabled={false} onSend={onSend} />);
  const input = screen.getByRole("textbox", { name: "Ask about this repository" });

  fireEvent.change(input, { target: { value: "Where is the app?" } });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));

  await waitFor(() => expect(onSend).toHaveBeenCalledWith("Where is the app?"));
  expect(input).toHaveValue("Where is the app?");
});
