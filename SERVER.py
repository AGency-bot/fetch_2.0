from flask import Flask, jsonify
import threading
import os
import logging

from FETCH import main, set_stop_requested

app = Flask(__name__)
logger = logging.getLogger(__name__)
is_running = False
thread_ref = None

def run_fetch():
    global is_running
    try:
        main(start_api=False)  # niech FETCH nie odpala swojego serwera
    finally:
        is_running = False

@app.route("/start", methods=["GET"])
def start_fetch():
    global is_running, thread_ref
    if not is_running:
        is_running = True
        thread_ref = threading.Thread(target=run_fetch, daemon=True)
        thread_ref.start()
        logger.info("Fetcher uruchomiony przez API.")
        return jsonify({"status": "started"}), 200
    else:
        return jsonify({"status": "already running"}), 200

@app.route("/status", methods=["GET"])
def status():
    return jsonify({"running": is_running}), 200

@app.route("/stop", methods=["GET"])
def stop_fetch():
    global is_running
    if is_running:
        set_stop_requested(True)
        logger.info("Fetcher zatrzymywany przez API.")
        return jsonify({"status": "stopping"}), 200
    else:
        return jsonify({"status": "not running"}), 200

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Serwer API startuje na porcie {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
