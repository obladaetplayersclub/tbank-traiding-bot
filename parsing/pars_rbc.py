import json, time, urllib.parse, requests
from json import JSONDecodeError
from pathlib import Path
from typing import Iterable, Iterator
from datetime import datetime
import re
import time
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://quote.rbc.ru"
DELAY = 60
HEADERS = {"User-Agent": "Mozilla/5.0 (headline-bot/1.0)"}
HEADLINE_SEL = "span.q-item__title.js-rm-central-column-item-text"
TIME_SELECTORS = ("time", "span.article__data-time", "span.article__header__date")

# Множество для хранения описаний (уникальных текстов статей)
descriptions = set()

def req(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.text

def iter_headline_links(html: str) -> Iterator[tuple[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    for a in soup.select(f"a:has({HEADLINE_SEL})"):
        span = a.select_one(HEADLINE_SEL)
        if span and "href" in a.attrs:
            yield span.get_text(strip=True), urllib.parse.urljoin(BASE_URL, a["href"])

def parse_article(url: str) -> str:
    soup = BeautifulSoup(req(url), "lxml")
    body = soup.select_one("div.article__text")
    if body:
        text = body.get_text(" ", strip=True).replace("\u00A0", " ")
    else:
        text = "\n".join(p.get_text(" ", strip=True) for p in soup.find_all("p")).strip()
    return text

def collect_set():
    descriptions = set()
    html = req(BASE_URL)
    for headline, url in iter_headline_links(html):
        try:
            text = parse_article(url)
            if text.strip():
                descriptions.add(text)
        except Exception as e:
            print(f"[⚠️] Ошибка при обработке {url}: {e}")
    return descriptions

def main():
    while True:
        try:
            html = req(BASE_URL)
            new_count = 0
            for headline, url in iter_headline_links(html):
                text = parse_article(url)
                if text not in descriptions and text.strip():
                    descriptions.add(text)
                    new_count += 1
            print(f"[{time.strftime('%H:%M:%S')}] добавлено {new_count} новых описаний")

        except KeyboardInterrupt:
            print("\n⏹ Остановлено пользователем")
            break
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] ⚠️ Ошибка: {e}")

        time.sleep(DELAY)

if __name__ == "__main__":
    main()