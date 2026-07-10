from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..core.config import get_settings
from ..core.database import get_db
from ..core.security import create_access_token, verify_password
from ..models import (
    AnalyzerRun,
    AuditLog,
    DocumentationRecommendation,
    Finding,
    FindingDecision,
    GitHubPublication,
    Notification,
    Organization,
    PullRequest,
    Repository,
    RepositoryPolicy,
    ReviewRun,
    SuppressionRule,
    TestRecommendation,
    User,
    UserRole,
    WebhookEvent,
)
from ..schemas import (
    AnalyzeRequest,
    FindingDecisionRequest,
    LoginRequest,
    PolicyUpdate,
    PublishRequest,
    PullRequestCreate,
    RepositoryCreate,
    SuppressionCreate,
)
from ..services.audit import record_audit
from ..services.demo_seed import seed_demo
from ..services.context_collector import RepositoryContextCollector
from ..services.github import GitHubAppClient, verify_webhook_signature
from ..services.publisher import publish_review
from ..services.review_pipeline import execute_review
from ..services.job_queue import enqueue_review
from .deps import ensure_same_organization, get_current_user, require_roles

router = APIRouter()


def serialize(obj: Any) -> dict:
    result = {}
    for column in obj.__table__.columns:
        value = getattr(obj, column.name)
        if isinstance(value, datetime):
            value = value.isoformat()
        result[column.name] = value
    return result


def repository_or_404(db: Session, repository_id: int, user: User) -> Repository:
    repo = db.query(Repository).filter(Repository.id == repository_id).first()
    if not repo:
        raise HTTPException(404, "Repository not found")
    ensure_same_organization(repo.organization_id, user)
    return repo


def pr_or_404(db: Session, pr_id: int, user: User) -> PullRequest:
    pr = db.query(PullRequest).filter(PullRequest.id == pr_id).first()
    if not pr:
        raise HTTPException(404, "Pull request not found")
    ensure_same_organization(pr.repository.organization_id, user)
    return pr


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {"status": "healthy", "service": settings.app_name, "environment": settings.app_env, "demo_mode": settings.demo_mode, "version": "1.0.0"}


