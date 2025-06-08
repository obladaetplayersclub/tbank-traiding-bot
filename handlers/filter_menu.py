import logging

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from states.filters import FilterStates
from keyboards.inline import filter_kb, back_to_filter_kb, main_kb
from db.connector import get_db_connection
from utils.ticker_map import ticker_lookup

router = Router()


@router.callback_query(F.data == "filter")
async def open_filter_menu(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer("Меню фильтрации:", reply_markup=filter_kb)


@router.callback_query(F.data == "add_filter")
async def add_filter(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(FilterStates.waiting_for_tickers)
    await callback.message.answer(
        "Введите тикер(ы) через запятую:",
        reply_markup=back_to_filter_kb
    )


@router.message(FilterStates.waiting_for_tickers)
async def process_tickers(message: types.Message, state: FSMContext):
    tg_id = message.from_user.id
    input_tickers = [t.strip().lower() for t in message.text.split(",")]

    valid = []
    for t in input_tickers:
        code = ticker_lookup.get(t)
        if code:
            valid.append(code)
        elif t.upper() in ticker_lookup.values():
            valid.append(t.upper())

    if not valid:
        await state.clear()
        return await message.answer("❌ Не найдено валидных тикеров", reply_markup=filter_kb)

    conn = get_db_connection()
    with conn:
        with conn.cursor() as cur:
            logging.info(f"Сохраняем фильтр {valid} для {tg_id}")
            cur.execute(
                """
                INSERT INTO users (telegram_id, filter)
                VALUES (%s, %s)
                ON CONFLICT (telegram_id) DO UPDATE
                  SET filter = EXCLUDED.filter
                """,
                (tg_id, valid)
            )

    await state.clear()
    await message.answer(
        f"✅ Фильтр обновлён:\n{', '.join(valid)}",
        reply_markup=filter_kb
    )


@router.callback_query(F.data == "view_filter")
async def view_filter(callback: types.CallbackQuery):
    await callback.answer()
    tg_id = callback.from_user.id

    conn = get_db_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT filter FROM users WHERE telegram_id = %s", (tg_id,))
            row = cur.fetchone()

    if not (row and row[0]):
        text = "<i>Фильтр не задан.</i>"
    else:
        raw = row[0]
        if isinstance(raw, str):
            items = [t.strip() for t in raw.strip("{}").split(",") if t.strip()]
        else:
            items = raw
        text = "<b>Ваш текущий фильтр:</b>\n" + "\n".join(f"• {t}" for t in items)

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=filter_kb
    )


@router.callback_query(F.data == "del_filter")
async def delete_filter(callback: types.CallbackQuery):
    await callback.answer()
    tg_id = callback.from_user.id

    conn = get_db_connection()
    with conn:
        with conn.cursor() as cur:
            logging.info(f"Очищаем фильтр для {tg_id}")
            cur.execute(
                "UPDATE users SET filter = ARRAY[]::text[] WHERE telegram_id = %s",
                (tg_id,)
            )

    await callback.message.answer(
        "✅ Фильтр очищен.",
        reply_markup=filter_kb
    )


@router.callback_query(F.data == "back_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.answer("Главное меню:", reply_markup=main_kb)


@router.callback_query(F.data == "back_filter")
async def back_to_filter(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.answer("Меню фильтрации:", reply_markup=filter_kb)