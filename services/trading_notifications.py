from aiogram import Bot
from db.connector import get_db_connection


async def send_trading_start(bot: Bot):
    """Уведомление о начале торгов"""
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT telegram_id FROM users")
                for (tg_id,) in cur.fetchall():
                    await bot.send_message(
                        chat_id=tg_id,
                        text="🔔 *Торги начались!*\n\nСейчас будем присылать *для вас* самые важные и актуальные новости.",
                        parse_mode="Markdown"
                    )
    finally:
        conn.close()


async def send_trading_end(bot: Bot, additional_message: str = None):
    """Уведомление о завершении торгов"""
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT telegram_id FROM users")
                for (tg_id,) in cur.fetchall():
                    message = "🔕 *Торги завершены*"
                    if additional_message:
                        message += f"\n\n{additional_message}"

                    await bot.send_message(
                        chat_id=tg_id,
                        text=message,
                        parse_mode="Markdown"
                    )
    finally:
        conn.close()