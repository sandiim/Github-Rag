import { useState } from "react";

export function AddRepositoryForm({ onAdd }: { onAdd: (url: string) => Promise<void> }) {
  const [url, setUrl] = useState(""); const [busy, setBusy] = useState(false);
  return <form onSubmit={async event => { event.preventDefault(); setBusy(true); try { await onAdd(url); setUrl(""); } finally { setBusy(false); } }}><label>GitHub repository URL<input aria-label="GitHub repository URL" required type="url" value={url} onChange={event => setUrl(event.target.value)} /></label><button disabled={busy}>{busy ? "Adding…" : "Add repository"}</button></form>;
}
