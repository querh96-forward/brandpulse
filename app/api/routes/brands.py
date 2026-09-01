import uuid
from datetime import UTC, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.brand import Brand
from app.schemas.brand import BrandCreate, BrandRead
from app.schemas.report import (
    BrandRiskSummary,
    BrandRiskTrendPoint,
    HighRiskArticleRead,
)
from app.services.report import (
    build_brand_risk_summary,
    build_brand_risk_trend,
    list_brand_high_risk_articles,
)

router = APIRouter(prefix="/brands", tags=["brands"])


@router.post("", response_model=BrandRead, status_code=status.HTTP_201_CREATED)
async def create_brand(
    payload: BrandCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Brand:
    existing_brand = await session.scalar(select(Brand).where(Brand.name == payload.name))

    if existing_brand is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="brand name already exists",
        )

    brand = Brand(
        name=payload.name,
        description=payload.description,
    )

    session.add(brand)
    await session.commit()
    await session.refresh(brand)

    return brand


@router.get("", response_model=list[BrandRead])
async def list_brands(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[Brand]:
    result = await session.scalars(
        select(Brand).order_by(Brand.created_at.desc()).offset(offset).limit(limit)
    )

    return list(result.all())


@router.get(
    "/{brand_id}/risk-summary",
    response_model=BrandRiskSummary,
)
async def get_brand_risk_summary(
    brand_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BrandRiskSummary:
    brand = await session.get(Brand, brand_id)

    if brand is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="brand not found",
        )

    return await build_brand_risk_summary(
        session=session,
        brand_id=brand_id,
    )


@router.get(
    "/{brand_id}/high-risk-articles",
    response_model=list[HighRiskArticleRead],
)
async def get_brand_high_risk_articles(
    brand_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[HighRiskArticleRead]:
    brand = await session.get(Brand, brand_id)

    if brand is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="brand not found",
        )

    return await list_brand_high_risk_articles(
        session=session,
        brand_id=brand_id,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{brand_id}/risk-trend",
    response_model=list[BrandRiskTrendPoint],
)
async def get_brand_risk_trend(
    brand_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> list[BrandRiskTrendPoint]:
    brand = await session.get(Brand, brand_id)

    if brand is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="brand not found",
        )

    start_day = datetime.now(UTC).date() - timedelta(
        days=days - 1,
    )
    since = datetime.combine(
        start_day,
        time.min,
        tzinfo=UTC,
    )

    return await build_brand_risk_trend(
        session=session,
        brand_id=brand_id,
        since=since,
    )


@router.get("/{brand_id}", response_model=BrandRead)
async def get_brand(
    brand_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Brand:
    brand = await session.get(Brand, brand_id)

    if brand is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="brand not found",
        )

    return brand
