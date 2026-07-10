from __future__ import annotations
import hashlib
import hmac
import time
from pathlib import Path
import httpx
import jwt
from ..core.config import get_settings


def verify_webhook_signature(body: bytes, signature_header: str | None) -> bool:
    settings = get_settings()
    if settings.demo_mode and not signature_header:
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(settings.github_webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature_header.removeprefix("sha256="), expected)


class GitHubAppClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def configured(self) -> bool:
        return bool(self.settings.github_app_id and self.settings.github_installation_id and self.settings.github_private_key_path)

    def _app_jwt(self) -> str:
        path = Path(self.settings.github_private_key_path or "")
        if not path.exists():
            raise RuntimeError("GitHub App private key file not found")
        now = int(time.time())
        return jwt.encode({"iat": now - 30, "exp": now + 540, "iss": self.settings.github_app_id}, path.read_text(), algorithm="RS256")

    def installation_token(self) -> str:
        if not self.configured:
            raise RuntimeError("GitHub App is not configured")
        response = httpx.post(
            f"{self.settings.github_api_url}/app/installations/{self.settings.github_installation_id}/access_tokens",
            headers={"Authorization": f"Bearer {self._app_jwt()}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["token"]

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.installation_token()}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}

    def fetch_pull_request(self, owner: str, repo: str, number: int) -> dict:
        response = httpx.get(f"{self.settings.github_api_url}/repos/{owner}/{repo}/pulls/{number}", headers=self._headers(), timeout=30)
        response.raise_for_status(); return response.json()

    def fetch_files(self, owner: str, repo: str, number: int) -> list[dict]:
        response = httpx.get(f"{self.settings.github_api_url}/repos/{owner}/{repo}/pulls/{number}/files", headers=self._headers(), timeout=30)
        response.raise_for_status(); return response.json()

    def fetch_commits(self, owner: str, repo: str, number: int) -> list[dict]:
        response = httpx.get(f"{self.settings.github_api_url}/repos/{owner}/{repo}/pulls/{number}/commits", headers=self._headers(), timeout=30)
        response.raise_for_status(); return response.json()

    def fetch_repository_content(self, owner: str, repo: str, path: str, ref: str) -> dict:
        response = httpx.get(f"{self.settings.github_api_url}/repos/{owner}/{repo}/contents/{path}", headers=self._headers(), params={"ref": ref}, timeout=30)
        response.raise_for_status(); return response.json()

    def download_archive(self, owner: str, repo: str, ref: str) -> bytes:
        response = httpx.get(f"{self.settings.github_api_url}/repos/{owner}/{repo}/tarball/{ref}", headers=self._headers(), timeout=120, follow_redirects=True)
        response.raise_for_status(); return response.content

    def publish_review(self, owner: str, repo: str, number: int, payload: dict) -> dict:
        response = httpx.post(f"{self.settings.github_api_url}/repos/{owner}/{repo}/pulls/{number}/reviews", headers=self._headers(), json=payload, timeout=30)
        response.raise_for_status(); return response.json()
