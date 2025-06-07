import json
import html
import calendar
import time
from datetime import datetime, timezone, timedelta
import locale
from pathlib import Path
from bs4 import BeautifulSoup

import feedparser
import requests


url = "https://www.finam.ru/analysis/conews/rsspoint/"
MAX_ITEMS = 3
delay = 60
JSON_FILE = Path("news_finam.json")

locale.setlocale(locale.LC_TIME, "C")

MOSCOW_TZ = timezone(timedelta(hours=3))

def get_resp(url: str) -> str:
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.text

def get_xml_dict(xml_str: str) -> dict:
    feed = feedparser.parse(xml_str)
    return feed

def clean_html(raw: str) -> str:
    text = BeautifulSoup(raw, "lxml").get_text(" ", strip=True)
    return html.unescape(text)

def format_pub_date(entry) -> str:
    if getattr(entry, "published_parsed", None):
        ts = calendar.timegm(entry.published_parsed)               # всегда UTC
        dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
    else:                                                           # fallback
        dt_utc = datetime.now(timezone.utc)

    dt_msk = dt_utc.astimezone(MOSCOW_TZ)
    return dt_msk.strftime("%d %B, %H:%M")


def collect_items(feed: feedparser.FeedParserDict, max_items: int = MAX_ITEMS) -> list[dict]:
    items = []
    for entry in feed.entries[:max_items]:
        item = {
            "title": clean_html(entry.title),
            "data": format_pub_date(entry),
            "url": entry.link.strip(),
            "text": clean_html(entry.get("summary", entry.get("description", "")))
        }
        items.append(item)

    return items


def write_json(data: list[dict]) -> None:
    JSON_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def collect_set() -> set[str]:
    xml_text = get_resp(url)
    feed = get_xml_dict(xml_text)
    news = collect_items(feed)
    ans = set()
    for item in news:
        ans.add(item["text"])
    return ans


def main():
    print(f"Старт парсинга Finam, интервал {delay} с")
    while True:
        try:
            #xml_text = get_resp(url)
            #feed = get_xml_dict(xml_text)
            #news = collect_items(feed)
            #write_json(news)
            print(collect_set())
            print("✓ Новости обновлены", flush=True)
        except Exception as err:
            print(f"‼ Ошибка: {err}", flush=True)
        time.sleep(delay)

if __name__ == "__main__":
    main()