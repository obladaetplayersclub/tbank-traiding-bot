import json, time, urllib.parse, requests
from json import JSONDecodeError
from pathlib import Path
from typing import Iterable, Iterator
from datetime import datetime
from bs4 import BeautifulSoup
import re

BASE_URL = "https://quote.rbc.ru"
DELAY = 60
JSON_FILE = Path("news_rbc.json")
HEADERS = {"User-Agent": "Mozilla/5.0 (headline-bot/1.0)"}
HEADLINE_SEL = "span.q-item__title.js-rm-central-column-item-text"
TIME_SELECTORS  = ("time", "span.article__data-time", "span.article__header__date")
RU2NUM = {
    "янв": 1, "фев": 2, "мар": 3, "апр": 4, "май": 5, "июн": 6,
    "июл": 7, "авг": 8, "сен": 9, "окт": 10, "ноя": 11, "дек": 12
}
ENG_MONTH = [  # 1→January, 2→February, …
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

def req(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status();  return r.text

def iter_headline_links(html: str) -> Iterator[tuple[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    for a in soup.select(f"a:has({HEADLINE_SEL})"):
        span = a.select_one(HEADLINE_SEL)
        if span and "href" in a.attrs:
            yield span.get_text(strip=True), urllib.parse.urljoin(BASE_URL, a["href"])

def normalize_time(text: str) -> str:
    m = re.match(r"\s*(\d{1,2})\s+([а-я]{3})\s*(\d{4})?,\s*(\d{2}:\d{2})", text, re.I)
    if not m:
        return text.strip()
    day, ru_mon, year, hm = m.groups()
    year = int(year) if year else datetime.now().year
    month_num = RU2NUM.get(ru_mon.lower())
    if not month_num:
        return text.strip()
    month_eng = ENG_MONTH[month_num]
    return f"{int(day):02d} {month_eng}, {hm}"

def parse_article(url: str) -> tuple[str, str]:
    soup = BeautifulSoup(req(url), "lxml")
    raw_time = next(
        (t.get_text(strip=True) for sel in TIME_SELECTORS
         if (t := soup.select_one(sel))),
        "")
    pub_time = normalize_time(raw_time) if raw_time else "[time unknown]"
    body = soup.select_one("div.article__text")
    if body:
        text = body.get_text(" ", strip=True).replace("\u00A0", " ")
    else:
        text = "\n".join(p.get_text(" ", strip=True) for p in soup.find_all("p")).strip()
    return pub_time, text

def plural(n: int) -> str:
    return ("новость"  if n % 10 == 1 and n % 100 != 11 else
            "новости" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else
            "новостей")

all_articles: list[dict] = []
seen_urls: set[str] = set()
if JSON_FILE.exists() and JSON_FILE.stat().st_size:          # файл есть и не пустой
    try:
        with JSON_FILE.open(encoding="utf-8") as f:
            all_articles = json.load(f)
            seen_urls   = {art["url"] for art in all_articles}
    except JSONDecodeError:
        print("news_rbc.json повреждён — начинаю с пустого списка.")
else:
    print("Файла news_rbc.json нет или он пуст — старт с чистого листа.")


while True:
    try:
        html = req(BASE_URL)
        new_count = 0
        for headline, url in iter_headline_links(html):
            if url in seen_urls:
                continue
            pub_time, text = parse_article(url)
            all_articles.append({
                "title": headline,
                "date": pub_time or "[время неизвестно]",
                "url": url,
                "text":  text
            })
            seen_urls.add(url);  new_count += 1
        print(f"[{time.strftime('%H:%M:%S')}] добавлено {new_count} {plural(new_count)}")
        if new_count:
            with JSON_FILE.open("w", encoding="utf-8") as f:
                json.dump(all_articles, f, ensure_ascii=False, indent=2)
            print(f"[{time.strftime('%H:%M:%S')}] {JSON_FILE.name} сохранён: статей {len(all_articles)}")

    except KeyboardInterrupt:
        print("\n⏹ Остановлено пользователем"); break
    except Exception as e:
        print(time.strftime("[%H:%M:%S]"), "⚠️ Ошибка:", e)

    time.sleep(DELAY)
