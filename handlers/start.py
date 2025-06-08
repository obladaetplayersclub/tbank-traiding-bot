import logging
from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.dialects.postgresql import insert

from keyboards.inline import trader_kb, interval_kb, main_kb
from db.connector import engine, users
from states.start import StartSurvey

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Добро пожаловать!\nКакой вы трейдер?",
        reply_markup=trader_kb
    )
    await state.set_state(StartSurvey.choosing_trader_type)


@router.callback_query(StartSurvey.choosing_trader_type)
async def process_trader_type(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(trader_type=callback.data)
    await callback.message.edit_text(
        "Как часто (в минутах) вы хотите получать новости?",
        reply_markup=interval_kb
    )
    await state.set_state(StartSurvey.choosing_news_frequency)


@router.callback_query(StartSurvey.choosing_news_frequency)
async def process_news_frequency(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    interval = int(callback.data)
    await state.update_data(news_interval=interval)

    data = await state.get_data()

    tg_id = callback.from_user.id
    stmt = insert(users).values(
        telegram_id=tg_id,
        trader_type=data["trader_type"],
        news_interval=data["news_interval"]
    )
    upsert = stmt.on_conflict_do_update(
        index_elements=[users.c.telegram_id],
        set_={
            "trader_type": stmt.excluded.trader_type,
            "news_interval": stmt.excluded.news_interval,
        }
    )
    with engine.begin() as conn:
        conn.execute(upsert)

    await state.clear()
    await callback.message.edit_text(
        "✅ Настройки сохранены!\nГлавное меню:",
        reply_markup=main_kb
    )


@router.message(StartSurvey.choosing_news_frequency)
async def process_custom_interval(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        return await message.answer("❗ Введите положительное число.")

    await state.update_data(news_interval=int(text))
    data = await state.get_data()

    tg_id = message.from_user.id
    stmt = insert(users).values(
        telegram_id=tg_id,
        trader_type=data["trader_type"],
        news_interval=data["news_interval"]
    )
    upsert = stmt.on_conflict_do_update(
        index_elements=[users.c.telegram_id],
        set_={
            "trader_type": stmt.excluded.trader_type,
            "news_interval": stmt.excluded.news_interval,
        }
    )
    with engine.begin() as conn:
        conn.execute(upsert)

    await state.clear()
    await message.answer(
        "✅ Настройки сохранены!\nГлавное меню:",
        reply_markup=main_kb
    )