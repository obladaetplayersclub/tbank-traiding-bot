import telethon
import re
import os
from dotenv import load_dotenv

load_dotenv()


str_api_id = os.getenv("API_ID")
if not str_api_id:
    raise ValueError("API_ID не установлена в переменных окружения")
api_id = int(str_api_id)

api_hash = os.getenv('API_HASH')
client = telethon.TelegramClient('session_name_1', api_id, api_hash)


# link = input()

async def main():
    channel_name = 'stocksi'
    channel = await client.get_entity(channel_name)
    messages = await client.get_messages(channel, limit=20)
    msg = set()
    for message in messages:
        if "#реклама" in message.text:
            continue
        if "Будь первым вместе c" in message.text:
            continue
        if "ERID:" in message.text:
            continue
        text = message.text
        text = re.sub(r'\[.*?\]\(.*?\)', '', text)
        text = re.sub(r'\s*[-–—]+\s*$', '', text)
        text = re.sub(r'\[👉.*?\]\(https://t\.me/.*?\)', '', text)
        text = re.sub(r'#\S+', '', text)
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(
            r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002702-\U000027B0\U000024C2-\U0001F251\U0001f926-\U0001f937]+',
            '', text)
        text = re.sub(r'\s{2,}', ' ', text).strip()
        msg.add(text)
        print(text)

with client:
    client.loop.run_until_complete(main())