import asyncio
from contextlib import suppress

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.jobs import schedule_jobs
from app.api.routers import main_router
from app.bot.main import start_bot
from app.core.config import settings
from app.core.db import engine
from app.core.exceptions import ApplicationError
from app.core.init_db import create_first_superuser
from app.core.logger_config import setup_logging


def create_app() -> FastAPI:
    app = FastAPI(debug=settings.DEBUG, title=settings.APP_TITLE,
                  description=settings.APP_DESCRIPTION)
    app.include_router(main_router)

    @app.exception_handler(ApplicationError)
    async def application_error(request, error):
        return JSONResponse(status_code=getattr(error, 'status_code', 500),
                            content={'detail': error.detail})

    @app.on_event('startup')
    async def on_startup():
        setup_logging()
        app.state.bot_instance = None
        app.state.scheduler_task = None
        await create_first_superuser()
        if settings.BOT_ENABLED:
            if not settings.BOT_TOKEN or settings.BOT_TOKEN.startswith('replace-'):
                raise RuntimeError('Для BOT_ENABLED=true задайте BOT_TOKEN своего бота.')
            app.state.bot_instance = await start_bot()
        if settings.ENABLE_SCHEDULER:
            app.state.scheduler_task = asyncio.create_task(schedule_jobs())

    @app.on_event('shutdown')
    async def on_shutdown():
        task = app.state.scheduler_task
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        bot = app.state.bot_instance
        if bot:
            if bot.updater and bot.updater.running:
                await bot.updater.stop()
            await bot.stop()
            await bot.shutdown()
        await engine.dispose()

    return app
