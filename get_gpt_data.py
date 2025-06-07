from gpt import *
import json
import re

def extract_and_parse(raw: str):
    """
    Извлекает из произвольной строки участок от первого { до последнего }
    и парсит его как JSON.
    """
    # ищем шаблон { ... }
    m = re.search(r'(\{.*\})', raw, re.DOTALL)
    if not m:
        raise ValueError("Не удалось найти JSON в строке")
    json_str = m.group(1)
    # теперь парсим
    return json.loads(json_str)

def get_gpt_data(
    text: str,
) -> list[str]:
    did = new_dialog_id()
    post_message(did, "Дай мне все тикеры и организации которые связаны с этой новостью или тикеры и организации на которые эта новость может повлиять в формате JSON. Названия тикеров должны быть официальные, не выдумывай свои. Еще сделай сжатую новость. Также необходимо определить полярность (positive/negative/neutral), Интенсивность (сколько положительных/отрицательных слов) по 10 балльной шкале, где 1 - максимальная концентрация отрицательных слов, а 10 - положительные слова"
                      "Отправь в формате {tickers: [], organizations: [], compressed_message, polarity, intensity: }" + "\n" + text
                 + "\n"
                   "tickers - список официальных тикеров только следующих бумаг на Московской бирже:"
                   "organizations — список организаций (имена из текста)."
                   "compressed_message — сжатая новость."
                   "polarity - полярность новости"
                   "intensity - интенсивность новости")

    reply = get_response(did)
    if reply is not None:
        reset_dialog(did)
        return extract_and_parse(reply)
    else:
        reset_dialog(did)
        return None

