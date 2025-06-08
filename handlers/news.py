from aiogram import Router, types, F
from db.connector import get_db_connection
from keyboards.inline import main_kb

router = Router()

@router.callback_query(F.data == "news")
async def handle_news(callback: types.CallbackQuery):
    await callback.answer()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Берём, например, 10 самых свежих новостей
            cur.execute("""
                SELECT title, content, published_time
                FROM news
                ORDER BY published_time DESC
                LIMIT 10
            """)
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        return await callback.message.answer(
            "Пока новостей нет 😔", reply_markup=main_kb
        )

    for title, summary, published_at in rows:
        # Форматируем дату
        ts = published_at.strftime("%d.%m.%Y %H:%M")
        # Составляем Markdown-сообщение
        text = (
            f"*{title}*\n"
            f"_{ts}_\n\n"
            f"{summary}\n\n"
        )
        await callback.message.answer(text, parse_mode="Markdown")

    await callback.message.answer("Это все новости.", reply_markup=main_kb)