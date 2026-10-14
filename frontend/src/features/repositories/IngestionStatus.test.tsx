import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { IngestionStatus } from "./IngestionStatus";
import type { Repository } from "../../types/api";

const repository: Repository = {
  id: "repo-1", name: "widgets", status: "pending",
  ingestion: {
    id: "job-1", state: "running", stage: "embedding",
    completed_files: 3, total_files: 10, error_message: null,
  },
};

test("shows selected-file progress", () => {
  render(<IngestionStatus repository={repository} onRetry={async () => {}} />);
  expect(screen.getByRole("status")).toHaveTextContent("3 / 10 files");
});

test("shows retry on failure", () => {
  const failed: Repository = {
    ...repository,
    ingestion: { ...repository.ingestion!, state: "failed", error_message: "Connection timed out" },
  };
  render(<IngestionStatus repository={failed} onRetry={async () => {}} />);
  expect(screen.getByText("Connection timed out")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
});
