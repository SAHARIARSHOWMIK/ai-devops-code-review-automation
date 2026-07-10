import io
import tarfile
from pathlib import Path
import pytest
from app.services.context_collector import safe_extract_tar
from app.services.analyzers import run_language_analyzers


def archive_with(name: str, content: bytes = b"hello", kind: str = "file") -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        info = tarfile.TarInfo(name)
        if kind == "symlink":
            info.type = tarfile.SYMTYPE
            info.linkname = "/etc/passwd"
            archive.addfile(info)
        else:
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
    return stream.getvalue()


def test_safe_extract_tar_accepts_regular_files(tmp_path: Path):
    root = safe_extract_tar(archive_with("repo-main/app.py", b"print('ok')"), tmp_path)
    assert (root / "app.py").read_text() == "print('ok')"


def test_safe_extract_tar_rejects_traversal(tmp_path: Path):
    with pytest.raises(ValueError, match="traversal"):
        safe_extract_tar(archive_with("../outside.txt"), tmp_path)


def test_safe_extract_tar_rejects_links(tmp_path: Path):
    with pytest.raises(ValueError, match="links"):
        safe_extract_tar(archive_with("repo-main/link", kind="symlink"), tmp_path)


def test_workspace_analyzer_falls_back_when_disabled(tmp_path: Path):
    results = run_language_analyzers("Python", '+password = "fake-demo-password"', [{"filename": "app.py"}], workspace=tmp_path)
    assert results
    assert all(row.output["execution_mode"] == "safe_adapter" for row in results)


def test_binary_paths_are_not_needed_for_diff_rules():
    results = run_language_analyzers("Unknown", "+safe_change = True", [{"filename": "asset.png"}])
    assert len(results) == 1
    assert results[0].tool_name == "generic-static-review"
