import asyncio
import sys
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from scrapy.http import HtmlResponse

import app.application as application
from app.api import jobs
from app.core.config import Settings, settings
from app.core.db import get_session
from app.crud.articles import add_article_to_db, mark_articles_as_read
from app.models import Article, ArticleUser, UserModel
from app.schemas.articles import Article as ArticleSchema
from app.services.parse_news import pipelines
from app.services.parse_news.spiders.itmo import ItmoSpider


async def make_article(session, name, source='ИТМО', category='Наука', days=0):
    return await add_article_to_db(session, {
        'title': name, 'source': source, 'category': category,
        'date': datetime.now(timezone.utc) - timedelta(days=days),
        'overview': 'Публичная новость университета', 'text': 'Текст новости',
        'link': f'https://university.example.com/news/{name}',
        'picture_link': None, 'video_link': None, 'video_preview_link': None,
        'authors': ['Пресс-служба'], 'infographic_links': [],
    })


def make_app(session):
    api = application.create_app()

    async def override_session():
        yield session

    api.dependency_overrides[get_session] = override_session
    return api


async def register_and_login(client, email, limit=5):
    response = await client.post('/auth/register', json={
        'email': email, 'password': 'campus-test-password', 'article_limit': limit,
    })
    assert response.status_code == 201, response.text
    login = await client.post('/auth/jwt/login', data={
        'username': email, 'password': 'campus-test-password',
    })
    assert login.status_code == 200, login.text
    return {'Authorization': 'Bearer ' + login.json()['access_token']}


async def test_registration_filters_read_history_and_permissions(db_session):
    wanted = await make_article(db_session, 'science-itmo')
    await make_article(db_session, 'science-hse', source='НИУ ВШЭ')
    await make_article(db_session, 'campus-itmo', category='Кампус')
    async with httpx.AsyncClient(app=make_app(db_session), base_url='http://test') as client:
        assert (await client.get('/articles/')).status_code == 401
        first = await register_and_login(client, 'first@example.com', limit=1)
        second = await register_and_login(client, 'second@example.com')
        params = {'source': 'ИТМО', 'category_filter': 'Наука'}
        response = await client.get('/articles/', params=params, headers=first)
        assert response.status_code == 200, response.text
        assert [item['id'] for item in response.json()] == [wanted.id]
        assert 'T' in response.json()[0]['date']
        assert (await client.get('/articles/', params=params, headers=first)).json() == []
        response = await client.get('/articles/', params=params, headers=second)
        assert [item['id'] for item in response.json()] == [wanted.id]
        assert (await client.get('/users/all', headers=first)).status_code == 403
        assert (await client.get('/articles/count', headers=first)).status_code == 403
        assert (await client.post('/db_interact/', headers=first)).status_code == 403
        assert (await client.get('/articles/', params={'source': 'РБК'}, headers=first)).status_code == 422


async def test_limit_order_html_and_retention_parameter(db_session):
    old = await make_article(db_session, 'old', days=90)
    recent = await make_article(db_session, 'recent', days=30)
    async with httpx.AsyncClient(app=make_app(db_session), base_url='http://test') as client:
        admin_headers = await register_and_login(client, 'admin@example.com', limit=1)
        admin = await db_session.scalar(select(UserModel).where(UserModel.email == 'admin@example.com'))
        admin.is_superuser = True
        await db_session.commit()
        page = await client.get(f'/articles/html/{recent.id}')
        assert page.status_code == 200 and recent.title in page.text
        response = await client.get('/articles/', headers=admin_headers)
        assert [row['id'] for row in response.json()] == [recent.id]
        assert (await client.delete('/db_interact/', params={'days': -1}, headers=admin_headers)).status_code == 422
        response = await client.delete('/db_interact/', params={'days': 60}, headers=admin_headers)
        assert response.status_code == 200, response.text
        assert '1 старых' in response.json()['result']
        remaining = (await db_session.scalars(select(Article.id))).all()
        assert remaining == [recent.id]
        count = await client.get('/articles/count', headers=admin_headers)
        assert count.json() == {'article_amount': 1}


async def test_read_mark_unique_per_user_article(db_session):
    article = await make_article(db_session, 'unique-mark')
    user = UserModel(email='reader@example.com', hashed_password='unused', article_limit=5,
                     is_active=True, is_superuser=False, is_verified=False)
    db_session.add(user)
    await db_session.commit()
    await mark_articles_as_read(user, [article], db_session)
    db_session.add(ArticleUser(user_id=user.id, article_id=article.id))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


def test_date_keeps_timezone_and_instant():
    instant = datetime(2026, 11, 17, 12, 30, tzinfo=timezone(timedelta(hours=3)))
    item = ArticleSchema(id=1, source='ИТМО', date=instant, category='Наука', title='Новости',
                         link='https://university.example.com/news/1')
    assert item.date == instant
    assert item.date.hour == 12
    assert '+03:00' in item.json()


