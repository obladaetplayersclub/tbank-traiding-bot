from aiogram import Router, types, F
from db.connector import get_db_connection
from keyboards.inline import main_kb

router = Router()

@router.callback_query(F.data == "news")
async def handle_news(callback: types.CallbackQuery):
    await callback.answer()
    tg_id = callback.from_user.id

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 1) Читаем массив фильтра (TEXT[])
            cur.execute(
                "SELECT filter FROM users WHERE telegram_id = %s",
                (tg_id,)
            )
            row = cur.fetchone()
            tickers = row[0] or []  # если NULL — получим []

            # 2) Если пользователь указал тикеры — проверяем equality ANY(),
            #    иначе — отдаем все новости
            if tickers:
                cur.execute(
                    """
                    SELECT text
                    FROM news
                    WHERE ticker = ANY(%s)
                    ORDER BY id DESC
                    LIMIT 10
                    """,
                    (tickers,)
                )
            else:
                cur.execute(
                    """
                    SELECT text
                    FROM news
                    ORDER BY id DESC
                    LIMIT 10
                    """
                )
            rows = cur.fetchall()
    finally:
        conn.close()

    # 3) Отправляем ответы
    if not rows:
        await callback.message.answer(
            "Пока новостей нет 😔",
            reply_markup=main_kb
        )
        return

    for (text,) in rows:
        await callback.message.answer(text)

    await callback.message.answer(
        "Это все новости.",
        reply_markup=main_kb
    )