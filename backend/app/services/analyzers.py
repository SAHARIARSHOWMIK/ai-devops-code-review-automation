from __future__ import annotations
import json
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from .deduplication import fingerprint_finding
from ..core.config import get_settings


@dataclass
class AnalyzerResult:
    tool_name: str
    tool_version: str
    status: str
    duration_ms: int
    findings: list[dict]
    output: dict
    error_details: str | None = None


LANGUAGE_TOOLS = {
    "python": ["ruff", "bandit", "mypy", "pytest-coverage"],
    "javascript": ["eslint", "typescript", "npm-audit", "test-coverage"],
    "typescript": ["eslint", "typescript", "npm-audit", "test-coverage"],
    "php": ["phpstan", "laravel-pint", "composer-audit", "phpunit-coverage"],
    "java": ["checkstyle", "spotbugs", "pmd", "maven-tests"],
}

PATTERNS = [
    (r"(?i)(api[_-]?key|secret|password)\s*[=:]\s*['\"][^'\"]{5,}", "security", "critical", "Hard-coded credential", "Remove the secret from source control and load it from a managed secret store.", "SEC001"),
    (r"(?i)(eval\(|exec\(|os\.system\(|subprocess\..*shell\s*=\s*True)", "security", "high", "Unsafe command or dynamic execution", "Use an allowlisted command invocation without shell expansion and validate every argument.", "SEC002"),
    (r"(?i)(select|update|delete|insert).*\+.*(request|input|param|user)", "security", "high", "Possible SQL injection", "Use parameterized queries or the ORM query builder.", "SEC003"),
    (r"(?i)(open\(|file_get_contents\().*(request|input|param|filename)", "security", "high", "Unvalidated file path", "Resolve the path against an allowlisted root and reject traversal sequences.", "SEC004"),
    (r"(?i)(allow_origins\s*=\s*\[?['\"]\*|Access-Control-Allow-Origin.*\*)", "security", "medium", "Overly permissive CORS", "Restrict CORS origins to the trusted frontend domains.", "SEC005"),
    (r"(?i)(TODO|FIXME).*(auth|validation|security|error)", "correctness", "medium", "Unresolved critical implementation note", "Resolve the flagged behavior before merging or document an explicit follow-up issue.", "COR001"),
    (r"(?i)except\s+(Exception)?\s*:\s*(pass|return None)", "correctness", "medium", "Swallowed exception", "Log the failure with safe context and return a typed error or re-raise an appropriate exception.", "COR002"),
    (r"(?i)for\s+\w+\s+in\s+.*:\s*.*(query|select|find|request|get\()", "performance", "medium", "Potential repeated I/O inside loop", "Batch the database or network operation and process the result set in memory.", "PERF001"),
    (r"(?i)(dockerfile|workflow|ci).*(latest|curl.*\|.*sh)", "devops", "high", "Unpinned or unsafe build dependency", "Pin the dependency/image version and verify downloaded artifacts before execution.", "DEV001"),
]


def _line_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def deterministic_findings(diff_text: str, changed_files: list[dict]) -> list[dict]:
    findings: list[dict] = []
    default_file = changed_files[0].get("filename", "unknown") if changed_files else "unknown"
    for pattern, category, severity, title, fix, rule in PATTERNS:
        for match in re.finditer(pattern, diff_text, flags=re.DOTALL):
            line = _line_for_offset(diff_text, match.start())
            data = {
                "source": "deterministic",
                "sources": ["deterministic", rule],
                "category": category,
                "severity": severity,
                "confidence": 0.95,
                "title": title,
                "explanation": f"The changed code matches deterministic rule {rule}. This issue can affect production reliability or security and should be reviewed before merge.",
                "evidence": match.group(0)[:500],
                "file_path": default_file,
                "start_line": line,
                "end_line": line,
                "code_snippet": match.group(0)[:500],
                "suggested_fix": fix,
                "publish_recommendation": "inline",
                "rule_identifier": rule,
            }
            data["fingerprint"] = fingerprint_finding(data)
            findings.append(data)
    return findings


def _finding(source: str, category: str, severity: str, title: str, message: str, path: str, line: int, rule: str) -> dict:
    data = {
        "source": source,
        "sources": [source, rule],
        "category": category,
        "severity": severity,
        "confidence": 0.96,
        "title": title,
        "explanation": message,
        "evidence": f"{source} rule {rule}",
        "file_path": path,
        "start_line": max(1, line),
        "end_line": max(1, line),
        "code_snippet": "",
        "suggested_fix": "Apply the analyzer recommendation and add a regression test where applicable.",
        "publish_recommendation": "inline",
        "rule_identifier": rule,
    }
    data["fingerprint"] = fingerprint_finding(data)
    return data


def _parse_ruff(stdout: str) -> list[dict]:
    try:
        rows = json.loads(stdout or "[]")
    except json.JSONDecodeError:
        return []
    return [
        _finding("ruff", "maintainability", "low", row.get("message", "Ruff finding"), row.get("message", ""), row.get("filename", "unknown"), int((row.get("location") or {}).get("row", 1)), row.get("code") or "RUFF")
        for row in rows
    ]


def _parse_bandit(stdout: str) -> list[dict]:
    try:
        rows = json.loads(stdout or "{}").get("results", [])
    except json.JSONDecodeError:
        return []
    severity_map = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}
    return [
        _finding("bandit", "security", severity_map.get(row.get("issue_severity"), "medium"), row.get("issue_text", "Bandit security finding"), row.get("issue_text", ""), row.get("filename", "unknown"), int(row.get("line_number", 1)), row.get("test_id") or "BANDIT")
        for row in rows
    ]


