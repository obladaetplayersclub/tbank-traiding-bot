import asyncio
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from db.connector import get_db_connection


async def process_user_news(bot: Bot, tg_id, tickers, limit):
    """Отправляет свежие новости одному пользователю"""
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, text, content
                    FROM news
                    WHERE tickers && %s AND NOT %s = ANY(users)
                    ORDER BY published_time
                    LIMIT %s
                """, (tickers, tg_id, limit))

                for news_id, title, content in cur.fetchall():
                    try:
                        await bot.send_message(
                            chat_id=tg_id,
                            text=f"📢 *{title}*\n\n{content}",
                            parse_mode="Markdown"
                        )
                        cur.execute("""
                            UPDATE news 
                            SET users = array_append(users, %s)
                            WHERE news_id = %s
                        """, (tg_id, news_id))
                    except TelegramBadRequest:
                        continue
    finally:
        conn.close()


async def news_dispatcher_task(bot: Bot):
    """Основной цикл рассылки новостей"""
    while True:
        conn = get_db_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT telegram_id, filter, noise_tolerance
                        FROM users
                    """)
                    for tg_id, tickers, limit in cur.fetchall():
                        if tickers:
                            await process_user_news(bot, tg_id, tickers, limit)
        finally:
            conn.close()
        await asyncio.sleep(60)