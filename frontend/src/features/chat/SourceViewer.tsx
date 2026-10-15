import { useState, useEffect } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import type { Citation } from "../../types/api";

export function SourceViewer({ citation, onClose }: { citation: Citation | null; onClose: () => void }) {
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!citation) return;

    const fetchSource = async () => {
      setLoading(true);
      setError(null);
      try {
        // Try to convert blob URL to raw URL
        // https://github.com/user/repo/blob/sha/path -> https://raw.githubusercontent.com/user/repo/sha/path
        const url = new URL(citation.url);
        const pathSegments = url.pathname.split("/");
        
        let rawUrl = citation.url;
        if (pathSegments[1] === "blob") {
          // Convert github.com/owner/repo/blob/sha/path... to raw.githubusercontent.com/owner/repo/sha/path...
          const owner = pathSegments[1] === "blob" ? pathSegments[2] : pathSegments[1];
          const repo = pathSegments[1] === "blob" ? pathSegments[3] : pathSegments[2];
          const sha = pathSegments[1] === "blob" ? pathSegments[4] : pathSegments[3];
          const filePath = pathSegments.slice(pathSegments[1] === "blob" ? 5 : 4).join("/");
          
          rawUrl = `https://raw.githubusercontent.com/${owner}/${repo}/${sha}/${filePath}`;
        }

        const response = await fetch(rawUrl);
        if (!response.ok) throw new Error(`Failed to fetch source (${response.status})`);
        const text = await response.text();
        setCode(text);
      } catch (err: any) {
        setError(err.message || "An unexpected error occurred");
      } finally {
        setLoading(false);
      }
    };

    fetchSource();
  }, [citation]);

  if (!citation) return null;

  return (
    <aside className="source-viewer">
      <div className="source-header">
        <div className="source-title">
          <span className="file-path" title={citation.path}>{citation.path}</span>
          <span className="line-range">Lines {citation.startLine} - {citation.endLine}</span>
        </div>
        <div className="source-actions">
          <a href={citation.url} target="_blank" rel="noreferrer" className="open-github-link">
            Open on GitHub ↗
          </a>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>
      </div>
      <div className="source-content">
        {loading && <div className="source-status">Loading source...</div>}
        {error && (
          <div className="source-error">
            <p>{error}</p>
            <a href={citation.url} target="_blank" rel="noreferrer" className="retry-link">
              View on GitHub instead
            </a>
          </div>
        )}
        {!loading && !error && (
          <SyntaxHighlighter 
            style={oneDark} 
            language="typescript" 
            PreTag="div" 
            customStyle={{ margin: 0, padding: 0, fontSize: "0.85rem" }}
          >
            {code}
          </SyntaxHighlighter>
        )}
      </div>
    </aside>
  );
}
