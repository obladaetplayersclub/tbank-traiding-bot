from datetime import datetime
from typing import Dict, Any

from sqlalchemy.dialects.postgresql import insert

from db.connector import engine, news


def save_news(data: Dict[str, Any]) -> int:
    required_fields = ["text", "published_time", "ticker", "polarity", "intensity", "minhash", "embedding"]

    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise ValueError(f"Обязательные поля отсутствуют: {', '.join(missing_fields)}")

    stmt = (
        insert(news)
        .values(**data)
        .returning(news.c.id)
    )

    with engine.begin() as conn:
        result = conn.execute(stmt)
        return result.scalar_one()