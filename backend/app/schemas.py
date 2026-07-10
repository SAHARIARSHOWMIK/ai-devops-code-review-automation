from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


class OrganizationOut(ORMModel):
    id: int
    name: str
    status: str
    github_installation_id: str | None
    created_at: datetime


class UserOut(ORMModel):
    id: int
    organization_id: int
    name: str
    email: EmailStr
    role: str
    is_active: bool
    last_login: datetime | None


class RepositoryCreate(BaseModel):
    owner: str = Field(min_length=1, max_length=150)
    name: str = Field(min_length=1, max_length=150)
    default_branch: str = "main"
    primary_language: str = "Python"
    visibility: str = "private"
    github_repository_id: str | None = None
    active_review_profile: str = "standard_application"


class RepositoryOut(ORMModel):
    id: int
    organization_id: int
    owner: str
    name: str
    default_branch: str
    primary_language: str
    visibility: str
    connection_status: str
    webhook_status: str
    active_review_profile: str
    last_synchronized_at: datetime | None


class PolicyUpdate(BaseModel):
    review_enabled: bool = True
    review_profile: str = "standard_application"
    monitored_branches: list[str] = Field(default_factory=lambda: ["main", "develop"])
    ignored_paths: list[str] = Field(default_factory=lambda: ["vendor/**", "node_modules/**", "dist/**"])
    analyzer_settings: dict[str, Any] = Field(default_factory=dict)
    maximum_diff_size: int = Field(default=5000, ge=100, le=100000)
    minimum_severity: Literal["info", "low", "medium", "high", "critical"] = "medium"
    security_checks: bool = True
    test_review: bool = True
    documentation_review: bool = True
    approval_required: bool = True
    auto_post_summary: bool = False
    re_review_on_push: bool = True


class PolicyOut(ORMModel):
    id: int
    repository_id: int
    review_enabled: bool
    review_profile: str
    monitored_branches: list[str]
    ignored_paths: list[str]
    analyzer_settings: dict[str, Any]
    maximum_diff_size: int
    minimum_severity: str
    security_checks: bool
    test_review: bool
    documentation_review: bool
    approval_required: bool
    auto_post_summary: bool
    re_review_on_push: bool


class PullRequestCreate(BaseModel):
    repository_id: int
    github_number: int
    title: str
    description: str = ""
    author: str
    base_branch: str = "main"
    head_branch: str
    current_commit_sha: str
    changed_files_count: int = 0
    additions: int = 0
    deletions: int = 0
    changed_files: list[dict[str, Any]] = Field(default_factory=list)
    commits: list[dict[str, Any]] = Field(default_factory=list)
    diff_text: str = ""
    repository_context: dict[str, str] = Field(default_factory=dict)


class PullRequestOut(ORMModel):
    id: int
    repository_id: int
    github_number: int
    title: str
    description: str
    author: str
    base_branch: str
    head_branch: str
    state: str
    current_commit_sha: str
    changed_files_count: int
    additions: int
    deletions: int
    risk_score: int
    risk_level: str
    analysis_status: str
    review_status: str
    assigned_reviewer: str | None
    changed_files: list[dict[str, Any]]
    repository_context: dict[str, str]
    created_at: datetime
    updated_at: datetime


class FindingOut(ORMModel):
    id: int
    review_run_id: int
    source: str
    sources: list[str]
    category: str
    severity: str
    confidence: float
    title: str
    explanation: str
    evidence: str
    file_path: str
    start_line: int
    end_line: int
    code_snippet: str
    suggested_fix: str
    publish_recommendation: str
    status: str
    fingerprint: str
    reviewer_comment: str | None
    edited_content: str | None
    published_comment_id: str | None


class FindingDecisionRequest(BaseModel):
    decision: Literal["approve", "edit", "dismiss", "false_positive", "suppress", "internal_note", "fixed", "reopen"]
    edited_content: str | None = None
    comment: str | None = None
    create_suppression: bool = False


class ReviewRunOut(ORMModel):
    id: int
    pull_request_id: int
    version: int
    commit_sha: str
    trigger_event: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    analysis_duration_ms: int | None
    final_summary: str
    merge_recommendation: str
    risk_score: int
    risk_factors: list[dict[str, Any]]
    failure_reason: str | None


class AnalyzeRequest(BaseModel):
    trigger_event: str = "manual"
    force: bool = False


class PublishRequest(BaseModel):
    review_decision: Literal["comment", "request_changes", "approve"] = "comment"
    include_summary: bool = True
    dry_run: bool = True


class SuppressionCreate(BaseModel):
    rule_type: str
    rule_identifier: str
    file_pattern: str | None = None
    reason: str
    expires_at: datetime | None = None


class WebhookResponse(BaseModel):
    accepted: bool
    delivery_id: str
    status: str
    detail: str


class AnalyticsSummary(BaseModel):
    connected_repositories: int
    open_pull_requests: int
    awaiting_approval: int
    high_risk_pull_requests: int
    critical_findings: int
    published_reviews: int
    failed_analysis_jobs: int
    average_review_duration_ms: int
    most_common_category: str | None
    false_positive_rate: float


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int