@router.post("/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    user = db.query(User).filter(User.email == payload.email, User.is_active.is_(True)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    user.last_login = datetime.now(timezone.utc)
    record_audit(db, "auth.login", actor=user, new_value={"email": user.email})
    db.commit()
    return {
        "access_token": create_access_token(user.email, user.role, user.organization_id),
        "token_type": "bearer",
        "user": serialize(user),
    }


@router.get("/auth/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return serialize(user)


@router.post("/demo/seed")
def create_demo(reset: bool = False, db: Session = Depends(get_db)) -> dict:
    if not get_settings().demo_mode:
        raise HTTPException(403, "Demo seed is disabled")
    return seed_demo(db, reset=reset)


@router.get("/organizations/current")
def current_organization(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return serialize(db.get(Organization, user.organization_id))


@router.get("/users")
def list_users(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(User).filter(User.organization_id == user.organization_id).order_by(User.name).all()
    return [serialize(row) for row in rows]


@router.get("/repositories")
def list_repositories(
    language: str | None = None,
    status_filter: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = db.query(Repository).filter(Repository.organization_id == user.organization_id)
    if language:
        query = query.filter(func.lower(Repository.primary_language) == language.lower())
    if status_filter:
        query = query.filter(Repository.connection_status == status_filter)
    rows = query.order_by(Repository.name).all()
    result = []
    for repo in rows:
        data = serialize(repo)
        open_prs = db.query(PullRequest).filter(PullRequest.repository_id == repo.id, PullRequest.state == "open").count()
        avg_risk = db.query(func.avg(PullRequest.risk_score)).filter(PullRequest.repository_id == repo.id).scalar() or 0
        data.update({"full_name": f"{repo.owner}/{repo.name}", "open_pull_requests": open_prs, "average_risk": round(avg_risk, 1)})
        result.append(data)
    return result


@router.post("/repositories", status_code=201)
def create_repository(
    payload: RepositoryCreate,
    user: User = Depends(require_roles(UserRole.PLATFORM_ADMIN.value, UserRole.ENGINEERING_MANAGER.value, UserRole.REPOSITORY_MAINTAINER.value)),
    db: Session = Depends(get_db),
) -> dict:
    exists = db.query(Repository).filter(Repository.organization_id == user.organization_id, Repository.owner == payload.owner, Repository.name == payload.name).first()
    if exists:
        raise HTTPException(409, "Repository already exists")
    repo = Repository(organization_id=user.organization_id, **payload.model_dump(), connection_status="connected", webhook_status="pending")
    db.add(repo); db.flush()
    db.add(RepositoryPolicy(repository_id=repo.id, review_profile=payload.active_review_profile))
    record_audit(db, "repository.created", actor=user, repository_id=repo.id, new_value=payload.model_dump())
    db.commit(); db.refresh(repo)
    return serialize(repo)


@router.get("/repositories/{repository_id}")
def repository_detail(repository_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    repo = repository_or_404(db, repository_id, user)
    data = serialize(repo)
    data["policy"] = serialize(repo.policy) if repo.policy else None
    data["pull_requests"] = [serialize(pr) for pr in db.query(PullRequest).filter(PullRequest.repository_id == repo.id).order_by(PullRequest.updated_at.desc()).limit(20)]
    category_counts = Counter(f.category for pr in repo.pull_requests for run in pr.review_runs for f in run.findings)
    data["recurring_categories"] = [{"category": key, "count": value} for key, value in category_counts.most_common()]
    return data


@router.get("/repositories/{repository_id}/policy")
def get_policy(repository_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    repo = repository_or_404(db, repository_id, user)
    if not repo.policy:
        raise HTTPException(404, "Repository policy not found")
    return serialize(repo.policy)


@router.put("/repositories/{repository_id}/policy")
def update_policy(
    repository_id: int,
    payload: PolicyUpdate,
    user: User = Depends(require_roles(UserRole.PLATFORM_ADMIN.value, UserRole.ENGINEERING_MANAGER.value, UserRole.REPOSITORY_MAINTAINER.value)),
    db: Session = Depends(get_db),
) -> dict:
    repo = repository_or_404(db, repository_id, user)
    policy = repo.policy or RepositoryPolicy(repository_id=repo.id)
    old = serialize(policy) if policy.id else None
    for key, value in payload.model_dump().items():
        setattr(policy, key, value)
    repo.active_review_profile = payload.review_profile
    db.add(policy)
    record_audit(db, "repository.policy_updated", actor=user, repository_id=repo.id, old_value=old, new_value=payload.model_dump())
    db.commit(); db.refresh(policy)
    return serialize(policy)


@router.get("/repositories/{repository_id}/suppressions")
def list_suppressions(repository_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    repo = repository_or_404(db, repository_id, user)
    return [serialize(x) for x in db.query(SuppressionRule).filter(SuppressionRule.repository_id == repo.id).all()]


@router.post("/repositories/{repository_id}/suppressions", status_code=201)
def create_suppression(
    repository_id: int,
    payload: SuppressionCreate,
    user: User = Depends(require_roles(UserRole.PLATFORM_ADMIN.value, UserRole.ENGINEERING_MANAGER.value, UserRole.REPOSITORY_MAINTAINER.value)),
    db: Session = Depends(get_db),
) -> dict:
    repo = repository_or_404(db, repository_id, user)
    row = SuppressionRule(repository_id=repo.id, created_by=user.id, **payload.model_dump())
    db.add(row)
    record_audit(db, "suppression.created", actor=user, repository_id=repo.id, new_value=payload.model_dump(mode="json"))
    db.commit(); db.refresh(row)
    return serialize(row)


@router.get("/pull-requests")
def list_pull_requests(
    risk_level: str | None = None,
    review_status: str | None = None,
    repository_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = db.query(PullRequest).join(Repository).filter(Repository.organization_id == user.organization_id)
    if risk_level:
        query = query.filter(PullRequest.risk_level == risk_level)
    if review_status:
        query = query.filter(PullRequest.review_status == review_status)
    if repository_id:
        query = query.filter(PullRequest.repository_id == repository_id)
    result=[]
    for pr in query.order_by(PullRequest.updated_at.desc()).all():
        data=serialize(pr)
        data.update({"repository": f"{pr.repository.owner}/{pr.repository.name}", "language": pr.repository.primary_language})
        result.append(data)
    return result


@router.post("/pull-requests", status_code=201)
def create_pull_request(
    payload: PullRequestCreate,
    user: User = Depends(require_roles(UserRole.PLATFORM_ADMIN.value, UserRole.ENGINEERING_MANAGER.value, UserRole.REPOSITORY_MAINTAINER.value)),
    db: Session = Depends(get_db),
) -> dict:
    repo = repository_or_404(db, payload.repository_id, user)
    row = PullRequest(**payload.model_dump())
    db.add(row); db.flush()
    record_audit(db, "pull_request.created", actor=user, repository_id=repo.id, pull_request_id=row.id, new_value={"number": row.github_number, "title": row.title})
    db.commit(); db.refresh(row)
    return serialize(row)


@router.get("/pull-requests/{pr_id}")
def pull_request_detail(pr_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    pr = pr_or_404(db, pr_id, user)
    data=serialize(pr)
    data["repository"]={"id":pr.repository.id,"full_name":f"{pr.repository.owner}/{pr.repository.name}","language":pr.repository.primary_language,"profile":pr.repository.active_review_profile}
    latest=db.query(ReviewRun).filter(ReviewRun.pull_request_id==pr.id).order_by(ReviewRun.version.desc()).first()
    data["latest_review"] = review_detail_payload(db, latest) if latest else None
    return data



@router.post("/pull-requests/{pr_id}/analyze")
def analyze_pull_request(
    pr_id: int,
    payload: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_roles(UserRole.PLATFORM_ADMIN.value, UserRole.ENGINEERING_MANAGER.value, UserRole.REPOSITORY_MAINTAINER.value, UserRole.DEVELOPER.value)),
    db: Session = Depends(get_db),
) -> dict:
    pr = pr_or_404(db, pr_id, user)
    if not payload.force and pr.analysis_status == "analysis_running":
        raise HTTPException(409, "Analysis is already running")
    record_audit(db, "review.analysis_requested", actor=user, repository_id=pr.repository_id, pull_request_id=pr.id, new_value={"trigger": payload.trigger_event})
    db.commit()
    if get_settings().demo_mode:
        run = execute_review(db, pr.id, payload.trigger_event)
        return {"queued": False, "review_run_id": run.id, "status": run.status}
    queued = enqueue_review(background_tasks, pr.id, payload.trigger_event)
    return {**queued, "pull_request_id": pr.id, "status": "pending_analysis"}


@router.get("/pull-requests/{pr_id}/review-history")
def review_history(pr_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    pr = pr_or_404(db, pr_id, user)
    rows = db.query(ReviewRun).filter(ReviewRun.pull_request_id == pr.id).order_by(ReviewRun.version.desc()).all()
    result=[]
    for row in rows:
        data=serialize(row)
        data.update({
            "findings_count": len(row.findings),
            "published_findings": sum(f.status == "published" for f in row.findings),
            "resolved_findings": sum(f.status == "fixed" for f in row.findings),
        })
        result.append(data)
    return result


def review_detail_payload(db: Session, run: ReviewRun) -> dict:
    data=serialize(run)
    data["findings"]=[serialize(f) for f in db.query(Finding).filter(Finding.review_run_id==run.id).order_by(Finding.severity, Finding.file_path).all()]
    data["analyzer_runs"]=[serialize(x) for x in db.query(AnalyzerRun).filter(AnalyzerRun.review_run_id==run.id).all()]
    data["test_recommendations"]=[serialize(x) for x in db.query(TestRecommendation).filter(TestRecommendation.review_run_id==run.id).all()]
    data["documentation_recommendations"]=[serialize(x) for x in db.query(DocumentationRecommendation).filter(DocumentationRecommendation.review_run_id==run.id).all()]
    data["publications"]=[serialize(x) for x in db.query(GitHubPublication).filter(GitHubPublication.review_run_id==run.id).all()]
    return data


@router.get("/review-runs/{review_run_id}")
def review_run_detail(review_run_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    run=db.query(ReviewRun).filter(ReviewRun.id==review_run_id).first()
    if not run: raise HTTPException(404,"Review run not found")
    ensure_same_organization(run.pull_request.repository.organization_id,user)
    return review_detail_payload(db,run)


@router.post("/review-runs/{review_run_id}/approve-all")
def approve_all(
    review_run_id: int,
    user: User = Depends(require_roles(UserRole.PLATFORM_ADMIN.value, UserRole.ENGINEERING_MANAGER.value, UserRole.REPOSITORY_MAINTAINER.value)),
    db: Session = Depends(get_db),
) -> dict:
    run=db.query(ReviewRun).filter(ReviewRun.id==review_run_id).first()
    if not run: raise HTTPException(404,"Review run not found")
    ensure_same_organization(run.pull_request.repository.organization_id,user)
    updated=0
    for finding in run.findings:
        if finding.status in {"awaiting_review","new","still_present"}:
            finding.status="approved"; updated+=1
            db.add(FindingDecision(finding_id=finding.id,reviewer_id=user.id,decision="approve"))
    run.status="approved_for_publication"; run.pull_request.review_status="approved_for_publication"
    record_audit(db,"review.approved_all",actor=user,repository_id=run.pull_request.repository_id,pull_request_id=run.pull_request_id,new_value={"findings":updated})
    db.commit()
    return {"approved":updated,"review_status":run.status}


@router.post("/findings/{finding_id}/decision")
def decide_finding(
    finding_id: int,
    payload: FindingDecisionRequest,
    user: User = Depends(require_roles(UserRole.PLATFORM_ADMIN.value, UserRole.ENGINEERING_MANAGER.value, UserRole.REPOSITORY_MAINTAINER.value, UserRole.DEVELOPER.value)),
    db: Session = Depends(get_db),
) -> dict:
    finding=db.query(Finding).filter(Finding.id==finding_id).first()
    if not finding: raise HTTPException(404,"Finding not found")
    ensure_same_organization(finding.review_run.pull_request.repository.organization_id,user)
    status_map={"approve":"approved","edit":"edited","dismiss":"dismissed","false_positive":"false_positive","suppress":"suppressed","internal_note":"internal_note","fixed":"fixed","reopen":"reopened"}
    old={"status":finding.status,"edited_content":finding.edited_content}
    finding.status=status_map[payload.decision]
    finding.edited_content=payload.edited_content
    finding.reviewer_comment=payload.comment
    db.add(FindingDecision(finding_id=finding.id,reviewer_id=user.id,decision=payload.decision,edited_content=payload.edited_content,comment=payload.comment))
    if payload.create_suppression or payload.decision=="suppress":
        db.add(SuppressionRule(repository_id=finding.review_run.pull_request.repository_id,rule_type="fingerprint",rule_identifier=finding.fingerprint,file_pattern=finding.file_path,reason=payload.comment or "Created from finding decision",created_by=user.id))
    record_audit(db,f"finding.{payload.decision}",actor=user,repository_id=finding.review_run.pull_request.repository_id,pull_request_id=finding.review_run.pull_request_id,old_value=old,new_value={"status":finding.status,"comment":payload.comment})
    db.commit(); db.refresh(finding)
    return serialize(finding)


@router.post("/review-runs/{review_run_id}/publish")
def publish(
    review_run_id:int,
    payload:PublishRequest,
    user:User=Depends(require_roles(UserRole.PLATFORM_ADMIN.value,UserRole.ENGINEERING_MANAGER.value,UserRole.REPOSITORY_MAINTAINER.value)),
    db:Session=Depends(get_db),
)->dict:
    run=db.query(ReviewRun).filter(ReviewRun.id==review_run_id).first()
    if not run: raise HTTPException(404,"Review run not found")
    ensure_same_organization(run.pull_request.repository.organization_id,user)
    publications=publish_review(db,review_run_id,payload.review_decision,payload.include_summary,payload.dry_run)
    record_audit(db,"review.published",actor=user,repository_id=run.pull_request.repository_id,pull_request_id=run.pull_request_id,new_value={"dry_run":payload.dry_run,"decision":payload.review_decision})
    db.commit()
    return {"published":len(publications),"items":[serialize(x) for x in publications]}


@router.get("/approvals")
def pending_approvals(user:User=Depends(get_current_user),db:Session=Depends(get_db))->list[dict]:
    rows=db.query(ReviewRun).join(PullRequest).join(Repository).filter(Repository.organization_id==user.organization_id,ReviewRun.status.in_(["awaiting_human_review","partially_approved","approved_for_publication"])).order_by(ReviewRun.completed_at.desc()).all()
    return [{**serialize(r),"repository":f"{r.pull_request.repository.owner}/{r.pull_request.repository.name}","pull_request_number":r.pull_request.github_number,"pull_request_title":r.pull_request.title,"risk_level":r.pull_request.risk_level,"total_findings":len(r.findings),"high_critical":sum(f.severity in {"high","critical"} for f in r.findings),"assigned_reviewer":r.pull_request.assigned_reviewer} for r in rows]


@router.get("/analytics/overview")
def analytics_overview(user:User=Depends(get_current_user),db:Session=Depends(get_db))->dict:
    repos=db.query(Repository).filter(Repository.organization_id==user.organization_id).all()
    repo_ids=[r.id for r in repos]
    prs=db.query(PullRequest).filter(PullRequest.repository_id.in_(repo_ids)).all() if repo_ids else []
    runs=[run for pr in prs for run in pr.review_runs]
    findings=[f for run in runs for f in run.findings]
    durations=[r.analysis_duration_ms for r in runs if r.analysis_duration_ms]
    categories=Counter(f.category for f in findings)
    false_positive=sum(f.status=="false_positive" for f in findings)
    decided=sum(f.status in {"approved","published","dismissed","false_positive","suppressed","fixed"} for f in findings)
    return {
        "connected_repositories":len(repos),"open_pull_requests":sum(pr.state=="open" for pr in prs),
        "awaiting_approval":sum(pr.review_status in {"awaiting_human_review","partially_approved","approved_for_publication"} for pr in prs),
        "high_risk_pull_requests":sum(pr.risk_level in {"high","critical"} for pr in prs),
        "critical_findings":sum(f.severity=="critical" and f.status not in {"fixed","dismissed","false_positive"} for f in findings),
        "published_reviews":sum(r.status=="published" for r in runs),"failed_analysis_jobs":sum(r.status=="failed" for r in runs),
        "average_review_duration_ms":round(sum(durations)/len(durations)) if durations else 0,
        "most_common_category":categories.most_common(1)[0][0] if categories else None,
        "false_positive_rate":round(false_positive/decided*100,1) if decided else 0,
        "findings_by_category":[{"name":k,"value":v} for k,v in categories.most_common()],
        "risk_distribution":[{"name":level.title(),"value":sum(pr.risk_level==level for pr in prs)} for level in ["low","moderate","high","critical"]],
    }


@router.get("/analytics/security")
def security_analytics(user:User=Depends(get_current_user),db:Session=Depends(get_db))->dict:
    findings=db.query(Finding).join(ReviewRun).join(PullRequest).join(Repository).filter(Repository.organization_id==user.organization_id,Finding.category=="security").all()
    by_repo=Counter(f"{f.review_run.pull_request.repository.owner}/{f.review_run.pull_request.repository.name}" for f in findings)
    by_severity=Counter(f.severity for f in findings)
    return {"total":len(findings),"unresolved":sum(f.status not in {"fixed","dismissed","false_positive","suppressed"} for f in findings),"by_repository":[{"name":k,"value":v} for k,v in by_repo.most_common()],"by_severity":[{"name":k,"value":v} for k,v in by_severity.items()],"recent":[serialize(f) for f in findings[-20:]]}


@router.get("/analytics/quality")
def quality_analytics(user:User=Depends(get_current_user),db:Session=Depends(get_db))->dict:
    findings=db.query(Finding).join(ReviewRun).join(PullRequest).join(Repository).filter(Repository.organization_id==user.organization_id).all()
    accepted=sum(f.status in {"approved","published","fixed"} for f in findings)
    rejected=sum(f.status in {"dismissed","false_positive","suppressed"} for f in findings)
    return {"findings":len(findings),"accepted":accepted,"rejected":rejected,"accepted_rate":round(accepted/max(accepted+rejected,1)*100,1),"false_positive_rate":round(sum(f.status=="false_positive" for f in findings)/max(accepted+rejected,1)*100,1),"by_category":[{"name":k,"value":v} for k,v in Counter(f.category for f in findings).most_common()],"by_status":[{"name":k,"value":v} for k,v in Counter(f.status for f in findings).most_common()]}


@router.get("/audit-logs")
def audit_logs(limit:int=100,user:User=Depends(get_current_user),db:Session=Depends(get_db))->list[dict]:
    rows=db.query(AuditLog).filter(AuditLog.organization_id==user.organization_id).order_by(AuditLog.created_at.desc()).limit(min(limit,500)).all()
    result=[]
    for row in rows:
        data=serialize(row)
        actor=db.get(User,row.actor_id) if row.actor_id else None
        data["actor_name"]=actor.name if actor else "System"
        result.append(data)
    return result


@router.get("/notifications")
def notifications(user:User=Depends(get_current_user),db:Session=Depends(get_db))->list[dict]:
    return [serialize(x) for x in db.query(Notification).filter(Notification.user_id==user.id).order_by(Notification.created_at.desc()).limit(100)]


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(notification_id:int,user:User=Depends(get_current_user),db:Session=Depends(get_db))->dict:
    row=db.query(Notification).filter(Notification.id==notification_id,Notification.user_id==user.id).first()
    if not row: raise HTTPException(404,"Notification not found")
    row.is_read=True; db.commit(); return serialize(row)


@router.get("/integrations/github/status")
def github_status(user:User=Depends(get_current_user),db:Session=Depends(get_db))->dict:
    org=db.get(Organization,user.organization_id)
    client=GitHubAppClient()
    return {"configured":client.configured,"demo_mode":get_settings().demo_mode,"organization_installation_id":org.github_installation_id,"webhook_secret_configured":get_settings().github_webhook_secret!="change-webhook-secret","permissions":["metadata:read","contents:read","pull_requests:write","checks:read"]}


@router.get("/failed-jobs")
def failed_jobs(user:User=Depends(get_current_user),db:Session=Depends(get_db))->list[dict]:
    rows=db.query(ReviewRun).join(PullRequest).join(Repository).filter(Repository.organization_id==user.organization_id,ReviewRun.status=="failed").all()
    return [{**serialize(r),"repository":f"{r.pull_request.repository.owner}/{r.pull_request.repository.name}","pull_request_number":r.pull_request.github_number} for r in rows]


@router.post("/failed-jobs/{review_run_id}/retry")
def retry_failed(review_run_id:int,user:User=Depends(require_roles(UserRole.PLATFORM_ADMIN.value,UserRole.REPOSITORY_MAINTAINER.value)),db:Session=Depends(get_db))->dict:
    run=db.query(ReviewRun).filter(ReviewRun.id==review_run_id,ReviewRun.status=="failed").first()
    if not run: raise HTTPException(404,"Failed review run not found")
    ensure_same_organization(run.pull_request.repository.organization_id,user)
    new_run=execute_review(db,run.pull_request_id,"manual.retry")
    return {"review_run_id":new_run.id,"status":new_run.status}


@router.post("/webhooks/github")
async def github_webhook(request:Request,background_tasks:BackgroundTasks,db:Session=Depends(get_db))->dict:
    body=await request.body()
    signature=request.headers.get("X-Hub-Signature-256")
    delivery=request.headers.get("X-GitHub-Delivery") or f"manual-{int(datetime.now(timezone.utc).timestamp()*1000)}"
    event_name=request.headers.get("X-GitHub-Event","unknown")
    if not verify_webhook_signature(body,signature):
        raise HTTPException(401,"Invalid webhook signature")
    existing=db.query(WebhookEvent).filter(WebhookEvent.delivery_id==delivery).first()
    if existing:
        return {"accepted":True,"delivery_id":delivery,"status":"duplicate","detail":"Event already processed"}
    payload=await request.json()
    action=payload.get("action")
    repository_full_name=(payload.get("repository") or {}).get("full_name")
    row=WebhookEvent(delivery_id=delivery,event_name=event_name,action=action,repository_full_name=repository_full_name,payload=payload,status="received")
    db.add(row); db.commit()
    if event_name=="pull_request" and action in {"opened","reopened","synchronize","review_requested"} and repository_full_name:
        owner,name=repository_full_name.split("/",1)
        github_repository_id=str((payload.get("repository") or {}).get("id") or "")
        installation_id=str((payload.get("installation") or {}).get("id") or "")
        organization = db.query(Organization).filter(Organization.github_installation_id == installation_id).first() if installation_id else None
        repo_query=db.query(Repository)
        if organization:
            repo_query = repo_query.filter(Repository.organization_id == organization.id)
        repo=repo_query.filter(Repository.github_repository_id==github_repository_id).first() if github_repository_id else None
        repo=repo or repo_query.filter(Repository.owner==owner,Repository.name==name).first()
        if repo:
            gh_pr=payload.get("pull_request") or {}
            number=int((payload.get("number") or gh_pr.get("number") or 0))
            pr=db.query(PullRequest).filter(PullRequest.repository_id==repo.id,PullRequest.github_number==number).first()
            values={
                "title":gh_pr.get("title","Untitled pull request"),"description":gh_pr.get("body") or "","author":(gh_pr.get("user") or {}).get("login","unknown"),
                "base_branch":(gh_pr.get("base") or {}).get("ref","main"),"head_branch":(gh_pr.get("head") or {}).get("ref","feature"),
                "current_commit_sha":(gh_pr.get("head") or {}).get("sha","unknown"),"changed_files_count":gh_pr.get("changed_files",0),"additions":gh_pr.get("additions",0),"deletions":gh_pr.get("deletions",0),
                "changed_files":[],"commits":[],"diff_text":"",
            }
            if not get_settings().demo_mode and GitHubAppClient().configured:
                try:
                    values.update(RepositoryContextCollector().collect_pull_request(owner,name,number, repo.policy.ignored_paths if repo.policy else []))
                except Exception as exc:
                    row.error_details=f"Context collection failed; webhook metadata retained: {exc}"
            if not pr:
                pr=PullRequest(repository_id=repo.id,github_number=number,**values); db.add(pr)
            else:
                for key,value in values.items(): setattr(pr,key,value)
            db.flush(); row.status="processed"; db.commit()
            policy = repo.policy
            eligible = bool(policy and policy.review_enabled and values["base_branch"] in policy.monitored_branches)
            if action == "synchronize" and policy and not policy.re_review_on_push:
                eligible = False
            if eligible:
                if get_settings().demo_mode:
                    execute_review(db,pr.id,f"pull_request.{action}")
                else:
                    enqueue_review(background_tasks, pr.id, f"pull_request.{action}")
            elif policy:
                pr.analysis_status = "ignored_by_policy"
                pr.review_status = "ignored_by_policy"
                row.error_details = "Pull request is outside the configured review policy"
                db.commit()
        else:
            row.status="ignored"
            row.error_details="Repository is not connected to this platform"
            db.commit()
    return {"accepted":True,"delivery_id":delivery,"status":row.status,"detail":"Webhook accepted"}
