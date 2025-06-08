from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz
from aiogram import Bot
from .trading_notifications import send_trading_start, send_trading_end
from .morning_digest import send_morning_digest

moscow_tz = pytz.timezone('Europe/Moscow')


def setup_scheduler(bot: Bot):
    scheduler = AsyncIOScheduler(timezone=moscow_tz)

    # Утренний дайджест в 9:00
    scheduler.add_job(
        send_morning_digest,
        'cron', hour=9, minute=0,
        kwargs={'bot': bot}
    )

    # Начало торгов в 10:00
    scheduler.add_job(
        send_trading_start,
        'cron', hour=10, minute=0,
        kwargs={'bot': bot}
    )

    # Окончание торгов в 19:00
    scheduler.add_job(
        send_trading_end,
        'cron', hour=19, minute=0,
        kwargs={
            'bot': bot,
            'additional_message': "📊 Торги завершены. Новости после закрытия будут включены в завтрашнюю утреннюю газету."
        }
    )

    return scheduler