import csv
import os
from db.connector import get_db_connection

# Пути к вашим CSV:
CSV_FILES = [
    os.path.join(os.path.dirname(__file__), '..', 'data', 'tickers1.csv'),
    os.path.join(os.path.dirname(__file__), '..', 'data', 'tickers2.csv'),
]

def load_tickers(csv_paths):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            for path in csv_paths:
                with open(path, encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Предполагаем, что в CSV колонки называются "name" и "symbol"
                        name   = row.get('name')   or row.get('Название')  # поправьте на реальные заголовки
                        symbol = row.get('symbol') or row.get('Тикер')
                        if not name or not symbol:
                            continue
                        cur.execute(
                            """
                            INSERT INTO tickers (name, symbol)
                            VALUES (%s, %s)
                            ON CONFLICT (symbol) DO NOTHING
                            """,
                            (name.strip(), symbol.strip())
                        )
            conn.commit()
    finally:
        conn.close()
