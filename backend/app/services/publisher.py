from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from ..core.config import get_settings
from ..models import Finding, GitHubPublication, ReviewRun
from .github import GitHubAppClient

EVENT_MAP = {"comment": "COMMENT", "request_changes": "REQUEST_CHANGES", "approve": "APPROVE"}


def publish_review(db: Session, review_run_id: int, review_decision: str = "comment", include_summary: bool = True, dry_run: bool = True) -> list[GitHubPublication]:
    run = db.query(ReviewRun).filter(ReviewRun.id == review_run_id).first()
    if not run:
        raise ValueError("Review run not found")
    approved = db.query(Finding).filter(
        Finding.review_run_id == run.id,
        Finding.status.in_(["approved", "edited", "internal_note"]),
    ).all()
    inline = [f for f in approved if f.publish_recommendation == "inline" and f.status != "internal_note"]
    body_parts: list[str] = []
    if include_summary:
        body_parts.append(
            f"## AI DevOps Review\n\nRisk score: **{run.risk_score}/100**\n\n"
            f"Recommendation: **{run.merge_recommendation.replace('_', ' ').title()}**\n\n{run.final_summary}"
        )
    body_parts.extend(
        f"- **{f.severity.upper()} · {f.category}** — {f.edited_content or f.title}: {f.suggested_fix}"
        for f in approved
        if f.publish_recommendation != "inline"
    )
    payload = {
        "body": "\n".join(body_parts) or "Approved review findings.",
        "event": EVENT_MAP.get(review_decision, "COMMENT"),
        "commit_id": run.commit_sha,
        "comments": [
            {
                "path": f.file_path,
                "line": f.end_line,
                "side": "RIGHT",
                "body": f.edited_content or f"**{f.title}**\n\n{f.explanation}\n\nSuggested change: {f.suggested_fix}",
            }
            for f in inline
        ],
    }
    publication = GitHubPublication(review_run_id=run.id, comment_type="review", status="pending", payload=payload)
    db.add(publication)
    db.flush()
    settings = get_settings()
    try:
        if dry_run or settings.demo_mode:
            publication.status = "simulated"
            publication.github_comment_id = f"demo-review-{publication.id}"
        else:
            pr = run.pull_request
            repo = pr.repository
            result = GitHubAppClient().publish_review(repo.owner, repo.name, pr.github_number, payload)
            publication.status = "published"
            publication.github_comment_id = str(result.get("id"))
        publication.published_at = datetime.now(timezone.utc)
        for finding in approved:
            if finding.status != "internal_note":
                finding.status = "published"
                finding.published_comment_id = publication.github_comment_id
        run.status = "published"
        run.pull_request.review_status = "published"
        db.commit()
        db.refresh(publication)
        return [publication]
    except Exception as exc:
        publication.status = "failed"
        publication.error_details = str(exc)
        db.commit()
        raise
