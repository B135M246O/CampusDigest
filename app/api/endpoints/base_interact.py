from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

from ...core.db import get_session
from ...core.user import current_superuser
from ..jobs import delete_old_articles_job, start_parsers_job

router = APIRouter()


@router.post('/', dependencies=[Depends(current_superuser)])
async def start_parsers(
    session: AsyncSession = Depends(get_session)
):
    """Эндпоинт для ручного запуска парсеров."""
    return await start_parsers_job(session)


@router.delete('/', dependencies=[Depends(current_superuser)])
async def delete_old_articles(
    session: AsyncSession = Depends(get_session),
    days: int = Query(settings.STORAGE_DAYS, ge=0)
):
    """Эндпоинт для ручного запуска очистки БД."""
    return await delete_old_articles_job(session, days)
