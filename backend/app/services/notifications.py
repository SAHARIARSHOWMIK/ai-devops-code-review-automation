from sqlalchemy.orm import Session
from ..models import Notification, User


def notify_role(db: Session, organization_id: int, roles: set[str], title: str, message: str, notification_type: str, review_id: int | None = None) -> int:
    users = db.query(User).filter(User.organization_id == organization_id, User.role.in_(roles), User.is_active.is_(True)).all()
    for user in users:
        db.add(Notification(user_id=user.id, type=notification_type, title=title, message=message, related_review_id=review_id))
    return len(users)
