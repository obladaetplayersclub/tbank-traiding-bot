import logging
from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.dialects.postgresql import insert

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states.start import StartSurvey
from keyboards.inline import trader_kb, interval_kb, main_kb
from db.connector import engine, users

router = Router()


# 1) Определяем список тем и константу подтверждения:
TOPICS = [
    ("financial_reporting", "Финансовая отчетность"),
    ("dividends",            "Дивиденды"),
    ("ipo",                  "IPO"),
    ("m_and_a",              "M&A"),
    ("regulation",           "Регуляторика"),
    ("macro",                "Макроэкономика"),
    ("new_products",         "Новые продукты"),
    ("partnerships",         "Партнерства"),
    ("litigations",          "Судебные разбирательства"),
    ("ecology",              "События связанные с экологией"),
    ("leadership_changes",   "Изменение в составе руководителей компании"),
]
CONFIRM = "topics_confirm"


# 2) Здесь же определяем build_topics_kb:
def build_topics_kb(selected: set[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row_width = 1  # или 2, в зависимости от желаемого расположения
    for key, label in TOPICS:
        prefix = "✅ " if key in selected else ""
        builder.button(text=prefix + label, callback_data=f"topic:{key}")
    builder.button(text="🚀 Готово", callback_data=CONFIRM)
    return builder.as_markup()


# 3) И теперь уже все хэндлеры, которые на это опираются:
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
    selected = set(data.get("topics", []))
    await callback.message.edit_text(
        "Что вас интересует? Выберите несколько пунктов:",
        reply_markup=build_topics_kb(selected)
    )
    await state.set_state(StartSurvey.choosing_topics)


@router.message(StartSurvey.choosing_news_frequency)
async def process_custom_interval(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        return await message.answer("❗ Введите положительное число.")
    await state.update_data(news_interval=int(text))

    data = await state.get_data()
    selected = set(data.get("topics", []))
    await message.answer(
        "Что вас интересует? Выберите несколько пунктов:",
        reply_markup=build_topics_kb(selected)
    )
    await state.set_state(StartSurvey.choosing_topics)


@router.callback_query(lambda c: c.data.startswith("topic:"), StartSurvey.choosing_topics)
async def toggle_topic(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    selected = set(data.get("topics", []))
    key = callback.data.split(":", 1)[1]

    if key in selected:
        selected.remove(key)
    else:
        selected.add(key)

    await state.update_data(topics=list(selected))
    await callback.message.edit_reply_markup(
        reply_markup=build_topics_kb(selected)
    )


@router.callback_query(lambda c: c.data == CONFIRM, StartSurvey.choosing_topics)
async def confirm_topics(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    topics = data.get("topics", [])
    if not topics:
        return await callback.message.answer("❗ Выберите хотя бы одну тему.")

    tg_id = callback.from_user.id
    stmt = insert(users).values(
        telegram_id   = tg_id,
        trader_type   = data["trader_type"],
        news_interval = data["news_interval"],
        event_type    = topics
    )
    upsert = stmt.on_conflict_do_update(
        index_elements=[users.c.telegram_id],
        set_={
            "trader_type":   stmt.excluded.trader_type,
            "news_interval": stmt.excluded.news_interval,
            "event_type":    stmt.excluded.event_type,
        }
    )
    with engine.begin() as conn:
        conn.execute(upsert)

    await state.clear()
    await callback.message.edit_text(
        "✅ Настройки сохранены!\nГлавное меню:",
        reply_markup=main_kb
    )