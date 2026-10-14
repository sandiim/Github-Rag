"""Rules for selecting useful repository text files."""

from pathlib import PurePosixPath

MAX_FILE_BYTES = 500_000
INDEX_POLICY_VERSION = 3
ALLOWED_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".md", ".rmd", ".json", ".yaml", ".yml", ".toml"}
EXCLUDED_DIRECTORIES = {
    ".git", "node_modules", "dist", "build", "coverage", ".venv", "venv", "vendor", "mlruns",
    "data", "datasets",
}
EXCLUDED_FILENAMES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock"}


def should_index(path: str, content: str) -> bool:
    """Return whether a repository text file is suitable for indexing."""

    file_path = PurePosixPath(path)
    if any(part in EXCLUDED_DIRECTORIES for part in file_path.parts):
        return False
    if file_path.name in EXCLUDED_FILENAMES or file_path.name.endswith(".min.js"):
        return False
    if len(content.encode("utf-8")) > MAX_FILE_BYTES or "\x00" in content:
        return False
    return file_path.name == "Dockerfile" or file_path.suffix.lower() in ALLOWED_SUFFIXES
