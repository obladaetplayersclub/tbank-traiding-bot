import asyncio
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from db.connector import get_db_connection

async def process_user_news(bot: Bot, tg_id, tickers, limit):
    """Отправляет свежие новости одному пользователю"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if tickers:
                # выборка по указанным тикерам
                cur.execute(
                    """
                    SELECT id, text
                    FROM news
                    WHERE ticker && %s
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (tickers, limit)
                )
            else:
                # если тикеры не заданы — берём все
                cur.execute(
                    """
                    SELECT id, text
                    FROM news
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (limit,)
                )

            for news_id, text in cur.fetchall():
                try:
                    await bot.send_message(
                        chat_id=tg_id,
                        text=f"📢 {text}"
                    )
                except TelegramBadRequest:
                    continue
    finally:
        conn.close()


async def news_dispatcher_task(bot: Bot):
    """Основной цикл рассылки новостей"""
    while True:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT telegram_id, filter, noise_tolerance FROM users"
                )
                for tg_id, tickers, limit in cur.fetchall():
                    await process_user_news(bot, tg_id, tickers, limit)
        finally:
            conn.close()
        await asyncio.sleep(60)
