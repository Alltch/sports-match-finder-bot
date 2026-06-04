import httpx
import logging
from datetime import date
from typing import List, Dict

log = logging.getLogger(__name__)

BASE_URL = "https://api.sofascore.com/api/v1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://www.sofascore.com/",
    "Accept": "application/json",
}

SPORT_SLUG = {
    "football": "football",
    "basketball": "basketball",
    "tennis": "tennis",
    "ice-hockey": "ice-hockey",
    "handball": "handball",
}

_CYR = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d",
    "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i",
    "й": "y", "к": "k", "л": "l", "м": "m", "н": "n",
    "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
    "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch",
    "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "",
    "э": "e", "ю": "yu", "я": "ya",
}


def _to_latin(text: str) -> str:
    return "".join(_CYR.get(ch, ch) for ch in text.lower())


def _normalize(text: str) -> str:
    text = _to_latin(text)
    text = text.lower()
    text = text.replace("-", " ")
    text = text.replace(".", " ")
    text = text.replace(",", " ")
    text = " ".join(text.split())
    return text


async def get_todays_events(sport: str) -> List[Dict]:
    slug = SPORT_SLUG.get(sport, "football")
    today = date.today().strftime("%Y-%m-%d")

    url = f"{BASE_URL}/sport/{slug}/scheduled-events/{today}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=HEADERS)

        if response.status_code != 200:
            log.warning(f"SofaScore HTTP {response.status_code}: {response.text[:200]}")
            return []

        events = response.json().get("events", [])
        log.info(f"SofaScore {sport}: {len(events)} events")
        return events

    except Exception as e:
        log.warning(f"SofaScore error: {e}")
        return []