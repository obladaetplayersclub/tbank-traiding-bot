from aiogram import Bot
from db.connector import get_db_connection

async def send_morning_digest(bot: Bot):
    """Собирает последние новости и отправляет одним сообщением"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT telegram_id, filter FROM users")
            users = cur.fetchall()

            for tg_id, tickers in users:
                # Если у пользователя указаны тикеры — фильтруем по ним, иначе берём все
                if tickers:
                    query = (
                        """
                        SELECT text
                        FROM news
                        WHERE ticker && %s
                        ORDER BY id DESC
                        LIMIT 20
                        """
                    )
                    params = (tickers,)
                else:
                    query = (
                        """
                        SELECT text
                        FROM news
                        ORDER BY id DESC
                        LIMIT 20
                        """
                    )
                    params = None

                # Выполняем запрос
                if params:
                    cur.execute(query, params)
                else:
                    cur.execute(query)

                rows = cur.fetchall()
                if not rows:
                    continue

                # Формируем и отправляем дайджест в хронологическом порядке
                digest_lines = [f"📰 {text}" for (text,) in rows]
                digest = "\n".join(reversed(digest_lines))
                await bot.send_message(
                    chat_id=tg_id,
                    text=f"🌅 *Утренний дайджест*\n\n{digest}",
                    parse_mode="Markdown"
                )
    finally:
        conn.close()
