"""Jolpica transport and atomic, daily disk cache. No Qt dependencies."""
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen

API = "https://api.jolpi.ca/ergast/f1"
MAX_AGE = 24 * 60 * 60


class StandingsService:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir

    def read_cache(self, mode: str) -> dict | None:
        try:
            data = json.loads((self.cache_dir / f"{mode}.json").read_text(encoding="utf-8"))
            if not isinstance(data["current"], dict) or not isinstance(data["saved_at"], (float, int)):
                return None
            return data
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def fetch_table(self, season: str, mode: str, round_number: int | None = None) -> dict:
        round_path = f"/{round_number}" if round_number is not None else ""
        endpoint = "driverstandings" if mode == "drivers" else "constructorstandings"
        request = Request(f"{API}/{season}{round_path}/{endpoint}.json?limit=100",
                          headers={"User-Agent": "Formula1Widget/0.1.0"})
        with urlopen(request, timeout=15) as response:
            tables = json.load(response)["MRData"]["StandingsTable"]["StandingsLists"]
        if not tables:
            raise ValueError("Standings have not been published yet")
        return tables[0]

    def load(self, mode: str, force: bool = False) -> dict:
        cached = self.read_cache(mode)
        if cached and not force and 0 <= time.time() - cached["saved_at"] < MAX_AGE:
            return dict(cached, source="Saved")
        try:
            current = self.fetch_table("current", mode)
            previous = None
            if int(current["round"]) > 1:
                try:
                    previous = self.fetch_table(current["season"], mode, int(current["round"]) - 1)
                except (OSError, ValueError, KeyError):
                    pass  # Missing history must never hide current standings.
            data = {"current": current, "previous": previous, "saved_at": time.time()}
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                path = self.cache_dir / f"{mode}.json"
                temporary = path.with_suffix(".tmp")
                temporary.write_text(json.dumps(data), encoding="utf-8")
                temporary.replace(path)
            except OSError:
                return dict(data, source="Live · cache unavailable")
            return dict(data, source="Live")
        except (OSError, ValueError, KeyError):
            if cached:
                return dict(cached, source="Offline · saved")
            raise
