from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.db.session import get_db_session
from app.main import app
from app.providers.dependencies import get_analysis_provider
from app.providers.rule_based import RuleBasedAnalysisProvider

settings = get_settings()

test_engine = create_async_engine(
    settings.test_database_url,
    poolclass=NullPool,
)


@pytest.fixture(autouse=True)
def force_rule_based_analysis_provider() -> Iterator[None]:
    def override_get_analysis_provider() -> RuleBasedAnalysisProvider:
        return RuleBasedAnalysisProvider()

    app.dependency_overrides[get_analysis_provider] = override_get_analysis_provider

    try:
        yield
    finally:
        app.dependency_overrides.pop(get_analysis_provider, None)


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with test_engine.connect() as connection:
        transaction = await connection.begin()

        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        try:
            yield session
        finally:
            await session.close()

            if transaction.is_active:
                await transaction.rollback()


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession,
) -> AsyncIterator[AsyncClient]:
    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db_session, None)
