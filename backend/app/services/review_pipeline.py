from __future__ import annotations
import time
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.orm import Session
from ..models import (
    AnalyzerRun,
    DocumentationRecommendation,
    Finding,
    PullRequest,
    ReviewRun,
    TestRecommendation,
)
from .ai_review import review_context
from .analyzers import AnalyzerResult, run_language_analyzers
from .context_collector import RepositoryContextCollector
from .github import GitHubAppClient
from ..core.config import get_settings
from .deduplication import deduplicate
from .notifications import notify_role
from .risk_engine import calculate_risk


def _organization_id(pr: PullRequest) -> int:
    return pr.repository.organization_id


def execute_review(
    db: Session, pull_request_id: int, trigger_event: str = "manual"
) -> ReviewRun:
    pr = db.query(PullRequest).filter(PullRequest.id == pull_request_id).first()
    if not pr:
        raise ValueError("Pull request not found")
    previous_runs = (
        db.query(ReviewRun)
        .filter(ReviewRun.pull_request_id == pr.id)
        .order_by(ReviewRun.version.desc())
        .all()
    )
    version = previous_runs[0].version + 1 if previous_runs else 1
    run = ReviewRun(
        pull_request_id=pr.id,
        version=version,
        commit_sha=pr.current_commit_sha,
        trigger_event=trigger_event,
        status="analysis_running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.flush()
    pr.analysis_status = "analysis_running"
    pr.review_status = "analysis_running"
    db.commit()
    db.refresh(run)
    started = time.perf_counter()
    try:
        language = pr.repository.primary_language
        settings = get_settings()
        analyzer_results = []
        if not settings.demo_mode and GitHubAppClient().configured:
            try:
                with RepositoryContextCollector().workspace(
                    pr.repository.owner, pr.repository.name, pr.current_commit_sha
                ) as workspace:
                    analyzer_results = run_language_analyzers(
                        language,
                        pr.diff_text or "",
                        pr.changed_files or [],
                        workspace=workspace,
                    )
            except Exception as exc:
                analyzer_results = run_language_analyzers(
                    language, pr.diff_text or "", pr.changed_files or []
                )
                analyzer_results.append(
                    AnalyzerResult(
                        tool_name="repository-context-collector",
                        tool_version="1.0",
                        status="failed",
                        duration_ms=0,
                        findings=[],
                        output={"fallback": "diff_only"},
                        error_details=str(exc),
                    )
                )
        else:
            analyzer_results = run_language_analyzers(
                language, pr.diff_text or "", pr.changed_files or []
            )
        raw_findings: list[dict] = []
        for result in analyzer_results:
            db.add(
                AnalyzerRun(
                    review_run_id=run.id,
                    tool_name=result.tool_name,
                    tool_version=result.tool_version,
                    status=result.status,
                    output=result.output,
                    duration_ms=result.duration_ms,
                    error_details=result.error_details,
                )
            )
            raw_findings.extend(result.findings)

        context: dict[str, Any] = {
            "github_number": pr.github_number,
            "title": pr.title,
            "description": pr.description,
            "base_branch": pr.base_branch,
            "head_branch": pr.head_branch,
            "changed_files": pr.changed_files,
            "commits": pr.commits,
            "diff_text": pr.diff_text,
            "repository": f"{pr.repository.owner}/{pr.repository.name}",
            "language": language,
            "review_profile": pr.repository.active_review_profile,
            "repository_context": pr.repository_context or {},
            "previous_unresolved_findings": [
                f.title
                for old in previous_runs[:1]
                for f in old.findings
                if f.status not in {"fixed", "dismissed", "false_positive", "outdated"}
            ],
        }
        policy = pr.repository.policy
        if policy and (pr.additions + pr.deletions) > policy.maximum_diff_size:
            context["diff_text"] = (context["diff_text"] or "")[
                : get_settings().max_diff_characters
            ]
            context["analysis_note"] = (
                "Diff exceeded repository policy and was truncated for bounded analysis."
            )
        ai_output = review_context(context)
        ai_findings = [
            item.model_dump() for item in ai_output.findings if item.confidence >= 0.65
        ]
        if policy and not policy.security_checks:
            raw_findings = [
                item for item in raw_findings if item.get("category") != "security"
            ]
            ai_findings = [
                item for item in ai_findings if item.get("category") != "security"
            ]
        raw_findings.extend(ai_findings)
        normalized = deduplicate(raw_findings)

        previous_fingerprints = {
            f.fingerprint: f for old in previous_runs[:1] for f in old.findings
        }
        new_fingerprints = {f["fingerprint"] for f in normalized}
        for old_fp, old_finding in previous_fingerprints.items():
            if old_finding.status not in {"dismissed", "false_positive", "suppressed"}:
                old_finding.status = (
                    "still_present" if old_fp in new_fingerprints else "fixed"
                )

        created_findings: list[Finding] = []
        for data in normalized:
            finding = Finding(
                review_run_id=run.id,
                source=data.get("source", "unknown"),
                sources=data.get("sources", [data.get("source", "unknown")]),
                category=data.get("category", "maintainability"),
                severity=data.get("severity", "low"),
                confidence=float(data.get("confidence", 0.7)),
                title=data.get("title", "Review finding"),
                explanation=data.get("explanation", ""),
                evidence=data.get("evidence", ""),
                file_path=data.get("file_path", "unknown"),
                start_line=max(1, int(data.get("start_line", 1))),
                end_line=max(1, int(data.get("end_line", data.get("start_line", 1)))),
                code_snippet=data.get("code_snippet", ""),
                suggested_fix=data.get("suggested_fix", ""),
                publish_recommendation=data.get("publish_recommendation", "inline"),
                status="awaiting_review",
                fingerprint=data["fingerprint"],
            )
            db.add(finding)
            created_findings.append(finding)

        test_rows: list[TestRecommendation] = []
        for item in (
            ai_output.test_recommendations if not policy or policy.test_review else []
        ):
            row = TestRecommendation(review_run_id=run.id, **item)
            db.add(row)
            test_rows.append(row)
        for item in (
            ai_output.documentation_recommendations
            if not policy or policy.documentation_review
            else []
        ):
            db.add(DocumentationRecommendation(review_run_id=run.id, **item))

        risk = calculate_risk(pr, created_findings, test_rows)
        run.status = "awaiting_human_review"
        run.final_summary = ai_output.summary
        run.risk_score = risk.score
        run.risk_factors = risk.factors
        run.merge_recommendation = risk.recommendation
        run.completed_at = datetime.now(timezone.utc)
        run.analysis_duration_ms = max(1, int((time.perf_counter() - started) * 1000))
        pr.risk_score = risk.score
        pr.risk_level = risk.level
        pr.analysis_status = "completed"
        pr.review_status = "awaiting_human_review"
        if risk.level in {"high", "critical"}:
            notify_role(
                db,
                _organization_id(pr),
                {"platform_admin", "engineering_manager", "repository_maintainer"},
                f"{risk.level.title()}-risk PR detected",
                f"{pr.repository.owner}/{pr.repository.name} PR #{pr.github_number} scored {risk.score}/100.",
                "high_risk_pr",
                run.id,
            )
        notify_role(
            db,
            _organization_id(pr),
            {"engineering_manager", "repository_maintainer"},
            "Review ready for approval",
            f"PR #{pr.github_number} has {len(created_findings)} finding(s) awaiting review.",
            "review_ready",
            run.id,
        )
        db.commit()
        db.refresh(run)
        return run
    except Exception as exc:
        db.rollback()
        failed_run = db.query(ReviewRun).filter(ReviewRun.id == run.id).first()
        pr = db.query(PullRequest).filter(PullRequest.id == pull_request_id).first()
        if failed_run:
            failed_run.status = "failed"
            failed_run.failure_reason = str(exc)
            failed_run.completed_at = datetime.now(timezone.utc)
        if pr:
            pr.analysis_status = "failed"
            pr.review_status = "failed"
            notify_role(
                db,
                pr.repository.organization_id,
                {"platform_admin", "repository_maintainer"},
                "Pull-request analysis failed",
                f"Analysis for PR #{pr.github_number} failed: {exc}",
                "analysis_failed",
                failed_run.id if failed_run else None,
            )
        db.commit()
        raise
