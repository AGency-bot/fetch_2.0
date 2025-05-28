import os

class AdaptiveController:
    def __init__(self, min_pause=None, max_pause=None, base_pause=None):
        self.min_pause = int(min_pause or os.getenv("MIN_CYCLE_PAUSE", 5))
        self.max_pause = int(max_pause or os.getenv("MAX_CYCLE_PAUSE", 20))
        self.pause = int(base_pause or os.getenv("CYCLE_PAUSE", 10))
        self.last_ids = set()

    def compute_ids(self, data):
        """Wydobywa zestaw unikalnych identyfikatorów z snapshotu JSON."""
        try:
            records = data.get("records", [])
            ids = {item["id"] for item in records if "id" in item}
            return ids
        except Exception:
            return set()

    def update(self, json_data):
        """Dostosowuje długość przerwy na podstawie liczby nowych rekordów."""
        current_ids = self.compute_ids(json_data)
        new_ids = current_ids - self.last_ids
        delta = len(new_ids)

        if delta == 0:
            self.pause = min(self.pause + 3, self.max_pause)
        elif delta <= 2:
            self.pause = max(self.pause - 1, self.min_pause)
        else:
            self.pause = max(self.pause - 3, self.min_pause)

        self.last_ids = current_ids
        return self.pause
