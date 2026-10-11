import { useState } from "react";
export function RebuildButton({ onRebuild }: { onRebuild: () => Promise<void> }) { const [busy, setBusy] = useState(false); return <button onClick={async () => { setBusy(true); try { await onRebuild(); } finally { setBusy(false); } }} disabled={busy}>{busy ? "Rebuilding…" : "Rebuild index"}</button>; }
