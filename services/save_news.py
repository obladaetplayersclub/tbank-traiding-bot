from db.connector import engine, news
def fetch_news(whereclause=None, limit=10):
    with engine.connect() as conn:
        query = news.select()
        if whereclause is not None:
            query = query.where(whereclause)
        query = query.order_by(news.c.published_time.desc()).limit(limit)
        result = conn.execute(query)
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]
