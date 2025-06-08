from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

main_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="📋 Новости", callback_data="news"),
        InlineKeyboardButton(text="🔍 Фильтр", callback_data="filter"),
    ]
])

filter_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="➕ Добавить тикеры", callback_data="add_filter"),
        InlineKeyboardButton(text="👀 Показать тикеры", callback_data="view_filter"),
    ],
    [
        InlineKeyboardButton(text="❌ Удалить фильтрацию", callback_data="del_filter"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_main"),
    ]
])

back_to_filter_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔙 Отмена", callback_data="back_filter")]
])

trader_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📈 Краткосрочный", callback_data="short")],
    [InlineKeyboardButton(text="📉 Среднесрочный", callback_data="medium")],
    [InlineKeyboardButton(text="🏦 Долгосрочный", callback_data="long")]
])

interval_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="15 минут", callback_data="15")],
    [InlineKeyboardButton(text="30 минут", callback_data="30")],
    [InlineKeyboardButton(text="60 минут", callback_data="60")]
])

