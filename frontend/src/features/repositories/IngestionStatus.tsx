import type { Repository } from "../../types/api";

export function IngestionStatus({ repository, onRetry }: {
  repository: Repository;
  onRetry: () => Promise<void>;
}) {
  const job = repository.ingestion;
  if (!job) return null;
  if (job.state === "queued") {
    return <p className="ingestion-status" role="status">Queued · Waiting for worker</p>;
  }
  if (job.state === "running") {
    return <p className="ingestion-status" role="status">
      {job.stage ?? "Processing"} · {job.total_files === null
        ? "Waiting for file list"
        : `${job.completed_files} / ${job.total_files} files`}
    </p>;
  }
  if (job.state === "failed") {
    return <div className="ingestion-status">
      <p>{job.error_message ?? "Repository import failed"}</p>
      <button type="button" onClick={() => void onRetry()}>Retry</button>
    </div>;
  }
  return null;
}
