import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from db.connector import engine, metadata                             # ← импортируем

from handlers.start import router as start_router
from handlers.news import router as news_router
from handlers.filter_menu import router as filter_router

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# регистрируем роутеры
dp.include_router(start_router)
dp.include_router(news_router)
dp.include_router(filter_router)

async def main():
    # создаём таблицы при старте
    metadata.create_all(engine)                                               # ← вызываем
    logging.info("✅ Таблицы в БД проверены и созданы, запускаю бота…")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())