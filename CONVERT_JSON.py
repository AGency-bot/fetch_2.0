import os
import json
import time
import logging
from datetime import datetime

REQUIRES = ["raw_json_path"]
PROVIDES = ["json_data", "cycle_id", "snapshot_paths"]

logger = logging.getLogger(__name__)
BASE_DIR = os.getenv("DATA_DIR", "/tmp")  # Render-friendly storage
MIN_DELAY_SECONDS = 0.4

VENDOR_FIELD_KEY = "fldxwoZ4nkNK8omVW"
MARCEL_KEYWORDS = ["marcel", "motoassist"]

def run(DATA_PIPE):
    logger.info("Konwertuj\u0119 surowy JSON do snapshot\u00f3w (marcel + motoassist)...")

    raw_json_path = DATA_PIPE.get("raw_json_path")
    if not raw_json_path or not os.path.exists(raw_json_path):
        raise ValueError("Brak \u015bcie\u017cki do pliku JSON!")

    with open(raw_json_path, "r", encoding="utf-8") as f:
        json_data = json.load(f)

    try:
        rows = json_data["data"]["table"]["rows"]
    except KeyError:
        raise ValueError("Nie uda\u0142o si\u0119 znale\u017a\u0107 pola 'data.table.rows' w JSON!")

    if not isinstance(rows, list):
        raise ValueError("'rows' nie jest list\u0105 – format danych niepoprawny!")

    logger.info(f"Za\u0142adowano {len(rows)} rekord\u00f3w.")

    marcel_records = []
    motoassist_records = []

    for row in rows:
        cell_data = row.get("cellValuesByColumnId", {})
        vendor = cell_data.get(VENDOR_FIELD_KEY)

        vendor_normalized = ""
        if isinstance(vendor, str):
            vendor_normalized = vendor.strip().lower()
        elif isinstance(vendor, list) and vendor:
            vendor_normalized = str(vendor[0]).strip().lower()

        if all(keyword in vendor_normalized for keyword in MARCEL_KEYWORDS):
            marcel_records.append(row)
        else:
            motoassist_records.append(row)

    logger.info(f"Znaleziono {len(marcel_records)} rekord\u00f3w 'marcel' i {len(motoassist_records)} 'motoassist'.")

    cycle_id = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    def write_snapshot(name, records):
        view_dir = os.path.join(BASE_DIR, name)
        os.makedirs(view_dir, exist_ok=True)
        filename = f"snapshot_{cycle_id}_{name}.json"
        path = os.path.join(view_dir, filename)
        payload = {
            "cycle_id": cycle_id,
            "records": records
        }
        with open(path, "w", encoding="utf-8") as f_out:
            json.dump(payload, f_out, ensure_ascii=False, indent=2)
        logger.info(f"Snapshot zapisany do: {path}")
        return path

    paths = {
        "marcel": write_snapshot("marcel", marcel_records),
        "motoassist": write_snapshot("motoassist", motoassist_records)
    }

    time.sleep(MIN_DELAY_SECONDS)

    return {
        "json_data": json_data,
        "cycle_id": cycle_id,
        "snapshot_paths": paths
    }