def test_api_only_startup_and_shutdown(monkeypatch):
    monkeypatch.setattr(settings, 'BOT_ENABLED', False)
    monkeypatch.setattr(settings, 'ENABLE_SCHEDULER', False)
    create_admin = AsyncMock()
    start_bot = AsyncMock()
    monkeypatch.setattr(application, 'create_first_superuser', create_admin)
    monkeypatch.setattr(application, 'start_bot', start_bot)
    with TestClient(application.create_app()) as client:
        assert client.get('/openapi.json').json()['info']['title'] == 'CampusDigest'
        assert client.app.state.bot_instance is None
        assert client.app.state.scheduler_task is None
    create_admin.assert_awaited_once()
    start_bot.assert_not_awaited()


async def test_parser_process_failure_is_reported(monkeypatch):
    process = SimpleNamespace(communicate=AsyncMock(), returncode=2)
    spawn = AsyncMock(return_value=process)
    monkeypatch.setattr(asyncio, 'create_subprocess_exec', spawn)
    with pytest.raises(RuntimeError, match='кодом 2'):
        await jobs.async_run(['python', '-m', 'scrapy'], cwd='.')
    assert spawn.call_args.kwargs['env']['SCRAPY_SETTINGS_MODULE'] == 'app.services.parse_news.settings'


def test_database_password_is_url_encoded():
    config = Settings(_env_file=None, DATABASE_URL=None, POSTGRES_PASSWORD='a@b:/?#%')
    from sqlalchemy.engine import make_url
    assert make_url(config.database_url).password == 'a@b:/?#%'


async def test_saved_article_through_pipeline_database_api_and_read_mark(db_session, monkeypatch):
    response = HtmlResponse(
        'https://news.itmo.ru/ru/it/science/news/15078',
        body=(Path(__file__).parent / 'fixtures/itmo_article.html').read_bytes(),
        encoding='utf-8',
    )
    spider = ItmoSpider()
    item, = spider.parse_article(response)
    monkeypatch.setattr(pipelines, 'engine', db_session.bind)
    pipeline = pipelines.ArticlesToDBPipeline()
    pipeline.open_spider(spider)
    await pipeline.process_item(item, spider)
    await pipeline.process_item(item, spider)
    rows = (await db_session.scalars(select(Article))).all()
    assert len(rows) == 1
    async with httpx.AsyncClient(app=make_app(db_session), base_url='http://test') as client:
        headers = await register_and_login(client, 'pipeline-reader@example.com')
        params = {'source': 'ИТМО', 'category_filter': 'Наука'}
        result = await client.get('/articles/', params=params, headers=headers)
        assert result.status_code == 200
        article, = result.json()
        assert article['title'] == item['title']
        assert article['text'] == item['text']
        assert article['authors'][0]['author_name'] == item['authors'][0]
        assert (await client.get('/articles/', params=params, headers=headers)).json() == []


async def test_cancelled_parser_terminates_child_process(monkeypatch):
    original_spawn = asyncio.create_subprocess_exec
    started = asyncio.Event()
    child = None

    async def spawn(*args, **kwargs):
        nonlocal child
        child = await original_spawn(*args, **kwargs)
        started.set()
        return child

    monkeypatch.setattr(asyncio, 'create_subprocess_exec', spawn)
    task = asyncio.create_task(jobs.async_run(
        [sys.executable, '-c', 'import time; time.sleep(60)']
    ))
    try:
        await asyncio.wait_for(started.wait(), timeout=10)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert child.returncode is not None
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        if child and child.returncode is None:
            child.kill()
            await child.wait()


async def test_failed_scheduled_job_waits_for_next_interval(monkeypatch):
    scheduler = jobs.schedule.Scheduler()
    monkeypatch.setattr(jobs.schedule, 'Scheduler', lambda: scheduler)

    @asynccontextmanager
    async def session():
        yield object()

    failures = []

    async def fail(session):
        failures.append(datetime.now())
        raise RuntimeError('source unavailable')

    monkeypatch.setattr(jobs, 'async_session_maker', session)
    monkeypatch.setattr(jobs, 'start_parsers_job', fail)
    task = asyncio.create_task(jobs.schedule_jobs())
    try:
        await asyncio.sleep(0)
        parser_job = scheduler.jobs[0]
        parser_job.next_run = datetime.now() - timedelta(seconds=1)
        await asyncio.sleep(1.1)
        assert len(failures) == 1
        assert parser_job.next_run > datetime.now() + timedelta(minutes=settings.PARSER_FREQUENCY - 1)
        await asyncio.sleep(1.1)
        assert len(failures) == 1
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


async def test_one_parser_failure_stops_other_parser(monkeypatch):
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def run(args, cwd):
        if args[-1] == 'itmo_spider':
            await started.wait()
            raise RuntimeError('parser failed')
        started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.set()
            raise

    monkeypatch.setattr(jobs, 'async_run', run)
    monkeypatch.setattr(jobs, 'get_article_amount_from_db', AsyncMock(return_value=0))
    with pytest.raises(RuntimeError, match='parser failed'):
        await jobs.start_parsers_job(object())
    assert cancelled.is_set()
