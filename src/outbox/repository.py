from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Outbox


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(
        self,
        event_type: str,
        aggregate_id: UUID,
        payload: dict
    ) -> Outbox:
        outbox = Outbox(
            event_type=event_type,
            aggregate_id=aggregate_id,
            payload=payload
        )

        self.session.add(outbox)
        await self.session.flush()

        return outbox

    async def get_pending(self, limit: int = 100) -> list[Outbox]:
        result = await self.session.execute(
            select(Outbox)
            .where(Outbox.published_at.is_(None))
            .order_by(Outbox.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )

        return list(result.scalars().all())

    async def mark_published(self, event_id: UUID) -> None:
        event = await self.session.get(Outbox, event_id)

        if event is not None:
            event.published_at = datetime.now(timezone.utc)

    async def increment_attempts(self, event_id: UUID) -> None:
        event = await self.session.get(Outbox, event_id)

        if event is not None:
            event.attempts += 1
