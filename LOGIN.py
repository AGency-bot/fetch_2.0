import os
import time
import logging
from datetime import datetime
from playwright.sync_api import TimeoutError

# Konfiguracja loggera
logger = logging.getLogger(__name__)

LOGIN_URL = "https://airtable.com/appcNCfp1rJvcF9RL/shrCd3zAzIFvxuB8n/tbl1UpRkbBHJpMmax"
PASSWORD = os.getenv("AIRTABLE_PASSWORD")

if not PASSWORD:
    raise EnvironmentError("Brakuje zmiennej AIRTABLE_PASSWORD")

REQUIRES = ["page", "login_context"]
PROVIDES = ["cookies_raw", "json_url", "raw_json_path"]

BASE_DIR = os.getenv("DATA_DIR", "/tmp")

def adaptive_pause(label="pauza", seconds=0.6):
    logger.info(f"{label} ({seconds:.2f}s)...")
    time.sleep(seconds)

def run(data):
    logger.info("Logowanie i przechwytywanie JSON URL...")

    page = data["page"]
    context = data["login_context"]
    json_request_url = None
    json_response_text = None

    def handle_response(response):
        nonlocal json_request_url, json_response_text
        try:
            if "readSharedViewData" in response.url and response.status == 200 and json_request_url is None:
                logger.info(f"Przechwycono JSON z: {response.url}")
                json_request_url = response.url

                for attempt in range(5):
                    try:
                        json_response_text = response.text()
                        break
                    except Exception as e:
                        logger.warning(f"B\u0142\u0105d przy odczycie JSON (pr\u00f3ba {attempt+1}/5): {e}")
                        time.sleep(1)
        except Exception as e:
            logger.warning(f"B\u0142\u0105d w handle_response: {e}")

    page.on("response", handle_response)

    try:
        page.goto(LOGIN_URL, timeout=120000)
        logger.info("Strona logowania za\u0142adowana.")
    except TimeoutError:
        raise Exception("Timeout przy otwieraniu strony logowania.")

    try:
        page.wait_for_selector("input[name='password']", timeout=10000)
        page.fill("input[name='password']", PASSWORD)
        page.keyboard.press("Enter")
        adaptive_pause("Pauza po ENTER", 0.6)
    except TimeoutError:
        logger.info("Ju\u017c zalogowano – pomijam logowanie.")
    except Exception as e:
        raise Exception(f"B\u0142\u0105d przy wprowadzaniu has\u0142a: {e}")

    try:
        cookie_btn = page.locator("button#onetrust-accept-btn-handler")
        if cookie_btn.is_visible(timeout=5000):
            cookie_btn.click()
            logger.info("Cookies zaakceptowane.")
            adaptive_pause("Pauza po cookies", 0.3)
        else:
            logger.warning("Brak cookies – kontynuacja.")
    except Exception as e:
        logger.warning(f"B\u0142\u0105d przy akceptowaniu cookies: {e}")

    try:
        page.wait_for_selector("text=MARCEL - MOTOASSIST", timeout=60000)
        logger.info("Gie\u0142da za\u0142adowana.")
        adaptive_pause("Pauza po za\u0142adowaniu gie\u0142dy", 0.6)
    except TimeoutError:
        raise Exception("Widok gie\u0142dy nie zosta\u0142 wykryty – logowanie nie powiod\u0142o si\u0119.")

    try:
        cookies_list = context.cookies()
        cookies_raw = "; ".join(f"{cookie['name']}={cookie['value']}" for cookie in cookies_list)
    except Exception as e:
        raise Exception(f"Nie uda\u0142o si\u0119 pobra\u0107 cookies: {e}")

    logger.info("Oczekiwanie na przechwycenie danych JSON...")
    max_wait_seconds = 30
    elapsed = 0
    while json_response_text is None and elapsed < max_wait_seconds:
        time.sleep(1)
        elapsed += 1

    if json_response_text is None:
        raise Exception("Nie przechwycono danych JSON!")

    raw_json_dir = os.path.join(BASE_DIR, "raw_json")
    os.makedirs(raw_json_dir, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
    raw_json_path = os.path.join(raw_json_dir, f"snapshot_RAW_{timestamp}.json")

    with open(raw_json_path, "w", encoding="utf-8") as f:
        f.write(json_response_text)

    return {
        "cookies_raw": cookies_raw,
        "json_url": json_request_url,
        "raw_json_path": raw_json_path
    }