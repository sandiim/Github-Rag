import pytest

from app.rag.file_filter import should_index


@pytest.mark.parametrize("path", ["src/app.py", "README.md", "config/app.yaml", "Dockerfile"])
def test_allowlisted_text_files_are_indexed(path: str) -> None:
    assert should_index(path, "meaningful text") is True


@pytest.mark.parametrize(
    "path",
    [
        "node_modules/a.js",
        "dist/app.min.js",
        "package-lock.json",
        ".git/config",
        "venv/Lib/site-packages/pkg/module.py",
        "mlruns/1/metadata.json",
        "data/sofascore/matches/round_17.json",
        "datasets/train.json",
    ],
)
def test_generated_or_dependency_files_are_excluded(path: str) -> None:
    assert should_index(path, "meaningful text") is False
