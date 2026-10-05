"""The append-only audit writer.

docs/04 4.6: Writing, Plot Studio and Literature are siblings that "feed downward into
Research Integrity". Integrity is a substrate, not a per-module feature, so all three
write through THIS module -- one mechanism, not three.

Three properties the rest of the system depends on:

1. ``attribution`` is decided by the caller and cannot be omitted. ``record()`` takes
   either a user or a component name and derives HUMAN/SOFTWARE from that, so no call
   site can invent a third attribution or leave it blank.

2. Nothing is ever updated or deleted. There is no ``update`` or ``delete`` function in
   this module, and ``AuditLog`` has no ``updated_at``.

3. Document-wide rewrites write ONE ROW PER CHANGE sharing a ``batch_id``
   (docs/07 7.6 step 6). A single summary row for a 400-replacement consistency run
   would satisfy "we logged it" while destroying the ability to answer "what exactly
   changed, and who reverted it".
"""
from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from scix.models import AuditLog
from scix.models.enums import Attributed, TargetKind


class AttributionError(ValueError):
    """Raised when a caller has not identified WHO acted.

    Deliberately an error rather than a default. Defaulting to SOFTWARE would let a
    human edit be logged as machine output, which is the exact failure mode R5 exists
    to prevent -- and a default is invisible, whereas an exception stops the write.
    """


@dataclass(frozen=True)
class Actor:
    """Who performed an action. Construct one of the two classmethods."""

    attribution: Attributed
    user_id: str | None = None
    component: str | None = None
    tool_version: str | None = None

    @classmethod
    def human(cls, user_id: str, tool_version: str | None = None) -> "Actor":
        if not user_id:
            raise AttributionError("human actor requires a user id")
        return cls(Attributed.HUMAN, user_id=user_id, tool_version=tool_version)

    @classmethod
    def software(cls, component: str, tool_version: str | None = None) -> "Actor":
        """A machine action. ``component`` names WHICH component -- grammar,
        consistency, matplotlib, statistics -- because "software" alone is not enough to
        reconstruct how a value was produced."""
        if not component:
            raise AttributionError("software actor requires a component name")
        return cls(Attributed.SOFTWARE, component=component, tool_version=tool_version)

    def validate(self) -> None:
        # Mirrors the database CHECK. Kept in application code so the caller gets a clear
        # message naming the actor, instead of a psycopg constraint violation naming a
        # column. The database still has the final say.
        if self.attribution is Attributed.HUMAN and self.user_id is None:
            raise AttributionError("HUMAN attribution requires actor_user_id")
        if self.attribution is Attributed.SOFTWARE and self.user_id is not None:
            raise AttributionError("SOFTWARE attribution must not carry a user id")
        if self.attribution is Attributed.SOFTWARE and not self.component:
            raise AttributionError("SOFTWARE attribution requires actor_component")


@dataclass
class Change:
    """One before/after pair, for a document-wide rewrite.

    ``offset_start``/``offset_end`` locate the change in the revision it was computed
    against, so a revert can find it even after later edits shifted offsets.
    """

    target_type: TargetKind
    target_id: str
    action: str
    before_value: dict[str, Any] | None = None
    after_value: dict[str, Any] | None = None
    detail: dict[str, Any] | None = None
    offset_start: int | None = None
    offset_end: int | None = None


@dataclass
class BatchRecorder:
    """Collects changes, then writes them as one ``batch_id``.

    Used as a context manager so a rewrite that raises part-way writes nothing at all,
    rather than leaving a partial rewrite with a partial log::

        with BatchRecorder(session, project_id, Actor.software("consistency")) as batch:
            for change in changes:
                batch.add(change)
    """

    session: Session
    project_id: str
    actor: Actor
    batch_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    _changes: list[Change] = field(default_factory=list)

    def add(self, change: Change) -> None:
        self._changes.append(change)

    def extend(self, changes: Iterable[Change]) -> None:
        self._changes.extend(changes)

    def flush(self) -> list[AuditLog]:
        return [
            record(
                session=self.session,
                project_id=self.project_id,
                actor=self.actor,
                action=c.action,
                target_type=c.target_type,
                target_id=c.target_id,
                before_value=c.before_value,
                after_value=c.after_value,
                detail=c.detail,
                batch_id=self.batch_id,
                occurred_at=None,
            )
            for c in self._changes
        ]

    def __enter__(self) -> "BatchRecorder":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is not None:
            return  # nothing written; caller's transaction rolls back
        self.flush()


def record(
    session: Session,
    *,
    project_id: str,
    actor: Actor,
    action: str,
    target_type: TargetKind,
    target_id: str | None = None,
    before_value: dict[str, Any] | None = None,
    after_value: dict[str, Any] | None = None,
    detail: dict[str, Any] | None = None,
    batch_id: str | None = None,
    occurred_at: datetime | None = None,
) -> AuditLog:
    """Append one event. This is the ONLY way an audit row is created."""
    actor.validate()
    if not action:
        raise ValueError("audit action is required")

    row = AuditLog(
        project_id=project_id,
        attribution=actor.attribution,
        actor_user_id=actor.user_id,
        actor_component=actor.component,
        tool_version=actor.tool_version,
        action=action,
        target_type=target_type,
        target_id=target_id,
        before_value=before_value,
        after_value=after_value,
        detail=detail,
        batch_id=batch_id,
        created_at=occurred_at or datetime.now(timezone.utc),
    )
    session.add(row)
    session.flush()
    return row


def record_many(
    session: Session,
    *,
    project_id: str,
    actor: Actor,
    changes: Sequence[Change],
    batch_id: str | None = None,
) -> list[AuditLog]:
    """One row per change, sharing a batch id."""
    return [
        record(
            session=session,
            project_id=project_id,
            actor=actor,
            action=c.action,
            target_type=c.target_type,
            target_id=c.target_id,
            before_value=c.before_value,
            after_value=c.after_value,
            detail=c.detail,
            batch_id=batch_id,
        )
        for c in changes
    ]


# --- components ------------------------------------------------------------- #
# Named constants, so "which software did this" is a closed set rather than a typo
# space. A misspelt component string in the audit log is unrecoverable history.

COMPONENT_INGEST = "ingest"
COMPONENT_TRANSFORM = "transform"
COMPONENT_STATISTICS = "statistics"
COMPONENT_GRAPH = "plotly"
COMPONENT_RENDER = "matplotlib"
COMPONENT_TERMINOLOGY = "terminology"
COMPONENT_CONSISTENCY = "consistency"
COMPONENT_EXPORT = "export"
COMPONENT_AUDIT = "audit"