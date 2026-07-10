from dataclasses import dataclass
from typing import Iterable

SEVERITY_POINTS = {"critical": 22, "high": 14, "medium": 7, "low": 2, "info": 0}


@dataclass
class RiskResult:
    score: int
    level: str
    factors: list[dict]
    recommendation: str


def calculate_risk(pr, findings: Iterable, test_recommendations: Iterable | None = None) -> RiskResult:
    score = 8
    factors: list[dict] = [{"factor": "Base pull-request review risk", "points": 8}]
    total_changes = int(pr.additions or 0) + int(pr.deletions or 0)
    if total_changes > 1000:
        score += 20; factors.append({"factor": "Very large code change", "points": 20})
    elif total_changes > 400:
        score += 12; factors.append({"factor": "Large code change", "points": 12})
    elif total_changes < 50:
        score -= 3; factors.append({"factor": "Small isolated change", "points": -3})

    diff = (pr.diff_text or "").lower()
    sensitive_terms = {
        "authentication/authorization changes": ["auth", "permission", "authorize", "role", "jwt"],
        "database migration changes": ["migration", "alter table", "schema"],
        "payment/security module changes": ["payment", "secret", "crypto", "password"],
        "critical dependency changes": ["requirements.txt", "package.json", "composer.json", "pom.xml"],
    }
    for label, terms in sensitive_terms.items():
        if any(term in diff for term in terms):
            points = 10 if label != "critical dependency changes" else 7
            score += points; factors.append({"factor": label.capitalize(), "points": points})

    finding_list = list(findings)
    severity_counts: dict[str, int] = {}
    for finding in finding_list:
        severity = finding.severity if hasattr(finding, "severity") else finding.get("severity", "low")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    for severity, count in severity_counts.items():
        points = min(SEVERITY_POINTS.get(severity, 0) * count, 35)
        if points:
            score += points
            factors.append({"factor": f"{count} {severity} finding(s)", "points": points})

    recommendations = list(test_recommendations or [])
    if recommendations:
        high = sum(1 for item in recommendations if (item.priority if hasattr(item, "priority") else item.get("priority")) == "high")
        points = min(5 + high * 3, 14)
        score += points; factors.append({"factor": "Missing or recommended tests", "points": points})

    if pr.changed_files and all(str(f.get("filename", "")).lower().endswith((".md", ".txt")) for f in pr.changed_files):
        score -= 10; factors.append({"factor": "Documentation-only change", "points": -10})

    score = max(0, min(100, score))
    level = "low" if score < 25 else "moderate" if score < 50 else "high" if score < 75 else "critical"
    unresolved_high = any((f.severity if hasattr(f, "severity") else f.get("severity")) in {"critical", "high"} for f in finding_list)
    if score >= 75 or any((f.severity if hasattr(f, "severity") else f.get("severity")) == "critical" for f in finding_list):
        recommendation = "high_risk_security_review_required"
    elif unresolved_high:
        recommendation = "changes_required"
    elif score >= 40:
        recommendation = "changes_recommended"
    else:
        recommendation = "ready_for_human_review"
    return RiskResult(score=score, level=level, factors=factors, recommendation=recommendation)
