import type { Repository } from "../../types/api";

type Props = { repositories: Repository[]; selectedRepositoryId: string | null; onSelect: (id: string) => void };

export function RepositorySidebar({ repositories, selectedRepositoryId, onSelect }: Props) {
  return (
    <nav aria-label="Repositories" className="repo-nav">
      <div className="repo-list">
        {repositories.map(repository => (
          <button 
            className={repository.id === selectedRepositoryId ? "selected" : ""} 
            key={repository.id} 
            onClick={() => onSelect(repository.id)}
          >
            <span className="repo-name">{repository.name}</span>
            <small className="repo-status" aria-hidden="true">
              {repository.status}
            </small>
          </button>
        ))}
      </div>
    </nav>
  );
}
