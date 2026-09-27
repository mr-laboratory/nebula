"""Record privileged actions in the audit log, inside the caller's transaction.

Writing in the same transaction as the action means the two commit or roll back together:
there is never an action without its entry, or an entry for an action that didn't happen.
"""

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditAction, AuditLog, User

logger = logging.getLogger(__name__)


def record(
    session: AsyncSession,
    actor: User | None,
    action: AuditAction,
    target_type: str,
    target_id: uuid.UUID,
    **details: Any,
) -> None:
    """Add an entry. `actor` is None for command-line actions. Details: ids and labels only."""
    actor_id = actor.id if actor else None
    session.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
        )
    )
    logger.info(
        "audit",
        extra={"action": str(action), "actor_id": str(actor_id), "target_id": str(target_id)},
    )
