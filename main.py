import asyncio

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import (
    RENDER_EXTERNAL_URL,
    TOKEN_API,
    WEBHOOK_PATH,
    WEBHOOK_SECRET,
    WEB_SERVER_HOST,
    WEB_SERVER_PORT,
)
from data.database import Database
from menu import base_model


dp = Dispatcher(storage=MemoryStorage())
db = Database()


def configure_dispatcher() -> None:
    if not dp.sub_routers:
        dp.include_router(base_model.router)


async def healthcheck(_: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def aiohttp_on_startup(app: web.Application) -> None:
    await on_startup(app["bot"])


async def aiohttp_on_shutdown(app: web.Application) -> None:
    await on_shutdown(app["bot"])


async def on_startup(bot: Bot) -> None:
    await db.create_db()
    configure_dispatcher()

    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}"
        await bot.set_webhook(webhook_url, secret_token=WEBHOOK_SECRET or None)
    else:
        await bot.delete_webhook(drop_pending_updates=True)


async def on_shutdown(bot: Bot) -> None:
    if RENDER_EXTERNAL_URL:
        await bot.delete_webhook()
    await bot.session.close()


async def run_polling() -> None:
    bot = Bot(TOKEN_API)
    await on_startup(bot)
    try:
        await dp.start_polling(bot)
    finally:
        await on_shutdown(bot)


def run_webhook() -> None:
    bot = Bot(TOKEN_API)
    app = web.Application()
    app["bot"] = bot

    app.router.add_get("/", healthcheck)
    app.router.add_get("/healthz", healthcheck)

    handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET or None,
    )
    handler.register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)
    app.on_startup.append(aiohttp_on_startup)
    app.on_shutdown.append(aiohttp_on_shutdown)

    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)


def main() -> None:
    if not TOKEN_API:
        raise RuntimeError("TOKEN_API is not set. Add it to .env before launch.")

    if RENDER_EXTERNAL_URL:
        run_webhook()
        return

    asyncio.run(run_polling())


if __name__ == "__main__":
    main()
