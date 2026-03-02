import json
import os
import threading
import time

from config import GITHUB_TOKEN, OPENROUTER_API_KEY, OPENROUTER_MODEL, REPO, DEFAULT_DAYS, TOP_N, CACHE_TTL
from github_data import get_pr_data
from calculator import ImpactCalculator

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
_lock = threading.Lock()
_memory_cache: dict = {}


def _disk_path(days: int) -> str:
    return os.path.join(CACHE_DIR, f"engineers_{days}.json")


def _load_from_disk(days: int) -> dict | None:
    path = _disk_path(days)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"[cache] Failed to read {path}: {e}")
        return None


def _save_to_disk(days: int, data: dict) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = _disk_path(days)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w") as f:
            json.dump(data, f)
        os.replace(tmp, path)
        print(f"[cache] Wrote {path}")
    except OSError as e:
        print(f"[cache] Failed to write {path}: {e}")


def get_cached_engineers(days: int) -> dict | None:
    with _lock:
        return _memory_cache.get(days)


def _refresh(days: int, retries: int = 3) -> None:
    """Fetch from GitHub, compute scores, and update both memory and disk caches."""
    for attempt in range(1, retries + 1):
        print(f"[cache] Refreshing data for {days} days (attempt {attempt}/{retries})...", flush=True)
        start = time.time()
        try:
            pulls, comments = get_pr_data(GITHUB_TOKEN, REPO, days=days)
            calculator = ImpactCalculator(pulls, comments, api_key=OPENROUTER_API_KEY, model=OPENROUTER_MODEL)
            engineers = calculator.compute(top_n=TOP_N, days=days)

            result = {
                "engineers": engineers,
                "meta": {
                    "repo": REPO,
                    "days": days,
                    "total_prs_analyzed": len(pulls),
                    "total_comments_analyzed": len(comments),
                    "cached": True,
                },
            }

            with _lock:
                _memory_cache[days] = result
            _save_to_disk(days, result)

            elapsed = time.time() - start
            print(f"[cache] Refresh complete for {days} days in {elapsed:.1f}s", flush=True)
            return
        except Exception as e:
            elapsed = time.time() - start
            print(f"[cache] Refresh failed for {days} days after {elapsed:.1f}s: {e}", flush=True)
            if attempt < retries:
                wait = 30 * attempt
                print(f"[cache] Retrying in {wait}s...", flush=True)
                time.sleep(wait)


def _background_loop() -> None:
    """Runs in a daemon thread: load disk cache, then refresh periodically."""
    days = DEFAULT_DAYS

    disk_data = _load_from_disk(days)
    if disk_data is not None:
        with _lock:
            _memory_cache[days] = disk_data
        print(f"[cache] Loaded {days}-day data from disk cache")

    while True:
        _refresh(days)
        time.sleep(CACHE_TTL)


def start_background_refresh() -> None:
    thread = threading.Thread(target=_background_loop, daemon=True)
    thread.start()
    print("[cache] Background refresh thread started")
