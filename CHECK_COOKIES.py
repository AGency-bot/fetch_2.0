import os
import time
import requests
import logging

REQUIRES = ["json_url", "cookies_raw"]
PROVIDES = ["cookies_valid"]

logger = logging.getLogger(__name__)
MIN_DELAY_SECONDS = float(os.getenv("MIN_DELAY_SECONDS", 0.4))

def adaptive_pause(label="pauza", seconds=MIN_DELAY_SECONDS):
    logger.info(f"{label} ({seconds:.2f}s)...")
    time.sleep(seconds)

def run(data):
    logger.info("Sprawdzam wa\u017cno\u015b\u0107 cookies (modu\u0142 informacyjny)...")

    url = data.get("json_url")
    raw_cookies = data.get("cookies_raw")

    if not url or not raw_cookies:
        logger.warning("Brak danych wej\u015bciowych: json_url lub cookies_raw. Pomijam sprawdzanie.")
        adaptive_pause("Brak danych – pauza awaryjna")
        return {"cookies_valid": False}

    headers = {
        "user-agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        ),
        "accept": "application/json, text/plain, */*",
        "x-requested-with": "XMLHttpRequest",
    }

    cookies = {}
    for pair in raw_cookies.split(";"):
        if "=" in pair:
            try:
                k, v = pair.strip().split("=", 1)
                cookies[k] = v
            except ValueError:
                continue

    try:
        response = requests.get(url, headers=headers, cookies=cookies, timeout=10)
        if response.status_code == 200:
            logger.info("Cookies s\u0105 wa\u017cne (200 OK).")
            adaptive_pause("Cookies OK – pauza ko\u0144cowa")
            return {"cookies_valid": True}
        elif response.status_code in [401, 403]:
            logger.warning(f"Cookies niewa\u017cne ({response.status_code}) – pipeline b\u0119dzie kontynuowany.")
        else:
            logger.warning(f"Nieoczekiwany kod odpowiedzi: {response.status_code} – kontynuuj\u0119.")
    except requests.Timeout:
        logger.error("Timeout – serwer nie odpowiedzia\u0142 na czas.")
    except requests.RequestException as e:
        logger.error(f"B\u0142\u0105d podczas sprawdzania cookies: {e}")

    adaptive_pause("Cookies b\u0142\u0119dne – pauza ko\u0144cowa")
    return {"cookies_valid": False}