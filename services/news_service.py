
from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy.dialects.postgresql import insert

from db.connector import engine, news


def save_news(data: Dict[str, Any]) -> int:
    if "title" not in data or "published_time" not in data:
        raise ValueError("title и published_time обязательны")

    stmt = (
        insert(news)
        .values(**data)
        .returning(news.c.news_id)
    )

    with engine.begin() as conn:
        result = conn.execute(stmt)
        return result.scalar_one()

if __name__ == "__main__":
    new_id = save_news(
        {
            "title": "Tesla объявила о сплите акций 3-к-1",
            "published_time": datetime.utcnow(),
            "content": "…текст новости…",
            "source": "Reuters",
            "sentiment": 0.4,
            "tickers": ["TSLA"],
            "event_type": 1,
        }
    )
    print("Новость сохранена, ID =", new_id)