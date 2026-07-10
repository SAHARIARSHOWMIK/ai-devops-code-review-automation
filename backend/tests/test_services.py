from types import SimpleNamespace
from app.core.security import hash_password, verify_password
from app.services.deduplication import deduplicate, fingerprint_finding
from app.services.risk_engine import calculate_risk
from app.services.analyzers import deterministic_findings, run_language_analyzers
from app.services.ai_review import mock_review


def test_password_hash_round_trip():
    encoded = hash_password("strong-password")
    assert verify_password("strong-password", encoded)
    assert not verify_password("wrong", encoded)


def test_fingerprint_is_stable():
    data = {"file_path": "app/main.py", "start_line": 10, "category": "security", "rule_identifier": "SEC001"}
    assert fingerprint_finding(data) == fingerprint_finding(dict(data))


def test_deduplication_merges_sources():
    base = {"file_path": "app/main.py", "start_line": 10, "category": "security", "severity": "high", "title": "Unsafe command", "confidence": 0.8, "source": "bandit", "rule_identifier": "SEC002"}
    second = dict(base, source="ai", confidence=0.85)
    result = deduplicate([base, second])
    assert len(result) == 1
    assert set(result[0]["sources"]) == {"bandit", "ai"}


def test_risk_score_bounded():
    pr = SimpleNamespace(additions=5000, deletions=5000, diff_text="auth migration payment package.json", changed_files=[{"filename": "app.py"}])
    findings = [SimpleNamespace(severity="critical") for _ in range(20)]
    result = calculate_risk(pr, findings, [SimpleNamespace(priority="high")])
    assert result.score == 100
    assert result.level == "critical"


def test_documentation_only_reduces_risk():
    pr = SimpleNamespace(additions=10, deletions=2, diff_text="docs", changed_files=[{"filename": "README.md"}])
    result = calculate_risk(pr, [], [])
    assert result.score < 25
    assert result.level == "low"


def test_deterministic_secret_detection():
    findings = deterministic_findings('+API_KEY = "secret-value-123"', [{"filename": "settings.py"}])
    assert findings
    assert findings[0]["severity"] == "critical"


def test_analyzer_adapter_returns_language_tools():
    results = run_language_analyzers("Python", '+eval(user_input)', [{"filename": "app.py"}])
    assert len(results) == 4
    assert all(item.status == "completed" for item in results)


def test_mock_ai_returns_structured_finding():
    output = mock_review({"github_number": 1, "changed_files": [{"filename": "api.py"}], "diff_text": "+payload = await request.json()"})
    assert output.findings
    assert output.findings[0].file_path == "api.py"


def test_mock_ai_recommends_tests_when_missing():
    output = mock_review({"github_number": 1, "changed_files": [{"filename": "service.py"}], "diff_text": "+db.commit()"})
    assert output.test_recommendations


def test_mock_ai_skips_test_recommendation_when_test_changed():
    output = mock_review({"github_number": 1, "changed_files": [{"filename": "tests/test_service.py"}], "diff_text": "+assert response.status_code == 200"})
    assert output.test_recommendations == []
