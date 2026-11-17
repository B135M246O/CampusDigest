import asyncio
import os
import sys

import aioschedule as schedule
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import BASE_DIR, settings
from app.core.db import async_session_maker
from app.crud.articles import delete_old_articles_from_db, get_article_amount_from_db

SPIDERS = ['itmo_spider', 'hse_spider']


async def async_run(args, cwd=None):
    environment = dict(os.environ, SCRAPY_SETTINGS_MODULE='app.services.parse_news.settings')
    process = await asyncio.create_subprocess_exec(*args, cwd=cwd, env=environment)
    try:
        await process.communicate()
    except asyncio.CancelledError:
        if process.returncode is None:
            try:
                process.terminate()
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
        raise
    if process.returncode:
        raise RuntimeError(f'Парсер завершился с кодом {process.returncode}')


async def start_parsers_job(session: AsyncSession):
    count_before = await get_article_amount_from_db(session)
    tasks = [
        asyncio.create_task(async_run(
            [sys.executable, '-m', 'scrapy.cmdline', 'crawl', spider], cwd=BASE_DIR
        ))
        for spider in SPIDERS
    ]
    try:
        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    # PostgreSQL REPEATABLE READ не должен оставлять старый снимок после внешних записей.
    await session.commit()
    count_after = await get_article_amount_from_db(session)
    added = count_after - count_before
    logger.info('Парсеры CampusDigest завершены, добавлено {} записей.', added)
    return {'result': f'В БД успешно добавлено {added} записей.'}


async def delete_old_articles_job(session: AsyncSession, days: int = settings.STORAGE_DAYS):
    before = await get_article_amount_from_db(session)
    await delete_old_articles_from_db(session, days)
    after = await get_article_amount_from_db(session)
    return {'result': f'Из БД успешно удалено {before - after} старых статей.'}


async def run_scheduled_job(action):
    try:
        async with async_session_maker() as session:
            await action(session)
    except Exception:
        # Job.run сдвигает next_run только после успешного возврата callback.
        logger.exception('Ошибка фоновой задачи {}', action.__name__)


async def schedule_jobs():
    scheduler = schedule.Scheduler()
    scheduler.every(settings.PARSER_FREQUENCY).minutes.do(
        run_scheduled_job, start_parsers_job
    )
    scheduler.every().day.at('00:00').do(
        run_scheduled_job, delete_old_articles_job
    )
    try:
        while True:
            # aioschedule.run_pending передает корутины в asyncio.wait; Python 3.11 это запрещает.
            due = [job.run() for job in scheduler.jobs if job.should_run]
            if due:
                outcomes = await asyncio.gather(*due, return_exceptions=True)
                for result in outcomes:
                    if isinstance(result, Exception):
                        logger.error('Ошибка фоновой задачи: {}', result)
            await asyncio.sleep(1)
    finally:
        scheduler.clear()
