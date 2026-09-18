from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from infrastructure.messaging.retry import MAX_RETRIES, RETRY_HEADER, handle_with_retry


@pytest.fixture
def msg():
    message = MagicMock()
    message.headers = {}
    message.ack = AsyncMock()
    message.nack = AsyncMock()
    return message


@pytest.fixture
def broker():
    broker = MagicMock()
    broker.publish = AsyncMock()
    return broker


@pytest.fixture
def queue():
    return MagicMock(name="queue")


@pytest.fixture
def exchange():
    return MagicMock(name="exchange")


@pytest.mark.asyncio
async def test_handle_with_retry_republishes_with_incremented_counter(
    msg, broker, queue, exchange,
):
    body = MagicMock()

    with patch(
        "infrastructure.messaging.retry.asyncio.sleep", AsyncMock(),
    ) as sleep_mock:
        await handle_with_retry(msg, broker, queue, exchange, body)

    sleep_mock.assert_awaited_once_with(1.0)
    broker.publish.assert_awaited_once_with(
        body,
        queue=queue,
        exchange=exchange,
        headers={RETRY_HEADER: "1"},
    )
    msg.ack.assert_awaited_once()
    msg.nack.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_with_retry_uses_exponential_backoff(msg, broker, queue, exchange):
    msg.headers = {RETRY_HEADER: "2"}
    body = MagicMock()

    with patch(
        "infrastructure.messaging.retry.asyncio.sleep", AsyncMock(),
    ) as sleep_mock:
        await handle_with_retry(msg, broker, queue, exchange, body)

    sleep_mock.assert_awaited_once_with(4.0)
    broker.publish.assert_awaited_once_with(
        body,
        queue=queue,
        exchange=exchange,
        headers={RETRY_HEADER: "3"},
    )
    msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_with_retry_sends_to_dlq_after_max_retries(
    msg, broker, queue, exchange,
):
    msg.headers = {RETRY_HEADER: str(MAX_RETRIES)}
    body = MagicMock()

    await handle_with_retry(msg, broker, queue, exchange, body)

    broker.publish.assert_not_awaited()
    msg.ack.assert_not_awaited()
    msg.nack.assert_awaited_once_with(requeue=False)
