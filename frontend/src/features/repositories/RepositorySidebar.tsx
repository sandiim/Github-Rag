import type { Repository } from "../../types/api";

type Props = { repositories: Repository[]; selectedRepositoryId: string | null; onSelect: (id: string) => void };

export function RepositorySidebar({ repositories, selectedRepositoryId, onSelect }: Props) {
  return <nav aria-label="Repositories"><h1>Repository RAG</h1><p>Saved repositories</p>{repositories.map(repository => <button className={repository.id === selectedRepositoryId ? "selected" : ""} key={repository.id} onClick={() => onSelect(repository.id)}>{repository.name}<small aria-hidden="true">{repository.status}</small></button>)}</nav>;
}
