import os
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

#from handlers import router - в этот модуль добавить эхо-локатор работает-лежит
from scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    logger.error("BOT_TOKEN не найден в .env или переменных окружения!")
    raise ValueError("Токен бота обязателен")

async def on_startup(bot: Bot):
    logger.info("Бот запущен")
    asyncio.create_task(start_scheduler(bot))

async def on_shutdown():
    logger.warning("Бот останавливается...")

async def main():
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    #dp.include_router(router) - в этот модуль добавить эхо-локатор работает-лежит
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
