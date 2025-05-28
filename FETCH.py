import os
import time
import datetime
import importlib
import traceback
import threading
import logging
from playwright.sync_api import sync_playwright
from ADAPTIVE import AdaptiveController
from dotenv import load_dotenv

# Konfiguracja loggera
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Wczytaj zmienne środowiskowe
load_dotenv("S3.env", override=False)

DATA_PIPE = {}
MODULES = ["LOGIN", "CHECK_COOKIES", "CONVERT_JSON", "EXPORT_S3"]
MAX_RETRIES = 3
CYCLE_PAUSE_SECONDS = int(os.getenv("CYCLE_PAUSE", 10))
MIN_CYCLE_PAUSE = int(os.getenv("MIN_CYCLE_PAUSE", 5))
MAX_CYCLE_PAUSE = int(os.getenv("MAX_CYCLE_PAUSE", 20))

stop_requested = False

def set_stop_requested(value: bool):
    global stop_requested
    stop_requested = value

def generate_cycle_id():
    return datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

class DelayController:
    def __init__(self, base_delay=0.4, max_delay=5.0, multiplier=1.5):
        self.delay = base_delay
        self.base = base_delay
        self.max = max_delay
        self.multiplier = multiplier

    def success(self):
        self.delay = max(self.base, self.delay * 0.7)
        return self.delay

    def fail(self):
        self.delay = min(self.max, self.delay * self.multiplier)
        return self.delay

class RestartPipelineException(Exception):
    pass

def run_module(module_name, delay_controller):
    logger.info(f"➡️ Uruchamiam moduł: {module_name}.py")
    try:
        mod = importlib.import_module(module_name)
        requires = getattr(mod, "REQUIRES", [])
        provides = getattr(mod, "PROVIDES", [])

        for req in requires:
            if req not in DATA_PIPE:
                raise ValueError(f"Brakuje wymaganych danych: {req} dla {module_name}")

        result = mod.run(DATA_PIPE)

        if isinstance(result, dict):
            for k, v in result.items():
                if k in provides:
                    DATA_PIPE[k] = v

        logger.info(f"✅ Moduł {module_name} zakończony pomyślnie.")
        pause = delay_controller.success()
        logger.info(f"⏸️ Przerwa po module ({pause:.2f}s)...")
        time.sleep(pause)
        return True

    except RestartPipelineException:
        raise

    except Exception as e:
        if module_name == "CHECK_COOKIES":
            logger.warning(f"CHECK_COOKIES zgłosił błąd, ale pipeline kontynuuje: {e}")
            return True
        logger.error(f"❌ Błąd w module {module_name}: {e}", exc_info=True)
        pause = delay_controller.fail()
        logger.warning(f"⏸️ Przerwa po błędzie ({pause:.2f}s)...")
        time.sleep(pause)
        return False

# --- Main loop ---
def main(start_api=True):  # dodany parametr, domyślnie True
    global stop_requested
    run_mode = os.getenv("RUN_MODE", "loop")
    logger.info(f"Tryb uruchomienia: {run_mode}")

    adaptive_enabled = os.getenv("ADAPTIVE_MODE", "1") == "1"
    adaptive = AdaptiveController(min_pause=MIN_CYCLE_PAUSE, max_pause=MAX_CYCLE_PAUSE, base_pause=CYCLE_PAUSE_SECONDS)

    with sync_playwright() as p:
        while not stop_requested:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = browser.new_context()
            page = context.new_page()

            DATA_PIPE.clear()
            DATA_PIPE["browser"] = browser
            DATA_PIPE["login_context"] = context
            DATA_PIPE["page"] = page

            delay_controller = DelayController()
            restart_cycle = False

            try:
                cycle_id = generate_cycle_id()
                logger.info(f"🚀 Rozpoczynam cykl: {cycle_id}")
                DATA_PIPE["cycle_id"] = cycle_id

                for module in MODULES:
                    if stop_requested:
                        logger.info("⛔ Działanie przerwane w trakcie cyklu")
                        break

                    for attempt in range(MAX_RETRIES):
                        logger.info(f"🔁 Próba {attempt + 1}/{MAX_RETRIES} dla {module}...")
                        try:
                            if run_module(module, delay_controller):
                                break
                        except RestartPipelineException:
                            logger.warning("🔄 Restart pełnego pipeline.")
                            restart_cycle = True
                            break

                    if restart_cycle:
                        break

            finally:
                logger.info("🧹 Zamykanie przeglądarki...")
                browser.close()

            if run_mode == "once" or stop_requested:
                break

            if restart_cycle:
                logger.info("🔄 Restart pełnego cyklu...")
                continue

            if adaptive_enabled and "json_data" in DATA_PIPE:
                new_pause = adaptive.update(DATA_PIPE["json_data"])
                logger.info(f"[ADAPTIVE] Pauza: {new_pause:.1f}s")
                time.sleep(new_pause)
            else:
                logger.info(f"⏱️ Pauza domyślna: {CYCLE_PAUSE_SECONDS}s")
                time.sleep(CYCLE_PAUSE_SECONDS)

if __name__ == "__main__":
    main(start_api=True)
