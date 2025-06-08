import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from db.connector import engine, metadata
import dbnews
import parsing.pars_finam
import parsing.pars_rbc
import parsing.pars_rss
import data_refactor

from handlers.start        import router as start_router
from handlers.news         import router as news_router
from handlers.filter_menu  import router as filter_router

from utils.ticker_map import ticker_lookup
ticker_list = list(ticker_lookup.values())

db_config = {
    "dbname":   "postgres",
    "user":     "_enter_",
    "password": "1234",
    "host":     "localhost",
    "port":     5432,
}

DELAY = 60  # секунда

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())

# Регистрируем роутеры
dp.include_router(start_router)
dp.include_router(news_router)
dp.include_router(filter_router)

async def parser_loop(checker: dbnews.DBNewsDeduplicator):
    """Фоновый цикл сбора и добавления новостей"""
    while True:
        try:
            articles = parsing.pars_finam.collect_set()
            print(len(articles))
            articles.update(parsing.pars_rbc.collect_set())
            print(len(articles))
            articles.update(parsing.pars_rss.collect_set())
            print(len(articles))
            data_refactor.add_news(checker, articles, ticker_lookup, ticker_list)
            data_refactor.print_news(checker)
            logging.info("Новости обновлены")
        except Exception as err:
            logging.error(f"Ошибка парсинга: {err}")
        await asyncio.sleep(DELAY)

async def main():
    # 1) Создаём таблицы
    metadata.create_all(engine)
    logging.info("✅ Таблицы проверены и созданы")

    # 2) Инициализируем дедупликатор
    checker = dbnews.DBNewsDeduplicator(db_config)
    logging.info("DBChecker инициализирован")

    # 3) Запускаем фон-задачу парсинга
    asyncio.create_task(parser_loop(checker))

    # 4) Запускаем бота
    logging.info("Запускаю бота…")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())