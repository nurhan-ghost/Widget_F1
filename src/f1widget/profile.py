"""Season summaries and cached portraits, independent of Qt."""
import json
import time
from urllib.parse import quote
from urllib.request import Request, urlopen

from .service import API, MAX_AGE


def summarize(races, round_number):
    results = [(race, race["Results"][0]) for race in races
               if int(race["round"]) <= round_number and race.get("Results")]
    excluded = {"Did not start", "Did not qualify", "Did not prequalify", "Withdrew", "Withdrawn"}
    starts = sum(result.get("status") not in excluded for _, result in results)
    wins = [race["raceName"] for race, result in results if result["position"] == "1"]
    podiums = sum(int(result["position"]) <= 3 for _, result in results)
    return {"starts": starts, "wins": wins, "podiums": podiums}


class ProfileService:
    def __init__(self, cache_dir):
        self.cache_dir = cache_dir / "profiles"

    def request(self, url, binary=False):
        request = Request(url, headers={"User-Agent": "Formula1Widget/0.1.0"})
        with urlopen(request, timeout=12) as response:
            return response.read(5_000_000) if binary else json.load(response)

    def load(self, entry, season, round_number):
        path = self.cache_dir / f"{season}-{round_number}-{entry.identity}.json"
        cached = None
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            if 0 <= time.time() - cached["saved_at"] < MAX_AGE:
                return dict(cached, source="Saved")
        except (OSError, ValueError, KeyError, TypeError):
            cached = None
        try:
            data = self.request(f"{API}/{season}/drivers/{quote(entry.identity, safe='')}/results.json?limit=100")
            result = summarize(data["MRData"]["RaceTable"]["Races"], round_number)
            result["saved_at"] = time.time()
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                temp = path.with_suffix(".tmp")
                temp.write_text(json.dumps(result), encoding="utf-8")
                temp.replace(path)
            except OSError:
                pass
            return dict(result, source="Live")
        except (OSError, ValueError, KeyError, TypeError):
            if cached:
                return dict(cached, source="Offline · saved")
            raise

    def portrait(self, entry):
        path = self.cache_dir / f"{entry.identity}.png"
        try:
            if time.time() - path.stat().st_mtime < MAX_AGE * 7:
                return path.read_bytes()
        except OSError:
            pass
        try:
            drivers = self.request("https://api.openf1.org/v1/drivers?session_key=latest")
            driver = next(d for d in drivers if d.get("name_acronym") == entry.code)
            url = driver.get("headshot_url")
            if not url or not url.startswith("https://"):
                raise ValueError("No portrait")
            content = self.request(url, binary=True)
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            except OSError:
                pass
            return content
        except (OSError, ValueError, KeyError, TypeError, StopIteration):
            try:
                return path.read_bytes()
            except OSError:
                return b""
