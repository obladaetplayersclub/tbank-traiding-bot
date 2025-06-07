import json
import time
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

import feedparser
import requests
from bs4 import BeautifulSoup

SRC_RSS_URL = "https://lenta.ru/rss/news/economics"
OUT_FILE = Path("lenta_economics.xml")
MAX_ITEMS = 5
delay = 60
JSON_FILE = Path("news_rss.json")

def fed_pars(url: str) -> dict:
    resp = requests.get(url, timeout=10, headers={"User-Agent": "rss-bot/1.0"})
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)
    return feed

def add_el(feed_data: feedparser.FeedParserDict) -> ET.ElementTree:
    rss = ET.Element("rss", version="2.0")
    chan = ET.SubElement(rss, "channel")

    ET.SubElement(chan, "title").text = feed_data.get("title", "Lenta.ru – Экономика")
    ET.SubElement(chan, "link").text = "https://lenta.ru/rubrics/economics/"
    ET.SubElement(chan, "description").text = "Экономические новости Lenta.ru (локальная копия)"
    ET.SubElement(chan, "language").text = "ru"
    ET.SubElement(chan, "lastBuildDate").text = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

    for entry in feed_data.entries[:MAX_ITEMS]:
        item = ET.SubElement(chan, "item")
        ET.SubElement(item, "title").text = entry.title
        ET.SubElement(item, "link").text = entry.link
        ET.SubElement(item, "pubDate").text = entry.published
        ET.SubElement(item, "description").text = entry.summary

    return ET.ElementTree(rss)

def save_tree(tree: ET.ElementTree, path: Path):
    tree.write(path, encoding="utf-8", xml_declaration=True)
    print(f"RSS сохранён в {path}")

def add_title(tree: ET.ElementTree) -> tuple[str, datetime, str, str]:
    titles = []
    root = tree.getroot()
    for item in root.findall(".//item"):
        title = item.find("title")
        date_str = item.find("pubDate")
        url = item.find("link")
        if date_str is not None and title is not None and title.text is not None:
            dt = datetime.strptime(date_str.text.strip(), "%a, %d %b %Y %H:%M:%S %z")
            formatted_date = dt.strftime("%d %B, %H:%M")
            url_1 = url.text.strip()
            url_txt = requests.get(url_1, timeout=10)
            soup = BeautifulSoup(url_txt.text, "lxml")
            other_part = soup.find("div", class_="topic-body__content")
            other_paragraphs = other_part.find_all("p", class_="topic-body__content-text")
            text_paragraphs2 = [p.get_text(strip=True) for p in other_paragraphs]
            article_txt = "\n".join(text_paragraphs2)
            article_txt = article_txt.replace("\u00A0", " ")
            titles.append((title.text, formatted_date, url_1, article_txt))
    return titles

def save_title_to_json(titles: tuple[str, datetime, str, str]):
    all_links = []
    for title, formatted_date, url, article_txt in titles:
        all_links.append({"title" : title, "data" : formatted_date, "url" : url, "text" : article_txt})
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(all_links, f, ensure_ascii=False, indent=2)
    print("Данные в JSON записаны!")

def get_jsons(titles: tuple[str, datetime, str, str]) -> set:
    all_links = set()
    for title, formatted_date, url, article_txt in titles:
        all_links.add(article_txt)
    return all_links

def main():
    first_run = True
    while True:
        if first_run:
            tm = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
            print(f"Начали парсинг в {tm}")
            first_run = False
        else:
            update_time = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
            print(f"Обновляем данные {update_time}")
        try:
            feed = fed_pars(SRC_RSS_URL)
            rss_tree = add_el(feed)
            save_tree(rss_tree, OUT_FILE)
            # save_title_to_json(add_title(rss_tree))
            s = get_jsons(add_title(rss_tree))
            print(s)
            print("лоз")
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        time.sleep(delay)

if __name__ == "__main__":
    main()