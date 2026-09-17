from collections.abc import AsyncIterable

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from core.settings import settings
from infrastructure.database.database import Database


class DatabaseProvider(Provider):
    @provide(scope=Scope.APP)
    async def database(self) -> AsyncIterable[Database]:
        database = Database(
            database_url=str(settings.POSTGRES_DSN),
        )
        yield database
        await database.close()

    @provide(scope=Scope.REQUEST)
    async def session(self, database: Database) -> AsyncIterable[AsyncSession]:
        async with database.session_factory() as session:
            yield session
