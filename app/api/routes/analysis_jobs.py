import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.analysis_job import AnalysisJob
from app.schemas.analysis import AnalysisJobStatusRead

router = APIRouter(
    prefix="/analysis-jobs",
    tags=["analysis-jobs"],
)


@router.get("/{job_id}", response_model=AnalysisJobStatusRead)
async def get_analysis_job(
    job_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AnalysisJobStatusRead:
    job = await session.get(AnalysisJob, job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="analysis job not found",
        )

    return AnalysisJobStatusRead(
        job_id=job.id,
        article_id=job.article_id,
        status=job.status,
        attempts=job.attempts,
        last_error=job.last_error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
