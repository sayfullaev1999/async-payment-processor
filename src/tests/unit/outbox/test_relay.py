from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from infrastructure.messaging.broker import payments_exchange
from outbox.models import Outbox
from outbox.relay import OutboxRelay


class _FakeSessionContext:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _make_event(event_type="payments.new", attempts=0):
    event_id = uuid4()
    return Outbox(
        id=event_id,
        event_type=event_type,
        aggregate_id=event_id,
        payload={"payment_id": str(event_id)},
        attempts=attempts,
    )


@pytest.fixture
def session():
    session = MagicMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def database(session):
    database = MagicMock()
    database.session_factory = MagicMock(return_value=_FakeSessionContext(session))
    return database


@pytest.fixture
def broker():
    broker = MagicMock()
    broker.publish = AsyncMock()
    return broker


@pytest.fixture
def relay(broker, database):
    return OutboxRelay(broker=broker, database=database, poll_interval=0, batch_size=10)


@pytest.mark.asyncio
async def test_process_batch_publishes_and_marks_all_pending_events(
    relay, broker, session,
):
    event1 = _make_event()
    event2 = _make_event(event_type="payments.webhook")

    mock_repo = MagicMock()
    mock_repo.get_pending = AsyncMock(return_value=[event1, event2])
    mock_repo.mark_published = AsyncMock()
    mock_repo.increment_attempts = AsyncMock()

    with patch("outbox.relay.OutboxRepository", return_value=mock_repo):
        await relay._process_batch()

    assert broker.publish.await_count == 2
    broker.publish.assert_any_await(
        event1.payload, exchange=payments_exchange, routing_key=event1.event_type,
    )
    broker.publish.assert_any_await(
        event2.payload, exchange=payments_exchange, routing_key=event2.event_type,
    )
    mock_repo.mark_published.assert_any_await(event1.id)
    mock_repo.mark_published.assert_any_await(event2.id)
    mock_repo.increment_attempts.assert_not_awaited()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_batch_isolates_a_failing_event_and_still_commits_the_rest(
    relay, broker, session,
):
    good_event = _make_event()
    bad_event = _make_event(event_type="payments.webhook")

    broker.publish = AsyncMock(side_effect=[None, Exception("amqp unavailable")])

    mock_repo = MagicMock()
    mock_repo.get_pending = AsyncMock(return_value=[good_event, bad_event])
    mock_repo.mark_published = AsyncMock()
    mock_repo.increment_attempts = AsyncMock()

    with patch("outbox.relay.OutboxRepository", return_value=mock_repo):
        await relay._process_batch()

    mock_repo.mark_published.assert_awaited_once_with(good_event.id)
    mock_repo.increment_attempts.assert_awaited_once_with(bad_event.id)
    # ключевая проверка: сбой одного события не срывает commit остальных
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_batch_does_nothing_when_no_pending_events(relay, broker, session):
    mock_repo = MagicMock()
    mock_repo.get_pending = AsyncMock(return_value=[])
    mock_repo.mark_published = AsyncMock()
    mock_repo.increment_attempts = AsyncMock()

    with patch("outbox.relay.OutboxRepository", return_value=mock_repo):
        await relay._process_batch()

    broker.publish.assert_not_awaited()
    mock_repo.mark_published.assert_not_awaited()
    session.commit.assert_awaited_once()
