from parsing.pars_finam import collect_set
import time
import unique_checker
import data_refactor
import dbnews

MAX_ITEMS = 3
delay = 60

ticker_lookup = {
        "лукойл": "LKOH",
        "транснефть": "TRNFP",
        "роснефть": "ROSN",
        "газпром нефть": "SIBN",
        "сбер": "SBER",
        "т-банк": "T",
        "совкомбанк": "SVCB",
        "втб": "VTBR",
        "яндекс": "YNDX",
        "вк": "VKCO",
        "ммк": "MAGN",
        "селигер": "SELG",
        "северсталь": "CHMF",
        "газпром": "GAZP",
        "котировки российского рынка": "IRUS",
        "xfive": "FIVE",
        "магнит": "MGNT",
    }
ticker_list = list(ticker_lookup.values())

db_config = {
    "dbname": "postgres",
    "user": "konstantinokriashvili",
    "password": "1234",
    "host": "localhost",
    "port": 5432
}

if __name__ == "__main__":

    checker = dbnews.DBNewsDeduplicator(db_config)

    print(f"Старт парсинга Finam, интервал {delay} с")
    while True:
        try:
            #print(collect_set())
            data_refactor.add_news(checker, collect_set(), ticker_lookup, ticker_list)

            data_refactor.print_news(checker)
            print("✓ Новости обновлены", flush=True)
        except Exception as err:
            print(f"‼ Ошибка: {err}", flush=True)
        time.sleep(delay)