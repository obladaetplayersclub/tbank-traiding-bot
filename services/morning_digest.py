from aiogram import Bot
from db.connector import get_db_connection
from datetime import datetime, timedelta


async def send_morning_digest(bot: Bot):
    """Собирает все ночные новости и отправляет одним сообщением"""
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT telegram_id, filter FROM users")
                users = cur.fetchall()

                for tg_id, tickers in users:
                    if not tickers:
                        continue

                    # Новости с 19:00 вчера до 9:00 сегодня
                    now = datetime.now()
                    yesterday_evening = now - timedelta(days=1, hours=now.hour - 19)

                    cur.execute("""
                        SELECT title, content 
                        FROM news
                        WHERE tickers && %s
                        AND published_time BETWEEN %s AND %s
                        ORDER BY published_time
                    """, (tickers, yesterday_evening, now))

                    digest = "\n".join(
                        f"📰 *{title}*\n{content}"
                        for title, content in cur.fetchall()
                    )

                    if digest:
                        await bot.send_message(
                            chat_id=tg_id,
                            text=f"🌅 *Утренний дайджест*\n\n{digest}",
                            parse_mode="Markdown"
                        )
    finally:
        conn.close()