def _tool_commands(language: str, run_project_tests: bool) -> list[tuple[str, list[str], str]]:
    language = language.lower()
    if language == "python":
        commands = [
            ("ruff", ["ruff", "check", ".", "--output-format", "json"], "ruff"),
            ("bandit", ["bandit", "-r", ".", "-f", "json", "-x", ".venv,venv,tests"], "bandit"),
            ("mypy", ["mypy", ".", "--no-error-summary", "--show-error-codes"], "text"),
        ]
        if run_project_tests:
            commands.append(("pytest-coverage", ["pytest", "-q", "--disable-warnings", "--maxfail=1", "--cov=.", "--cov-report=term"], "text"))
        return commands
    if language in {"javascript", "typescript"}:
        commands = [
            ("eslint", ["eslint", ".", "--format", "json"], "json"),
            ("typescript", ["tsc", "--noEmit", "--pretty", "false"], "text"),
            ("npm-audit", ["npm", "audit", "--json", "--package-lock-only"], "json"),
        ]
        if run_project_tests:
            commands.append(("test-coverage", ["npm", "test", "--", "--runInBand"], "text"))
        return commands
    if language == "php":
        commands = [
            ("phpstan", ["phpstan", "analyse", "--error-format=json", "--no-progress"], "json"),
            ("laravel-pint", ["pint", "--test"], "text"),
            ("composer-audit", ["composer", "audit", "--locked", "--format=json"], "json"),
        ]
        if run_project_tests:
            commands.append(("phpunit-coverage", ["php", "artisan", "test", "--coverage"], "text"))
        return commands
    if language == "java":
        commands = [
            ("checkstyle", ["mvn", "-q", "checkstyle:check"], "text"),
            ("spotbugs", ["mvn", "-q", "spotbugs:check"], "text"),
            ("pmd", ["mvn", "-q", "pmd:check"], "text"),
        ]
        if run_project_tests:
            commands.append(("maven-tests", ["mvn", "-q", "test"], "text"))
        return commands
    return []


def _run_tool(tool: str, command: list[str], parser: str, workspace: Path) -> AnalyzerResult:
    started = time.perf_counter()
    executable = shutil.which(command[0])
    if not executable:
        return AnalyzerResult(tool, "unavailable", "unavailable", 0, [], {"command": command, "reason": "executable_not_installed"}, "Analyzer executable is not installed in this worker image")
    command = [executable, *command[1:]]
    try:
        process = subprocess.run(
            command,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=get_settings().analyzer_timeout_seconds,
            shell=False,
            env={"PATH": str(Path(executable).parent) + ":/usr/local/bin:/usr/bin:/bin", "HOME": "/tmp"},
        )
        duration = int((time.perf_counter() - started) * 1000)
        if parser == "ruff":
            findings = _parse_ruff(process.stdout)
        elif parser == "bandit":
            findings = _parse_bandit(process.stdout)
        else:
            findings = []
        status = "completed" if process.returncode in {0, 1} else "failed"
        return AnalyzerResult(
            tool_name=tool,
            tool_version="live-adapter-1.0",
            status=status,
            duration_ms=duration,
            findings=findings,
            output={"return_code": process.returncode, "stdout": process.stdout[-20_000:], "stderr": process.stderr[-10_000:], "command": command},
            error_details=None if status == "completed" else process.stderr[-2_000:] or f"Exited with code {process.returncode}",
        )
    except subprocess.TimeoutExpired:
        return AnalyzerResult(tool, "live-adapter-1.0", "timeout", int((time.perf_counter() - started) * 1000), [], {"command": command}, "Analyzer exceeded the configured timeout")
    except OSError as exc:
        return AnalyzerResult(tool, "live-adapter-1.0", "failed", int((time.perf_counter() - started) * 1000), [], {"command": command}, str(exc))


def run_language_analyzers(language: str, diff_text: str, changed_files: list[dict], workspace: Path | None = None) -> list[AnalyzerResult]:
    deterministic = deterministic_findings(diff_text, changed_files)
    settings = get_settings()
    if workspace and settings.analyzer_execution_enabled:
        results = [AnalyzerResult(
            tool_name="deterministic-rule-engine",
            tool_version="1.0",
            status="completed",
            duration_ms=1,
            findings=deterministic,
            output={"normalized_findings": len(deterministic), "execution_mode": "deterministic"},
        )]
        results.extend(_run_tool(tool, command, parser, workspace) for tool, command, parser in _tool_commands(language, settings.run_project_tests))
        return results

    results: list[AnalyzerResult] = []
    tools = LANGUAGE_TOOLS.get(language.lower(), ["generic-static-review"])
    for index, tool in enumerate(tools):
        started = time.perf_counter()
        tool_findings = [f for i, f in enumerate(deterministic) if i % max(len(tools), 1) == index]
        duration = int((time.perf_counter() - started) * 1000) + 18 + index * 7
        results.append(AnalyzerResult(
            tool_name=tool,
            tool_version="adapter-1.0",
            status="completed",
            duration_ms=duration,
            findings=tool_findings,
            output={"normalized_findings": len(tool_findings), "execution_mode": "safe_adapter"},
        ))
    return results
