from __future__ import annotations
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(StrEnum):
    PLATFORM_ADMIN = "platform_admin"
    ENGINEERING_MANAGER = "engineering_manager"
    REPOSITORY_MAINTAINER = "repository_maintainer"
    DEVELOPER = "developer"
    AUDITOR = "auditor"


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="active")
    github_installation_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    users: Mapped[list[User]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    repositories: Mapped[list[Repository]] = relationship(back_populates="organization", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(500))
    role: Mapped[str] = mapped_column(String(50), default=UserRole.DEVELOPER.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    organization: Mapped[Organization] = relationship(back_populates="users")


class Repository(Base):
    __tablename__ = "repositories"
    __table_args__ = (UniqueConstraint("organization_id", "owner", "name", name="uq_org_repository"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    github_repository_id: Mapped[str | None] = mapped_column(String(100))
    owner: Mapped[str] = mapped_column(String(150))
    name: Mapped[str] = mapped_column(String(150))
    default_branch: Mapped[str] = mapped_column(String(100), default="main")
    primary_language: Mapped[str] = mapped_column(String(50), default="Python")
    visibility: Mapped[str] = mapped_column(String(30), default="private")
    connection_status: Mapped[str] = mapped_column(String(30), default="connected")
    webhook_status: Mapped[str] = mapped_column(String(30), default="active")
    active_review_profile: Mapped[str] = mapped_column(String(80), default="standard_application")
    last_synchronized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    organization: Mapped[Organization] = relationship(back_populates="repositories")
    policy: Mapped[RepositoryPolicy | None] = relationship(back_populates="repository", uselist=False, cascade="all, delete-orphan")
    pull_requests: Mapped[list[PullRequest]] = relationship(back_populates="repository", cascade="all, delete-orphan")


class RepositoryPolicy(Base):
    __tablename__ = "repository_policies"
    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), unique=True)
    review_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    review_profile: Mapped[str] = mapped_column(String(80), default="standard_application")
    monitored_branches: Mapped[list[str]] = mapped_column(JSON, default=lambda: ["main", "develop"])
    ignored_paths: Mapped[list[str]] = mapped_column(JSON, default=lambda: ["vendor/**", "node_modules/**", "dist/**"])
    analyzer_settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    maximum_diff_size: Mapped[int] = mapped_column(Integer, default=5000)
    minimum_severity: Mapped[str] = mapped_column(String(20), default="medium")
    security_checks: Mapped[bool] = mapped_column(Boolean, default=True)
    test_review: Mapped[bool] = mapped_column(Boolean, default=True)
    documentation_review: Mapped[bool] = mapped_column(Boolean, default=True)
    approval_required: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_post_summary: Mapped[bool] = mapped_column(Boolean, default=False)
    re_review_on_push: Mapped[bool] = mapped_column(Boolean, default=True)
    repository: Mapped[Repository] = relationship(back_populates="policy")


class PullRequest(Base):
    __tablename__ = "pull_requests"
    __table_args__ = (UniqueConstraint("repository_id", "github_number", name="uq_repo_pr_number"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), index=True)
    github_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    author: Mapped[str] = mapped_column(String(150))
    base_branch: Mapped[str] = mapped_column(String(100))
    head_branch: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(30), default="open")
    current_commit_sha: Mapped[str] = mapped_column(String(64))
    changed_files_count: Mapped[int] = mapped_column(Integer, default=0)
    additions: Mapped[int] = mapped_column(Integer, default=0)
    deletions: Mapped[int] = mapped_column(Integer, default=0)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_level: Mapped[str] = mapped_column(String(20), default="low")
    analysis_status: Mapped[str] = mapped_column(String(50), default="pending_analysis")
    review_status: Mapped[str] = mapped_column(String(50), default="pending_analysis")
    assigned_reviewer: Mapped[str | None] = mapped_column(String(255))
    changed_files: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    commits: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    diff_text: Mapped[str] = mapped_column(Text, default="")
    repository_context: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    repository: Mapped[Repository] = relationship(back_populates="pull_requests")
    review_runs: Mapped[list[ReviewRun]] = relationship(back_populates="pull_request", cascade="all, delete-orphan")


class ReviewRun(Base):
    __tablename__ = "review_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    pull_request_id: Mapped[int] = mapped_column(ForeignKey("pull_requests.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    commit_sha: Mapped[str] = mapped_column(String(64))
    trigger_event: Mapped[str] = mapped_column(String(80), default="pull_request.opened")
    status: Mapped[str] = mapped_column(String(50), default="pending_analysis")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    analysis_duration_ms: Mapped[int | None] = mapped_column(Integer)
    final_summary: Mapped[str] = mapped_column(Text, default="")
    merge_recommendation: Mapped[str] = mapped_column(String(80), default="analysis_incomplete")
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_factors: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    pull_request: Mapped[PullRequest] = relationship(back_populates="review_runs")
    findings: Mapped[list[Finding]] = relationship(back_populates="review_run", cascade="all, delete-orphan")
    analyzer_runs: Mapped[list[AnalyzerRun]] = relationship(back_populates="review_run", cascade="all, delete-orphan")
    test_recommendations: Mapped[list[TestRecommendation]] = relationship(back_populates="review_run", cascade="all, delete-orphan")
    documentation_recommendations: Mapped[list[DocumentationRecommendation]] = relationship(back_populates="review_run", cascade="all, delete-orphan")


class AnalyzerRun(Base):
    __tablename__ = "analyzer_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    review_run_id: Mapped[int] = mapped_column(ForeignKey("review_runs.id"), index=True)
    tool_name: Mapped[str] = mapped_column(String(80))
    tool_version: Mapped[str] = mapped_column(String(50), default="simulated")
    status: Mapped[str] = mapped_column(String(30), default="completed")
    output: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    error_details: Mapped[str | None] = mapped_column(Text)
    review_run: Mapped[ReviewRun] = relationship(back_populates="analyzer_runs")


class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[int] = mapped_column(primary_key=True)
    review_run_id: Mapped[int] = mapped_column(ForeignKey("review_runs.id"), index=True)
    source: Mapped[str] = mapped_column(String(80))
    sources: Mapped[list[str]] = mapped_column(JSON, default=list)
    category: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    title: Mapped[str] = mapped_column(String(300))
    explanation: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str] = mapped_column(Text, default="")
    file_path: Mapped[str] = mapped_column(String(500))
    start_line: Mapped[int] = mapped_column(Integer, default=1)
    end_line: Mapped[int] = mapped_column(Integer, default=1)
    code_snippet: Mapped[str] = mapped_column(Text, default="")
    suggested_fix: Mapped[str] = mapped_column(Text, default="")
    publish_recommendation: Mapped[str] = mapped_column(String(30), default="inline")
    status: Mapped[str] = mapped_column(String(40), default="awaiting_review")
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    reviewer_comment: Mapped[str | None] = mapped_column(Text)
    edited_content: Mapped[str | None] = mapped_column(Text)
    published_comment_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    review_run: Mapped[ReviewRun] = relationship(back_populates="findings")
    decisions: Mapped[list[FindingDecision]] = relationship(back_populates="finding", cascade="all, delete-orphan")


