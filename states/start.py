from aiogram.fsm.state import StatesGroup, State

class StartSurvey(StatesGroup):
    choosing_trader_type     = State()
    choosing_news_frequency  = State()
    choosing_topics          = State()