from __future__ import annotations
import base64
import io
import fnmatch
import shutil
import tarfile
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from .github import GitHubAppClient

CONTEXT_FILES = [
    "README.md", "CONTRIBUTING.md", "SECURITY.md", ".github/copilot-instructions.md",
    "pyproject.toml", "requirements.txt", "package.json", "composer.json", "pom.xml",
    "Dockerfile", "docker-compose.yml",
]


def safe_extract_tar(archive_bytes: bytes, destination: Path) -> Path:
    """Extract a GitHub archive while rejecting traversal and link entries."""
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            if member.issym() or member.islnk():
                raise ValueError("Archive links are not permitted")
            target = (destination / member.name).resolve()
            if not target.is_relative_to(destination):
                raise ValueError("Archive path traversal detected")
        archive.extractall(destination, members=members, filter="data")
    roots = [item for item in destination.iterdir() if item.is_dir()]
    return roots[0] if len(roots) == 1 else destination


class RepositoryContextCollector:
    def __init__(self, client: GitHubAppClient | None = None) -> None:
        self.client = client or GitHubAppClient()

    def collect_pull_request(self, owner: str, repo: str, number: int, ignored_paths: list[str] | None = None) -> dict:
        pr = self.client.fetch_pull_request(owner, repo, number)
        files = self.client.fetch_files(owner, repo, number)
        commits = self.client.fetch_commits(owner, repo, number)
        context_documents: dict[str, str] = {}
        for path in CONTEXT_FILES:
            try:
                item = self.client.fetch_repository_content(owner, repo, path, pr["base"]["sha"])
                if item.get("encoding") == "base64" and item.get("content"):
                    context_documents[path] = base64.b64decode(item["content"]).decode("utf-8", errors="replace")[:40_000]
            except Exception:
                continue
        ignored_paths = ignored_paths or []
        def included(filename: str) -> bool:
            return not any(fnmatch.fnmatch(filename, pattern) for pattern in ignored_paths)

        normalized_files = [
            {
                "filename": item.get("filename"),
                "status": item.get("status"),
                "additions": item.get("additions", 0),
                "deletions": item.get("deletions", 0),
                "changes": item.get("changes", 0),
                "patch": (item.get("patch") or "")[:80_000],
            }
            for item in files
            if included(item.get("filename", "")) and not item.get("filename", "").lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".jar"))
        ]
        diff_text = "\n\n".join(f"diff --git a/{f['filename']} b/{f['filename']}\n{f['patch']}" for f in normalized_files if f["patch"])
        return {
            "title": pr.get("title", "Untitled pull request"),
            "description": pr.get("body") or "",
            "author": (pr.get("user") or {}).get("login", "unknown"),
            "base_branch": (pr.get("base") or {}).get("ref", "main"),
            "head_branch": (pr.get("head") or {}).get("ref", "feature"),
            "current_commit_sha": (pr.get("head") or {}).get("sha", "unknown"),
            "changed_files_count": len(normalized_files),
            "additions": pr.get("additions", 0),
            "deletions": pr.get("deletions", 0),
            "changed_files": normalized_files,
            "commits": [{"sha": c.get("sha"), "message": (c.get("commit") or {}).get("message", "")} for c in commits],
            "diff_text": diff_text,
            "repository_context": context_documents,
        }

    @contextmanager
    def workspace(self, owner: str, repo: str, commit_sha: str) -> Iterator[Path]:
        temp_root = Path(tempfile.mkdtemp(prefix="sentinel-review-"))
        try:
            archive = self.client.download_archive(owner, repo, commit_sha)
            yield safe_extract_tar(archive, temp_root)
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)
