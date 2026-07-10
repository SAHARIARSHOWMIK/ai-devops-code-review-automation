from __future__ import annotations
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from ..core.security import hash_password
from ..models import (
    AuditLog,
    DocumentationRecommendation,
    Finding,
    Notification,
    Organization,
    PullRequest,
    Repository,
    RepositoryPolicy,
    ReviewRun,
    TestRecommendation,
    User,
    WebhookEvent,
)
from .review_pipeline import execute_review

# Documented credential used only when DEMO_MODE is enabled.
DEMO_PASSWORD = "demo1234"


def seed_demo(db: Session, reset: bool = False) -> dict:
    if reset:
        for model in [
            WebhookEvent,
            AuditLog,
            Notification,
            Finding,
            TestRecommendation,
            DocumentationRecommendation,
            ReviewRun,
            PullRequest,
            RepositoryPolicy,
            Repository,
            User,
            Organization,
        ]:
            db.query(model).delete()
        db.commit()
    existing = (
        db.query(Organization).filter(Organization.name == "Acme Engineering").first()
    )
    if existing:
        return {
            "seeded": False,
            "organization_id": existing.id,
            "message": "Demo data already exists",
        }

    org = Organization(
        name="Acme Engineering",
        status="active",
        github_installation_id="demo-installation-1042",
    )
    db.add(org)
    db.flush()
    users = [
        User(
            organization_id=org.id,
            name="Amina Rahman",
            email="admin@demo.com",
            password_hash=hash_password(DEMO_PASSWORD),
            role="platform_admin",
        ),
        User(
            organization_id=org.id,
            name="Daniel Lee",
            email="manager@demo.com",
            password_hash=hash_password(DEMO_PASSWORD),
            role="engineering_manager",
        ),
        User(
            organization_id=org.id,
            name="Priya Nair",
            email="maintainer@demo.com",
            password_hash=hash_password(DEMO_PASSWORD),
            role="repository_maintainer",
        ),
        User(
            organization_id=org.id,
            name="Omar Hasan",
            email="developer@demo.com",
            password_hash=hash_password(DEMO_PASSWORD),
            role="developer",
        ),
        User(
            organization_id=org.id,
            name="Maya Chen",
            email="auditor@demo.com",
            password_hash=hash_password(DEMO_PASSWORD),
            role="auditor",
        ),
    ]
    db.add_all(users)
    db.flush()
    repo_specs = [
        ("acme", "payments-api", "Python", "security_sensitive_application"),
        ("acme", "vendor-portal", "PHP", "laravel_application"),
        ("acme", "customer-console", "TypeScript", "standard_application"),
        ("acme", "ledger-service", "Java", "api_service"),
    ]
    repos = []
    for idx, (owner, name, language, profile) in enumerate(repo_specs, 1):
        repo = Repository(
            organization_id=org.id,
            github_repository_id=str(9000 + idx),
            owner=owner,
            name=name,
            primary_language=language,
            visibility="private",
            connection_status="active",
            webhook_status="active",
            active_review_profile=profile,
            last_synchronized_at=datetime.now(timezone.utc)
            - timedelta(minutes=idx * 7),
        )
        db.add(repo)
        db.flush()
        db.add(
            RepositoryPolicy(
                repository_id=repo.id,
                review_profile=profile,
                monitored_branches=["main", "develop", "release/*"],
                ignored_paths=[
                    "vendor/**",
                    "node_modules/**",
                    "dist/**",
                    "generated/**",
                ],
                analyzer_settings={"enabled": True, "tools": "language_default"},
                minimum_severity="medium",
            )
        )
        repos.append(repo)
    db.commit()

    prs = [
        PullRequest(
            repository_id=repos[0].id,
            github_number=184,
            title="Add idempotent payment retry endpoint",
            description="Adds retry support for failed card authorizations.",
            author="nora-dev",
            base_branch="main",
            head_branch="feature/payment-retry",
            current_commit_sha="a8f2c1d9b410",
            changed_files_count=4,
            additions=286,
            deletions=61,
            assigned_reviewer="Priya Nair",
            changed_files=[
                {"filename": "app/api/payments.py", "additions": 88, "deletions": 12},
                {
                    "filename": "app/services/payment_service.py",
                    "additions": 142,
                    "deletions": 31,
                },
                {"filename": "requirements.txt", "additions": 2, "deletions": 1},
                {
                    "filename": "tests/test_payments.py",
                    "additions": 54,
                    "deletions": 17,
                },
            ],
            commits=[{"sha": "a8f2c1d", "message": "add retry endpoint"}],
            diff_text="""diff --git a/app/api/payments.py b/app/api/payments.py
+API_KEY = \"demo-hardcoded-token-not-real\"
+@router.post(\"/payments/{payment_id}/retry\")
+async def retry_payment(payment_id: str, request: Request):
+    payload = await request.json()
+    payment = db.query(Payment).get(payment_id)
+    payment.status = \"retrying\"
+    db.commit()
+    return payment
""",
        ),
        PullRequest(
            repository_id=repos[1].id,
            github_number=72,
            title="Allow vendor admins to replace compliance files",
            description="Updates file replacement workflow.",
            author="leo-php",
            base_branch="develop",
            head_branch="feature/vendor-file-replace",
            current_commit_sha="b762ed01fa12",
            changed_files_count=3,
            additions=174,
            deletions=42,
            assigned_reviewer="Priya Nair",
            changed_files=[
                {
                    "filename": "app/Http/Controllers/VendorDocumentController.php",
                    "additions": 91,
                    "deletions": 22,
                },
                {
                    "filename": "app/Models/VendorDocument.php",
                    "additions": 29,
                    "deletions": 9,
                },
                {"filename": "routes/web.php", "additions": 54, "deletions": 11},
            ],
            commits=[{"sha": "b762ed0", "message": "replace vendor files"}],
            diff_text="""diff --git a/app/Http/Controllers/VendorDocumentController.php
+public function replace(Request $request, VendorDocument $document) {
+    // TODO auth validation before release
+    $data = $request->all();
+    $path = file_get_contents($request->input('filename'));
+    $document->update($data);
+    return response()->json($document);
+}
""",
        ),
        PullRequest(
            repository_id=repos[2].id,
            github_number=311,
            title="Refactor account settings state",
            description="Moves settings to a shared hook.",
            author="sara-ui",
            base_branch="main",
            head_branch="refactor/settings-hook",
            current_commit_sha="c45a998eff33",
            changed_files_count=2,
            additions=98,
            deletions=76,
            assigned_reviewer="Daniel Lee",
            changed_files=[
                {
                    "filename": "src/hooks/useAccountSettings.ts",
                    "additions": 71,
                    "deletions": 20,
                },
                {
                    "filename": "src/pages/Settings.tsx",
                    "additions": 27,
                    "deletions": 56,
                },
            ],
            commits=[{"sha": "c45a998", "message": "shared settings hook"}],
            diff_text="""diff --git a/src/hooks/useAccountSettings.ts
+export async function saveSettings(input: any) {
+  const response = await fetch('/api/settings', { method: 'POST', body: JSON.stringify(input) })
+  return response.json()
+}
""",
        ),
        PullRequest(
            repository_id=repos[3].id,
            github_number=58,
            title="Stream ledger reconciliation report",
            description="Avoids loading the entire report in memory.",
            author="ivan-java",
            base_branch="main",
            head_branch="perf/ledger-stream",
            current_commit_sha="d91fe33ac981",
            changed_files_count=2,
            additions=122,
            deletions=89,
            assigned_reviewer="Daniel Lee",
            changed_files=[
                {
                    "filename": "src/main/java/com/acme/LedgerReportService.java",
                    "additions": 85,
                    "deletions": 70,
                },
                {
                    "filename": "src/test/java/com/acme/LedgerReportServiceTest.java",
                    "additions": 37,
                    "deletions": 19,
                },
            ],
            commits=[{"sha": "d91fe33", "message": "stream reconciliation report"}],
            diff_text="""diff --git a/src/main/java/com/acme/LedgerReportService.java
+public Report getReport(String accountId) {
+    try {
+        return repository.findAll(accountId);
+    } catch (Exception e) {
+        return null;
+    }
+}
""",
        ),
        PullRequest(
            repository_id=repos[0].id,
            github_number=181,
            title="Update health-check response metadata",
            description="Documentation and response metadata only.",
            author="nora-dev",
            base_branch="main",
            head_branch="docs/health-metadata",
            current_commit_sha="e77bcaa19200",
            changed_files_count=2,
            additions=24,
            deletions=8,
            assigned_reviewer="Priya Nair",
            changed_files=[
                {"filename": "README.md", "additions": 19, "deletions": 4},
                {"filename": "docs/api.md", "additions": 5, "deletions": 4},
            ],
            commits=[{"sha": "e77bcaa", "message": "document health metadata"}],
            diff_text="""diff --git a/README.md
+The health endpoint includes build version and deployment region metadata.
""",
        ),
    ]
    db.add_all(prs)
    db.commit()
    for index, pr in enumerate(prs):
        run = execute_review(db, pr.id, "pull_request.opened")
        if index == 2:
            for finding in run.findings[:1]:
                finding.status = "false_positive"
            run.status = "partially_approved"
            pr.review_status = "partially_approved"
        elif index == 3:
            for finding in run.findings:
                finding.status = "approved"
            run.status = "approved_for_publication"
            pr.review_status = "approved_for_publication"
        elif index == 4:
            for finding in run.findings:
                finding.status = "published"
                finding.published_comment_id = "demo-991"
            run.status = "published"
            pr.review_status = "published"
        db.commit()
    db.add_all(
        [
            WebhookEvent(
                delivery_id="demo-delivery-001",
                event_name="pull_request",
                action="opened",
                repository_full_name="acme/payments-api",
                payload={"demo": True},
                status="processed",
            ),
            WebhookEvent(
                delivery_id="demo-delivery-002",
                event_name="pull_request",
                action="synchronize",
                repository_full_name="acme/vendor-portal",
                payload={"demo": True},
                status="processed",
            ),
            AuditLog(
                actor_id=users[2].id,
                organization_id=org.id,
                repository_id=repos[0].id,
                pull_request_id=prs[0].id,
                event_type="review.analysis_completed",
                new_value={"risk": prs[0].risk_score},
                result="success",
            ),
            AuditLog(
                actor_id=users[1].id,
                organization_id=org.id,
                repository_id=repos[2].id,
                pull_request_id=prs[2].id,
                event_type="finding.false_positive",
                new_value={"reason": "Expected shared validation layer"},
                result="success",
            ),
            AuditLog(
                actor_id=users[2].id,
                organization_id=org.id,
                repository_id=repos[3].id,
                pull_request_id=prs[3].id,
                event_type="review.approved",
                new_value={"decision": "request_changes"},
                result="success",
            ),
        ]
    )
    db.commit()
    return {
        "seeded": True,
        "organization_id": org.id,
        "repositories": len(repos),
        "pull_requests": len(prs),
        "users": len(users),
        "demo_login": {"email": "admin@demo.com", "password": DEMO_PASSWORD},
    }