class FindingDecision(Base):
    __tablename__ = "finding_decisions"
    id: Mapped[int] = mapped_column(primary_key=True)
    finding_id: Mapped[int] = mapped_column(ForeignKey("findings.id"), index=True)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    decision: Mapped[str] = mapped_column(String(50))
    edited_content: Mapped[str | None] = mapped_column(Text)
    comment: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finding: Mapped[Finding] = relationship(back_populates="decisions")


class TestRecommendation(Base):
    __tablename__ = "test_recommendations"
    id: Mapped[int] = mapped_column(primary_key=True)
    review_run_id: Mapped[int] = mapped_column(ForeignKey("review_runs.id"), index=True)
    test_type: Mapped[str] = mapped_column(String(60))
    target_module: Mapped[str] = mapped_column(String(300))
    scenario: Mapped[str] = mapped_column(Text)
    expected_result: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    status: Mapped[str] = mapped_column(String(30), default="recommended")
    review_run: Mapped[ReviewRun] = relationship(back_populates="test_recommendations")


class DocumentationRecommendation(Base):
    __tablename__ = "documentation_recommendations"
    id: Mapped[int] = mapped_column(primary_key=True)
    review_run_id: Mapped[int] = mapped_column(ForeignKey("review_runs.id"), index=True)
    document_type: Mapped[str] = mapped_column(String(60))
    reason: Mapped[str] = mapped_column(Text)
    suggested_update: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    review_run: Mapped[ReviewRun] = relationship(back_populates="documentation_recommendations")


class GitHubPublication(Base):
    __tablename__ = "github_publications"
    id: Mapped[int] = mapped_column(primary_key=True)
    review_run_id: Mapped[int] = mapped_column(ForeignKey("review_runs.id"), index=True)
    finding_id: Mapped[int | None] = mapped_column(ForeignKey("findings.id"))
    comment_type: Mapped[str] = mapped_column(String(30))
    github_comment_id: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="pending")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_details: Mapped[str | None] = mapped_column(Text)


class SuppressionRule(Base):
    __tablename__ = "suppression_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), index=True)
    rule_type: Mapped[str] = mapped_column(String(30))
    rule_identifier: Mapped[str] = mapped_column(String(120))
    file_pattern: Mapped[str | None] = mapped_column(String(500))
    reason: Mapped[str] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(60))
    title: Mapped[str] = mapped_column(String(250))
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    related_review_id: Mapped[int | None] = mapped_column(ForeignKey("review_runs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    repository_id: Mapped[int | None] = mapped_column(ForeignKey("repositories.id"), index=True)
    pull_request_id: Mapped[int | None] = mapped_column(ForeignKey("pull_requests.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(100))
    old_value: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    new_value: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    result: Mapped[str] = mapped_column(String(30), default="success")
    ip_address: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    delivery_id: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    event_name: Mapped[str] = mapped_column(String(80))
    action: Mapped[str | None] = mapped_column(String(80))
    repository_full_name: Mapped[str | None] = mapped_column(String(300))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="received")
    error_details: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
