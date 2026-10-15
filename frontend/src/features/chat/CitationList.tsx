import type { Citation } from "../../types/api";

export function CitationList({ citations }: { citations: Citation[] }) { 
  if (!citations || citations.length === 0) return null;
  
  return (
    <ul className="citations">
      {citations.map((citation, index) => (
        <li key={citation.url}>
          <a 
            href={citation.url} 
            target="_blank" 
            rel="noreferrer" 
            className="citation-item"
          >
            <span className="citation-index">[{index + 1}]</span>
            <span className="citation-path">{citation.path}</span>
            <span className="citation-range">L{citation.startLine}-{citation.endLine}</span>
          </a>
        </li>
      ))}
    </ul>
  ); 
}
