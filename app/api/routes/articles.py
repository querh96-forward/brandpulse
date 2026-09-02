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
from app.models.analysis import AnalysisResult
from app.models.analysis_job import AnalysisJob, AnalysisJobStatus
from app.models.article import Article
from app.models.brand import Brand
from app.providers.base import AnalysisProvider
from app.providers.dependencies import get_analysis_provider
from app.schemas.analysis import (
    AnalysisJobRead,
    AnalysisRead,
    AnalysisStatusRead,
)
from app.schemas.article import (
    ArticleCreate,
    ArticleRead,
    RssImportRead,
    RssImportRequest,
)
from app.services.analysis import analyze_and_save_article
from app.services.analysis_queue import enqueue_analysis_job
from app.services.article import calculate_content_hash, save_collected_articles
from app.services.rss import fetch_and_parse_rss_feed

router = APIRouter(prefix="/articles", tags=["articles"])


@router.post("", response_model=ArticleRead, status_code=status.HTTP_201_CREATED)
async def create_article(
    payload: ArticleCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Article:
    if payload.brand_id is not None:
        brand = await session.get(Brand, payload.brand_id)

        if brand is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="brand not found",
            )

    content_hash = calculate_content_hash(payload.content)

    existing_article = await session.scalar(
        select(Article).where(Article.content_hash == content_hash)
    )

    if existing_article is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="article content already exists",
        )

    article = Article(
        brand_id=payload.brand_id,
        source_type=payload.source_type,
        source_name=payload.source_name,
        title=payload.title,
        content=payload.content,
        url=payload.url,
        content_hash=content_hash,
        published_at=payload.published_at,
    )

    session.add(article)
    await session.commit()
    await session.refresh(article)

    return article


@router.post("/import/rss", response_model=RssImportRead)
async def import_rss_articles(
    payload: RssImportRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    http_client: Annotated[AsyncClient, Depends(get_http_client)],
) -> RssImportRead:
    brand = await session.get(Brand, payload.brand_id)

    if brand is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="brand not found",
        )

    articles = await fetch_and_parse_rss_feed(
        client=http_client,
        url=str(payload.feed_url),
        source_name=payload.source_name,
        brand_id=payload.brand_id,
    )
    considered_articles = articles[: payload.max_articles]

    imported_count, skipped_count = await save_collected_articles(
        session=session,
        articles=considered_articles,
    )

    return RssImportRead(
        discovered_count=len(articles),
        considered_count=len(considered_articles),
        truncated_count=max(0, len(articles) - len(considered_articles)),
        imported_count=imported_count,
        skipped_count=skipped_count,
    )


@router.post("/{article_id}/analyze", response_model=AnalysisRead)
async def analyze_article(
    article_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    provider: Annotated[AnalysisProvider, Depends(get_analysis_provider)],
) -> AnalysisResult:
    article = await session.get(Article, article_id)

    if article is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="article not found",
        )

    return await analyze_and_save_article(
        session=session,
        provider=provider,
        article=article,
    )


@router.post(
    "/{article_id}/analyze/async",
    response_model=AnalysisJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_analysis_job(
    article_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis_client: Annotated[Redis, Depends(get_redis_client)],
) -> AnalysisJobRead:
    article = await session.get(Article, article_id)

    if article is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="article not found",
        )

    active_job_statement = (
        select(AnalysisJob)
        .where(
            AnalysisJob.article_id == article_id,
            AnalysisJob.status.in_(
                [
                    AnalysisJobStatus.QUEUED,
                    AnalysisJobStatus.PROCESSING,
                ]
            ),
        )
        .order_by(AnalysisJob.created_at.desc())
    )
    existing_job = await session.scalar(active_job_statement)

    if existing_job is not None:
        return AnalysisJobRead(
            job_id=existing_job.id,
            article_id=existing_job.article_id,
            status=existing_job.status,
            queue_length=None,
            reused=True,
        )

    job = AnalysisJob(article_id=article_id)

    session.add(job)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()

        existing_job = await session.scalar(active_job_statement)

        if existing_job is None:
            raise

        return AnalysisJobRead(
            job_id=existing_job.id,
            article_id=existing_job.article_id,
            status=existing_job.status,
            queue_length=None,
            reused=True,
        )

    await session.refresh(job)

    queue_length = await enqueue_analysis_job(
        redis_client=redis_client,
        job_id=job.id,
    )

    return AnalysisJobRead(
        job_id=job.id,
        article_id=article_id,
        status=job.status,
        queue_length=queue_length,
        reused=False,
    )


@router.get("/{article_id}/analysis", response_model=AnalysisRead)
async def get_article_analysis(
    article_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AnalysisResult:
    article = await session.get(Article, article_id)

    if article is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="article not found",
        )

    analysis = await session.scalar(
        select(AnalysisResult).where(
            AnalysisResult.article_id == article_id,
        )
    )

    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="analysis result not found",
        )

    return analysis


@router.get(
    "/{article_id}/analysis/status",
    response_model=AnalysisStatusRead,
)
async def get_article_analysis_status(
    article_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AnalysisStatusRead:
    article = await session.get(Article, article_id)

    if article is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="article not found",
        )

    analysis = await session.scalar(
        select(AnalysisResult).where(
            AnalysisResult.article_id == article_id,
        )
    )
    latest_job = await session.scalar(
        select(AnalysisJob)
        .where(AnalysisJob.article_id == article_id)
        .order_by(AnalysisJob.created_at.desc())
        .limit(1)
    )

    if analysis is not None:
        return AnalysisStatusRead(
            article_id=article_id,
            status="completed",
            job_id=latest_job.id if latest_job is not None else None,
            attempts=latest_job.attempts if latest_job is not None else 0,
            last_error=latest_job.last_error if latest_job is not None else None,
            result=AnalysisRead.model_validate(analysis),
        )

    if latest_job is not None:
        return AnalysisStatusRead(
            article_id=article_id,
            status=latest_job.status,
            job_id=latest_job.id,
            attempts=latest_job.attempts,
            last_error=latest_job.last_error,
        )

    return AnalysisStatusRead(article_id=article_id, status="not_submitted")


@router.get("", response_model=list[ArticleRead])
async def list_articles(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    brand_id: uuid.UUID | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[Article]:
    statement = select(Article)

    if brand_id is not None:
        statement = statement.where(Article.brand_id == brand_id)

    result = await session.scalars(
        statement.order_by(Article.created_at.desc()).offset(offset).limit(limit)
    )

    return list(result.all())


@router.get("/{article_id}", response_model=ArticleRead)
async def get_article(
    article_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Article:
    article = await session.get(Article, article_id)

    if article is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="article not found",
        )

    return article
