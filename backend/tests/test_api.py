import hashlib
import hmac
import json


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["docs"] == "/docs"


def test_login_success(client):
    response = client.post(
        "/api/auth/login", json={"email": "admin@demo.com", "password": "demo1234"}
    )
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_login_failure(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@demo.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_auth_required(client):
    assert client.get("/api/repositories").status_code == 401


def test_me(client, admin_headers):
    response = client.get("/api/auth/me", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["role"] == "platform_admin"


def test_demo_seed_is_idempotent(client):
    response = client.post("/api/demo/seed")
    assert response.status_code == 200
    assert response.json()["seeded"] is False


def test_list_users(client, admin_headers):
    rows = client.get("/api/users", headers=admin_headers).json()
    assert len(rows) == 5
    assert {x["role"] for x in rows} >= {"platform_admin", "auditor"}


def test_list_repositories(client, admin_headers):
    response = client.get("/api/repositories", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) == 4
    assert all("average_risk" in row for row in response.json())


def test_repository_language_filter(client, admin_headers):
    rows = client.get("/api/repositories?language=Python", headers=admin_headers).json()
    assert len(rows) == 1
    assert rows[0]["primary_language"] == "Python"


def test_repository_detail(client, admin_headers):
    repo_id = client.get("/api/repositories", headers=admin_headers).json()[0]["id"]
    response = client.get(f"/api/repositories/{repo_id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["policy"]


def test_policy_update(client, admin_headers):
    repo_id = client.get("/api/repositories", headers=admin_headers).json()[0]["id"]
    current = client.get(
        f"/api/repositories/{repo_id}/policy", headers=admin_headers
    ).json()
    current["minimum_severity"] = "high"
    current.pop("id")
    current.pop("repository_id")
    response = client.put(
        f"/api/repositories/{repo_id}/policy", headers=admin_headers, json=current
    )
    assert response.status_code == 200
    assert response.json()["minimum_severity"] == "high"


def test_auditor_cannot_update_policy(client, auditor_headers, admin_headers):
    repo_id = client.get("/api/repositories", headers=admin_headers).json()[0]["id"]
    payload = {
        "review_enabled": True,
        "review_profile": "standard_application",
        "monitored_branches": ["main"],
        "ignored_paths": [],
        "analyzer_settings": {},
        "maximum_diff_size": 5000,
        "minimum_severity": "medium",
        "security_checks": True,
        "test_review": True,
        "documentation_review": True,
        "approval_required": True,
        "auto_post_summary": False,
        "re_review_on_push": True,
    }
    assert (
        client.put(
            f"/api/repositories/{repo_id}/policy", headers=auditor_headers, json=payload
        ).status_code
        == 403
    )


def test_create_repository(client, admin_headers):
    response = client.post(
        "/api/repositories",
        headers=admin_headers,
        json={
            "owner": "acme",
            "name": "ml-risk-service",
            "primary_language": "Python",
            "active_review_profile": "data_ml_project",
        },
    )
    assert response.status_code == 201
    assert response.json()["name"] == "ml-risk-service"


def test_duplicate_repository_rejected(client, admin_headers):
    payload = {
        "owner": "acme",
        "name": "duplicate-service",
        "primary_language": "Python",
    }
    assert (
        client.post(
            "/api/repositories", headers=admin_headers, json=payload
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/repositories", headers=admin_headers, json=payload
        ).status_code
        == 409
    )


def test_list_pull_requests(client, admin_headers):
    rows = client.get("/api/pull-requests", headers=admin_headers).json()
    assert len(rows) >= 5
    assert all("repository" in row for row in rows)


def test_pull_request_detail_has_review(client, admin_headers):
    pr_id = client.get("/api/pull-requests", headers=admin_headers).json()[0]["id"]
    response = client.get(f"/api/pull-requests/{pr_id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["latest_review"]["findings"]


def test_risk_filter(client, admin_headers):
    response = client.get(
        "/api/pull-requests?risk_level=critical", headers=admin_headers
    )
    assert response.status_code == 200
    assert all(x["risk_level"] == "critical" for x in response.json())


def test_manual_reanalysis(client, admin_headers):
    pr_id = client.get("/api/pull-requests", headers=admin_headers).json()[0]["id"]
    response = client.post(
        f"/api/pull-requests/{pr_id}/analyze",
        headers=admin_headers,
        json={"trigger_event": "manual.test", "force": True},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "awaiting_human_review"


def test_review_history(client, admin_headers):
    pr_id = client.get("/api/pull-requests", headers=admin_headers).json()[0]["id"]
    rows = client.get(
        f"/api/pull-requests/{pr_id}/review-history", headers=admin_headers
    ).json()
    assert len(rows) >= 1
    assert "findings_count" in rows[0]


def test_finding_approve(client, admin_headers):
    pr = client.get("/api/pull-requests", headers=admin_headers).json()[0]
    detail = client.get(f"/api/pull-requests/{pr['id']}", headers=admin_headers).json()
    finding = detail["latest_review"]["findings"][0]
    response = client.post(
        f"/api/findings/{finding['id']}/decision",
        headers=admin_headers,
        json={"decision": "approve", "comment": "Valid finding"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_finding_edit(client, admin_headers):
    pr = client.get("/api/pull-requests", headers=admin_headers).json()[1]
    finding = client.get(
        f"/api/pull-requests/{pr['id']}", headers=admin_headers
    ).json()["latest_review"]["findings"][0]
    response = client.post(
        f"/api/findings/{finding['id']}/decision",
        headers=admin_headers,
        json={
            "decision": "edit",
            "edited_content": "Validate and authorize the vendor document replacement.",
            "comment": "Clarified wording",
        },
    )
    assert response.status_code == 200
    assert response.json()["edited_content"].startswith("Validate")


def test_false_positive_decision(client, admin_headers):
    pr = client.get("/api/pull-requests", headers=admin_headers).json()[2]
    finding = client.get(
        f"/api/pull-requests/{pr['id']}", headers=admin_headers
    ).json()["latest_review"]["findings"][0]
    response = client.post(
        f"/api/findings/{finding['id']}/decision",
        headers=admin_headers,
        json={
            "decision": "false_positive",
            "comment": "Validated by shared middleware",
        },
    )
    assert response.json()["status"] == "false_positive"


def test_suppression_creation_from_finding(client, admin_headers):
    pr = client.get("/api/pull-requests", headers=admin_headers).json()[0]
    detail = client.get(f"/api/pull-requests/{pr['id']}", headers=admin_headers).json()
    finding = detail["latest_review"]["findings"][-1]
    response = client.post(
        f"/api/findings/{finding['id']}/decision",
        headers=admin_headers,
        json={
            "decision": "suppress",
            "comment": "Accepted generated-code exception",
            "create_suppression": True,
        },
    )
    assert response.status_code == 200
    repo_id = detail["repository"]["id"]
    assert client.get(
        f"/api/repositories/{repo_id}/suppressions", headers=admin_headers
    ).json()


def test_approve_all_and_publish_dry_run(client, admin_headers):
    pr = client.get("/api/pull-requests", headers=admin_headers).json()[0]
    detail = client.get(f"/api/pull-requests/{pr['id']}", headers=admin_headers).json()
    run_id = detail["latest_review"]["id"]
    response = client.post(
        f"/api/review-runs/{run_id}/approve-all", headers=admin_headers
    )
    assert response.status_code == 200
    publish = client.post(
        f"/api/review-runs/{run_id}/publish",
        headers=admin_headers,
        json={
            "review_decision": "request_changes",
            "include_summary": True,
            "dry_run": True,
        },
    )
    assert publish.status_code == 200
    assert publish.json()["items"][0]["status"] == "simulated"


def test_auditor_cannot_publish(client, auditor_headers, admin_headers):
    pr = client.get("/api/pull-requests", headers=admin_headers).json()[0]
    run_id = client.get(f"/api/pull-requests/{pr['id']}", headers=admin_headers).json()[
        "latest_review"
    ]["id"]
    response = client.post(
        f"/api/review-runs/{run_id}/publish",
        headers=auditor_headers,
        json={"dry_run": True},
    )
    assert response.status_code == 403


def test_approvals(client, admin_headers):
    response = client.get("/api/approvals", headers=admin_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_analytics_overview(client, admin_headers):
    data = client.get("/api/analytics/overview", headers=admin_headers).json()
    assert data["connected_repositories"] >= 4
    assert "risk_distribution" in data


def test_security_analytics(client, admin_headers):
    data = client.get("/api/analytics/security", headers=admin_headers).json()
    assert data["total"] >= 1
    assert "by_severity" in data


def test_quality_analytics(client, admin_headers):
    data = client.get("/api/analytics/quality", headers=admin_headers).json()
    assert data["findings"] >= 1
    assert 0 <= data["accepted_rate"] <= 100


def test_audit_logs(client, admin_headers):
    rows = client.get("/api/audit-logs", headers=admin_headers).json()
    assert rows
    assert "actor_name" in rows[0]


def test_notifications(client, admin_headers):
    rows = client.get("/api/notifications", headers=admin_headers).json()
    assert isinstance(rows, list)
    if rows:
        response = client.post(
            f"/api/notifications/{rows[0]['id']}/read", headers=admin_headers
        )
        assert response.json()["is_read"] is True


def test_github_status(client, admin_headers):
    data = client.get("/api/integrations/github/status", headers=admin_headers).json()
    assert data["demo_mode"] is True
    assert "pull_requests:write" in data["permissions"]


def webhook_headers(body: bytes, delivery: str):
    signature = hmac.new(b"test-webhook-secret", body, hashlib.sha256).hexdigest()
    return {
        "X-Hub-Signature-256": f"sha256={signature}",
        "X-GitHub-Delivery": delivery,
        "X-GitHub-Event": "ping",
        "Content-Type": "application/json",
    }


def test_valid_webhook(client):
    body = json.dumps({"zen": "Keep it logically awesome"}).encode()
    response = client.post(
        "/api/webhooks/github",
        content=body,
        headers=webhook_headers(body, "test-delivery-valid"),
    )
    assert response.status_code == 200
    assert response.json()["accepted"] is True


def test_invalid_webhook_rejected(client):
    response = client.post(
        "/api/webhooks/github",
        content=b"{}",
        headers={
            "X-Hub-Signature-256": "sha256=invalid",
            "X-GitHub-Delivery": "invalid-delivery",
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 401


def test_duplicate_webhook(client):
    body = b'{"demo": true}'
    headers = webhook_headers(body, "test-delivery-duplicate")
    assert (
        client.post("/api/webhooks/github", content=body, headers=headers).status_code
        == 200
    )
    response = client.post("/api/webhooks/github", content=body, headers=headers)
    assert response.json()["status"] == "duplicate"


def test_failed_jobs_endpoint(client, admin_headers):
    response = client.get("/api/failed-jobs", headers=admin_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
