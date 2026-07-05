import pytest

from app.core.exceptions import MarkdownProcessingException
from app.dal.files.markdown_reader import read_markdown_documents


@pytest.mark.asyncio
async def test_read_markdown_documents_returns_relative_paths_and_ignores_git(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wiki_root = tmp_path / "wikis"
    wiki_root.mkdir()
    (wiki_root / "guide.md").write_text("Guide", encoding="utf-8")
    nested = wiki_root / "nested"
    nested.mkdir()
    (nested / "page.md").write_text("Page", encoding="utf-8")
    git_dir = wiki_root / ".git"
    git_dir.mkdir()
    (git_dir / "ignored.md").write_text("Ignored", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = await read_markdown_documents()

    documents_by_path = {document.path: document.content for document in result.documents}
    assert documents_by_path == {"guide.md": "Guide", "nested/page.md": "Page"}


@pytest.mark.asyncio
async def test_read_markdown_documents_wraps_read_errors(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wiki_root = tmp_path / "wikis"
    wiki_root.mkdir()
    broken_file = wiki_root / "broken.md"
    broken_file.write_text("Broken", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    class FailingOpen:
        async def __aenter__(self):
            raise OSError("cannot read")

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    def failing_open(*args, **kwargs):
        return FailingOpen()

    monkeypatch.setattr("app.dal.files.markdown_reader.aiofiles.open", failing_open)

    with pytest.raises(MarkdownProcessingException) as exc_info:
        await read_markdown_documents()

    assert exc_info.value.details["file"].endswith("broken.md")
