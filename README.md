# async-payment-processor

Asynchronous payment processing service built with **FastAPI**, **RabbitMQ**, **PostgreSQL**, **FastStream**, and **Dishka**.

## Architecture

```text
                    ┌──────────────┐
                    │    Client    │
                    └──────┬───────┘
                           │ HTTP
                           ▼
                    ┌──────────────┐
                    │     API      │
                    │   FastAPI    │
                    └──────┬───────┘
                           │
                           │ PaymentNewMessage
                           ▼
                    ┌──────────────┐
                    │   RabbitMQ   │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   Consumer   │
                    │  FastStream  │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  PostgreSQL  │
                    └──────┬───────┘
                           │
                           │ Outbox event
                           ▼
                    ┌──────────────┐
                    │   RabbitMQ   │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │    Webhook   │
                    │   Consumer   │
                    └──────────────┘
```

## Tech Stack

- Python 3.10+
- FastAPI
- SQLAlchemy 2
- PostgreSQL 18
- Alembic
- RabbitMQ 4
- FastStream
- Dishka
- Pydantic v2
- Docker Compose
- pytest
- pytest-asyncio

## Project Structure

```text
src/
├── api/
├── core/
├── domain/
│   └── payments/
├── infrastructure/
│   ├── database/
│   └── messaging/
├── tests/
│   ├── unit/
│   │   └── payments/
│   │       └── test_service.py
│   └── integration/
├── main.py
└── worker.py

alembic/
docker-compose.yml
Dockerfile
.env
```

## Payment Flow

1. Client creates a payment through the API.
2. API stores the payment in PostgreSQL.
3. API publishes `PaymentNewMessage` to RabbitMQ.
4. Payment consumer receives the message.
5. Consumer processes the payment asynchronously.
6. Payment status is updated in PostgreSQL.
7. A webhook delivery event is stored using the Outbox pattern.
8. The event is published to RabbitMQ.
9. Webhook consumer handles webhook delivery.

Payment lifecycle:

```text
PENDING
   │
   ├──► SUCCEEDED
   │
   └──► FAILED
```

## Transactional Outbox

The project uses the Transactional Outbox pattern to keep database changes and event creation atomic.

Instead of:

```text
UPDATE payment
      ↓
RabbitMQ publish
```

the payment update and outbox event are written in the same PostgreSQL transaction:

```text
BEGIN
   │
   ├── UPDATE payment
   │
   └── INSERT outbox event
   │
COMMIT
```

The outbox publisher can then publish the event to RabbitMQ.

This prevents losing an event when the database transaction succeeds but message publishing fails.

## Docker Compose

The project runs as several separate containers:

```text
postgres
rabbitmq
migrate
api
consumer
```

All services communicate through the internal Docker Compose network.

### Internal services

PostgreSQL:

```text
postgres:5432
```

RabbitMQ:

```text
rabbitmq:5672
```

PostgreSQL and RabbitMQ ports are **not exposed to the host**.

Only the API is exposed:

```text
localhost:8000
```

## Environment

Create `.env` in the project root:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=async_payment

POSTGRES_DSN=postgresql+asyncpg://postgres:postgres@postgres:5432/async_payment

RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/

API_KEY=your-api-key
```

When running inside Docker, use the Docker service names (`postgres`, `rabbitmq`) instead of `localhost`.

## Run with Docker

Build and start all services:

```bash
docker compose up --build
```

Services are started in the following dependency order:

```text
PostgreSQL
    ↓
RabbitMQ
    ↓
migrations
    ↓
API + consumer
```

Database migrations are executed automatically by the `migrate` service.

## API

API:

```text
http://localhost:8000
```

Swagger UI:

```text
http://localhost:8000/docs
```

OpenAPI:

```text
http://localhost:8000/openapi.json
```

## Database Migrations

Create a new migration:

```bash
docker compose run --rm migrate \
    alembic revision --autogenerate -m "migration message"
```

Apply migrations:

```bash
docker compose run --rm migrate
```

## Consumer

The consumer runs as a separate Docker service:

```bash
docker compose up consumer
```

It uses:

- FastStream
- RabbitMQ
- Dishka
- SQLAlchemy
- PostgreSQL

The consumer is separated from the HTTP API so asynchronous payment processing does not block API requests.

## Local Development

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the API:

```bash
uvicorn main:app --reload
```

Run the consumer:

```bash
python worker.py
```

When running outside Docker, configure `.env` with connection addresses available from the host environment.

## License

This project is intended for educational and demonstration purposes.
