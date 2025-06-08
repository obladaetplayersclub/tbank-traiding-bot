import requests, uuid, time
import os

API_BASE = os.getenv("API_BASE")
API_KEY = os.getenv("API_KEY")
OSC = 12
USER = os.getenv("USER")

def new_dialog_id():
    return f"{USER}_{uuid.uuid4().hex}"

def post_message(dialog_id: str, text: str):
    payload = {
        "operatingSystemCode": OSC,
        "apiKey": API_KEY,
        "userDomainName": USER,
        "dialogIdentifier": dialog_id,
        "aiModelCode": 1,
        "Message": text           # заглавная M
    }
    r = requests.post(f"{API_BASE}/PostNewRequest", json=payload)
    r.raise_for_status()

def get_response(dialog_id: str, timeout=30, interval=2):
    payload = {
        "operatingSystemCode": OSC,
        "apiKey": API_KEY,
        "dialogIdentifier": dialog_id
    }
    start = time.time()
    while time.time() - start < timeout:
        r = requests.post(f"{API_BASE}/GetNewResponse", json=payload)
        r.raise_for_status()
        resp = r.json()
        #print("DEBUG response JSON:", resp)

        # вот здесь достаём поле data
        data = resp.get("data")
        if data and data.get("lastMessage"):
            return data["lastMessage"]

        time.sleep(interval)
    return None


def reset_dialog(dialog_id: str):
    payload = {
        "operatingSystemCode": OSC,
        "apiKey": API_KEY,
        "dialogIdentifier": dialog_id
    }
    r = requests.post(f"{API_BASE}/CompleteSession", json=payload)
    r.raise_for_status()