import re
import spacy
from rapidfuzz import process

# Загрузите модель командой:
# python -m spacy download ru_core_news_sm
nlp = spacy.load("ru_core_news_sm")

def detect_tickers(
    text: str,
    ticker_lookup: dict[str, str],
    ticker_list: list[str],
    fuzzy_threshold: int = 90
) -> list[str]:
    """
    Извлекает тикеры из текста с помощью трёх стратегий:
    1) Простое вхождение по названиям компаний из ticker_lookup
    2) NER (spaCy) + фаззи-маппинг найденных ORG-сущностей
    3) Прямой поиск по латинским кодам тикеров из ticker_list

    Параметры:
      text              — входная строка новости
      ticker_lookup     — словарь {название_компании: код_тикера}
      ticker_list       — список всех кодов тикеров для прямого поиска
      fuzzy_threshold   — порог схожести (0–100) для фаззи-матчинга

    Возвращает:
      список уникальных кодов тикеров, найденных в тексте
    """
    found = set()  # множество, чтобы избежать дубликатов
    lower_text = text.lower()

    # 1) Простое вхождение по ключевым названиям компаний
    for name, ticker in ticker_lookup.items():
        pattern = rf"\b{re.escape(name)}\b"
        if re.search(pattern, lower_text):
            found.add(ticker)

    # 2) NER + фаззи-маппинг по ORG-сущностям
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ == "ORG":
            org_name = ent.text.lower().strip()
            match, score, _ = process.extractOne(org_name, list(ticker_lookup.keys()))
            if score >= fuzzy_threshold:
                found.add(ticker_lookup[match])

    # 3) Прямой поиск по кодам тикеров (латиница)
    for ticker in ticker_list:
        pattern = rf"\b{re.escape(ticker)}\b"
        if re.search(pattern, text, flags=re.IGNORECASE):
            found.add(ticker)

    return list(found)
