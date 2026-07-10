from __future__ import annotations
import json
import httpx
from pydantic import BaseModel, Field, ValidationError
from ..core.config import get_settings
from .deduplication import fingerprint_finding


class StructuredFinding(BaseModel):
    source: str = "ai"
    sources: list[str] = Field(default_factory=lambda: ["ai"])
    category: str
    severity: str
    confidence: float = Field(ge=0, le=1)
    title: str
    explanation: str
    evidence: str
    file_path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    code_snippet: str = ""
    suggested_fix: str
    publish_recommendation: str = "inline"
    rule_identifier: str = "AI"


class AIReviewOutput(BaseModel):
    summary: str
    findings: list[StructuredFinding] = Field(default_factory=list)
    test_recommendations: list[dict] = Field(default_factory=list)
    documentation_recommendations: list[dict] = Field(default_factory=list)


def _default_file(context: dict) -> str:
    files = context.get("changed_files") or []
    return files[0].get("filename", "unknown") if files else "unknown"


def mock_review(context: dict) -> AIReviewOutput:
    diff = context.get("diff_text", "")
    file_path = _default_file(context)
    findings: list[StructuredFinding] = []
    lower = diff.lower()
    patterns = [
        (
            "authorization",
            [
                "@public",
                "skip_auth",
                "withoutmiddleware",
                "permitall",
                "is_admin = true",
            ],
            "security",
            "high",
            "Authorization control may be bypassed",
            "The change weakens or bypasses an authorization boundary. Verify the caller's permissions before accessing the resource.",
            "Restore policy/middleware enforcement and add an authorization regression test.",
        ),
        (
            "input",
            ["request.json", "req.body", "request->all", "getparameter"],
            "security",
            "medium",
            "New input path requires explicit validation",
            "The changed path consumes external input, but the diff does not show a complete validation contract.",
            "Add schema validation, length/range constraints, and negative tests before using the value.",
        ),
        (
            "transaction",
            ["commit()", "save()", "update("],
            "correctness",
            "medium",
            "State change needs failure-path handling",
            "The change updates persistent state. Partial failure or concurrent execution could leave inconsistent data.",
            "Use an explicit transaction and add rollback/idempotency behavior for failure paths.",
        ),
        (
            "async",
            ["await ", "promise", "future<"],
            "correctness",
            "low",
            "Asynchronous failure path should be reviewed",
            "The new asynchronous operation may reject or time out without a visible recovery path.",
            "Handle timeout/cancellation and surface a typed error to the caller.",
        ),
        (
            "query",
            [".all()", "select *", "findall", "get()"],
            "performance",
            "medium",
            "Potential unbounded data retrieval",
            "The changed query can retrieve an unbounded result set or create unnecessary memory pressure.",
            "Add filtering, pagination, selected columns, or an explicit limit.",
        ),
    ]
    for rule, needles, category, severity, title, explanation, fix in patterns:
        if any(n in lower for n in needles):
            line = max(
                1,
                next(
                    (
                        i
                        for i, line_text in enumerate(diff.splitlines(), 1)
                        if any(n in line_text.lower() for n in needles)
                    ),
                    1,
                ),
            )
            finding = StructuredFinding(
                category=category,
                severity=severity,
                confidence=0.82,
                title=title,
                explanation=explanation,
                evidence=f"Repository-aware review matched {rule} behavior in the supplied diff.",
                file_path=file_path,
                start_line=line,
                end_line=line,
                code_snippet=diff.splitlines()[line - 1][:400]
                if diff.splitlines() and line <= len(diff.splitlines())
                else "",
                suggested_fix=fix,
                rule_identifier=f"AI-{rule.upper()}",
            )
            findings.append(finding)
    if not findings:
        findings.append(
            StructuredFinding(
                category="maintainability",
                severity="low",
                confidence=0.72,
                title="Confirm repository convention and regression coverage",
                explanation="The change is not matched by a high-confidence deterministic pattern. A human reviewer should still verify behavior and repository conventions.",
                evidence="No critical deterministic or repository-aware signal was identified in the supplied context.",
                file_path=file_path,
                start_line=1,
                end_line=1,
                suggested_fix="Confirm the expected behavior in tests and document any public contract change.",
                publish_recommendation="internal_only",
                rule_identifier="AI-GENERAL",
            )
        )

    changed = [f.get("filename", "") for f in context.get("changed_files", [])]
    has_test_change = any("test" in f.lower() or "spec" in f.lower() for f in changed)
    tests = (
        []
        if has_test_change
        else [
            {
                "test_type": "integration",
                "target_module": file_path,
                "scenario": "Exercise the changed behavior with valid, invalid, and unauthorized inputs.",
                "expected_result": "The valid request succeeds and invalid/unauthorized requests are rejected without changing state.",
                "priority": "high"
                if any(f.severity in {"high", "critical"} for f in findings)
                else "medium",
            }
        ]
    )
    docs = []
    if any(
        name.lower().endswith(
            (
                ".env",
                "dockerfile",
                "docker-compose.yml",
                "requirements.txt",
                "package.json",
            )
        )
        for name in changed
    ):
        docs.append(
            {
                "document_type": "README/deployment documentation",
                "reason": "The pull request changes environment, dependency, or deployment configuration.",
                "suggested_update": "Document the new configuration, default value, migration step, and rollback procedure.",
                "priority": "medium",
            }
        )
    return AIReviewOutput(
        summary=f"Repository-aware review produced {len(findings)} structured finding(s) for PR #{context.get('github_number', '?')}.",
        findings=findings,
        test_recommendations=tests,
        documentation_recommendations=docs,
    )


def openai_compatible_review(context: dict) -> AIReviewOutput:
    settings = get_settings()
    if not settings.ai_base_url or not settings.ai_api_key or not settings.ai_model:
        raise RuntimeError(
            "AI_BASE_URL, AI_API_KEY, and AI_MODEL are required for openai_compatible mode"
        )
    prompt = {
        "task": "Review the pull request using only supplied context. Return JSON matching the requested schema.",
        "rules": [
            "reference files and lines",
            "separate evidence from hypotheses",
            "no generic style noise",
            "mark uncertainty",
        ],
        "context": context,
        "schema": AIReviewOutput.model_json_schema(),
    }
    response = httpx.post(
        settings.ai_base_url.rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {settings.ai_api_key}"},
        json={
            "model": settings.ai_model,
            "messages": [{"role": "user", "content": json.dumps(prompt)}],
            "response_format": {"type": "json_object"},
        },
        timeout=settings.ai_timeout_seconds,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    try:
        return AIReviewOutput.model_validate_json(content)
    except ValidationError as exc:
        raise RuntimeError("AI provider returned malformed structured output") from exc


def review_context(context: dict) -> AIReviewOutput:
    provider = get_settings().ai_provider.lower()
    output = (
        openai_compatible_review(context)
        if provider == "openai_compatible"
        else mock_review(context)
    )
    for item in output.findings:
        data = item.model_dump()
        data["fingerprint"] = fingerprint_finding(data)
    return output
