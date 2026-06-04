import logging
from datetime import datetime
from typing import Dict, List
from zoneinfo import ZoneInfo

import httpx


log = logging.getLogger(__name__)

BASE_URL = "https://api.sofascore.com/api/v1"
TZ = ZoneInfo("Europe/Berlin")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
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
    return "".join(
        _CYR.get(character, character)
        for character in text.lower()
    )


def _normalize(text: str) -> str:
    text = _to_latin(text)
    text = text.lower()
    text = text.replace("-", " ")
    text = text.replace(".", " ")
    text = text.replace(",", " ")
    return " ".join(text.split())


async def get_todays_events(sport: str) -> List[Dict]:
    slug = SPORT_SLUG.get(sport)

    if not slug:
        log.error("Unknown sport slug: %s", sport)
        return []

    today = datetime.now(TZ).strftime("%Y-%m-%d")
    url = f"{BASE_URL}/sport/{slug}/scheduled-events/{today}"

    log.info("Requesting SofaScore URL: %s", url)

    try:
        async with httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=True,
        ) as client:
            response = await client.get(
                url,
                headers=HEADERS,
            )

        log.info(
            "SofaScore response: status=%s content_type=%s size=%s",
            response.status_code,
            response.headers.get("content-type"),
            len(response.text),
        )

        if response.status_code != 200:
            log.error(
                "SofaScore HTTP error: status=%s body=%s",
                response.status_code,
                response.text[:500],
            )
            return []

        payload = response.json()
        events = payload.get("events", [])

        log.info(
            "SofaScore sport=%s date=%s events=%s",
            sport,
            today,
            len(events),
        )

        return events

    except httpx.TimeoutException:
        log.exception("SofaScore timeout for URL: %s", url)
        return []

    except Exception:
        log.exception("SofaScore unexpected error for URL: %s", url)
        return []