"""API dependencies.

Auth is deliberately minimal at this stage and deliberately *honest* about it: a
single ``X-Scix-User`` header identifies the acting researcher, because row-level
project ownership is required "from day one" (docs/04 4.7) but real institutional
SSO is Stage 4. The header is a stand-in with the same shape as a session, so swapping
in JWT/OIDC later touches this module and nothing else.
"""
from __future__ import annotations

import uuid

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from scix.db.session import get_db
from scix.models import Project, User
from scix.models.enums import UserRole

DEV_USER_EMAIL = "researcher@scix.local"


def get_current_user(
    session: Session = Depends(get_db),
    x_scix_user: str | None = Header(default=None, alias="X-Scix-User"),
) -> User:
    """Resolve the acting user.

    With no header, resolves to the seeded development researcher so the API is usable
    out of the box. This fallback is a development affordance and must be removed before
    any deployment where more than one person can reach it.
    """
    if x_scix_user:
        try:
            user_id = uuid.UUID(x_scix_user)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-Scix-User must be a UUID",
            ) from exc
        user = session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown user")
        return user

    user = session.query(User).filter(User.email == DEV_USER_EMAIL).one_or_none()
    if user is None:
        user = ensure_dev_user(session)
    return user


def ensure_dev_user(session: Session) -> User:
    user = User(
        email=DEV_USER_EMAIL,
        full_name="Development Researcher",
        hashed_password="not-a-real-hash",
        role=UserRole.RESEARCHER,
    )
    session.add(user)
    session.flush()
    session.commit()
    session.refresh(user)
    return user


def require_project(
    project_id: uuid.UUID,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Project:
    """Load a project and enforce ownership.

    Ownership is checked on every project-scoped read, not just at creation. Without
    this, any authenticated user can read any project by guessing a UUID -- and these
    UUIDs are not secret, they appear in export metadata and audit records.
    """
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    if project.owner_id != user.id and user.role not in (UserRole.ADMIN,):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="project belongs to another researcher",
        )
    return project