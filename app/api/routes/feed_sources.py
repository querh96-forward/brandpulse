import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.http import get_http_client
from app.core.redis import get_redis_client
from app.db.session import get_db_session
from app.models.brand import Brand
from app.models.feed_source import FeedSource
from app.schemas.feed_source import (
    FeedCollectionRead,
    FeedSourceCreate,
    FeedSourceRead,
    FeedSourceUpdate,
)
from app.services.feed_source import collect_feed_source

router = APIRouter(prefix="/feed-sources", tags=["feed-sources"])


@router.post("", response_model=FeedSourceRead, status_code=status.HTTP_201_CREATED)
async def create_feed_source(
    payload: FeedSourceCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FeedSource:
    brand = await session.get(Brand, payload.brand_id)

    if brand is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="brand not found",
        )

    source = FeedSource(
        brand_id=payload.brand_id,
        name=payload.name,
        feed_url=str(payload.feed_url),
        enabled=payload.enabled,
        interval_minutes=payload.interval_minutes,
        max_articles_per_collection=payload.max_articles_per_collection,
    )
    session.add(source)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="feed URL already exists for this brand",
        ) from exc

    await session.refresh(source)
    return source


@router.get("", response_model=list[FeedSourceRead])
async def list_feed_sources(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    brand_id: uuid.UUID | None = None,
    enabled: bool | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[FeedSource]:
    statement = select(FeedSource)

    if brand_id is not None:
        statement = statement.where(FeedSource.brand_id == brand_id)

    if enabled is not None:
        statement = statement.where(FeedSource.enabled == enabled)

    result = await session.scalars(
        statement.order_by(FeedSource.created_at.desc()).offset(offset).limit(limit)
    )
    return list(result.all())


@router.get("/{feed_source_id}", response_model=FeedSourceRead)
async def get_feed_source(
    feed_source_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FeedSource:
    source = await session.get(FeedSource, feed_source_id)

    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="feed source not found",
        )

    return source


@router.patch("/{feed_source_id}", response_model=FeedSourceRead)
async def update_feed_source(
    feed_source_id: uuid.UUID,
    payload: FeedSourceUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FeedSource:
    source = await session.get(FeedSource, feed_source_id)

    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="feed source not found",
        )

    changes = payload.model_dump(exclude_unset=True)

    if "feed_url" in changes:
        changes["feed_url"] = str(changes["feed_url"])

    for field_name, value in changes.items():
        setattr(source, field_name, value)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="feed URL already exists for this brand",
        ) from exc

    await session.refresh(source)
    return source


@router.post("/{feed_source_id}/collect", response_model=FeedCollectionRead)
async def collect_feed_source_now(
    feed_source_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis_client: Annotated[Redis, Depends(get_redis_client)],
    http_client: Annotated[AsyncClient, Depends(get_http_client)],
) -> FeedCollectionRead:
    source = await session.get(FeedSource, feed_source_id)

    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="feed source not found",
        )

    try:
        result = await collect_feed_source(
            session=session,
            redis_client=redis_client,
            http_client=http_client,
            source=source,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"feed collection failed: {exc}",
        ) from exc

    return FeedCollectionRead(
        feed_source_id=source.id,
        **result.__dict__,
    )
