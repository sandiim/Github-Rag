import type { Citation } from "../../types/api";
export function CitationList({ citations }: { citations: Citation[] }) { return <ul className="citations">{citations.map(citation => <li key={citation.url}><a href={citation.url} target="_blank" rel="noreferrer">{citation.path}:{citation.startLine}-{citation.endLine}</a></li>)}</ul>; }
