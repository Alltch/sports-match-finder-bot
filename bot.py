import asyncio
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
from rapidfuzz import fuzz

import parsers.sofascore as ss


load_dotenv()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

bot = Bot(token=BOT_TOKEN)
router = Router()

TZ = ZoneInfo("Europe/Berlin")


class IsOwner(Filter):
    async def __call__(self, event) -> bool:
        if OWNER_ID == 0:
            return True

        user_id = getattr(getattr(event, "from_user", None), "id", 0)
        return user_id == OWNER_ID


class SearchFlow(StatesGroup):
    select_sport = State()
    enter_name = State()
    select_match = State()


SPORTS = [
    ("⚽ Football", "football"),
    ("🎾 Tennis", "tennis"),
    ("🏀 Basketball", "basketball"),
    ("🤾 Handball", "handball"),
    ("🏒 Hockey", "ice-hockey"),
]

ICONS = {
    "football": "⚽",
    "tennis": "🎾",
    "basketball": "🏀",
    "handball": "🤾",
    "ice-hockey": "🏒",
}


def kb_sports():
    keyboard = InlineKeyboardBuilder()

    for label, sport_key in SPORTS:
        keyboard.button(
            text=label,
            callback_data=f"sport:{sport_key}",
        )

    keyboard.adjust(2)
    return keyboard.as_markup()


def kb_matches(matches: list[dict]):
    keyboard = InlineKeyboardBuilder()

    for index, match in enumerate(matches):
        time_prefix = (
            f"{match['start_time']}  "
            if match.get("start_time")
            else ""
        )

        button_text = (
            f"{time_prefix}"
            f"{match['home']} vs {match['away']}"
        )

        if len(button_text) > 62:
            button_text = button_text[:59] + "…"

        keyboard.button(
            text=button_text,
            callback_data=f"match:{index}",
        )

    keyboard.button(
        text="🔍 Search again",
        callback_data="match:search",
    )

    keyboard.adjust(1)
    return keyboard.as_markup()


def search_matches(
    events: list[dict],
    query: str,
    limit: int = 10,
) -> list[dict]:
    normalized_query = ss._normalize(query)
    scored_events = []

    for event in events:
        home = event.get("homeTeam", {}).get("name", "")
        away = event.get("awayTeam", {}).get("name", "")

        normalized_home = ss._normalize(home)
        normalized_away = ss._normalize(away)
        normalized_title = f"{normalized_home} {normalized_away}"

        score = max(
            fuzz.partial_ratio(normalized_query, normalized_home),
            fuzz.partial_ratio(normalized_query, normalized_away),
            fuzz.token_set_ratio(normalized_query, normalized_title),
        )

        if score >= 30:
            scored_events.append((score, event))

    scored_events.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    matches = []

    for score, event in scored_events[:limit]:
        home = event.get("homeTeam", {}).get("name", "?")
        away = event.get("awayTeam", {}).get("name", "?")

        timestamp = event.get("startTimestamp")
        start_time = ""

        if timestamp:
            start_time = datetime.fromtimestamp(
                timestamp,
                TZ,
            ).strftime("%H:%M")

        tournament = event.get("tournament", {}).get("name", "")
        category = event.get("tournament", {}).get(
            "category",
            {},
        ).get(
            "name",
            "",
        )

        matches.append(
            {
                "home": home,
                "away": away,
                "start_time": start_time,
                "tournament": (
                    f"{category} · {tournament}"
                    if category
                    else tournament
                ),
                "score": round(score),
            }
        )

    return matches


def format_selected_match(match: dict) -> str:
    lines = [
        "✅ Нужный матч найден",
        "",
        f"⚔️ {match['home']} vs {match['away']}",
    ]

    if match.get("tournament"):
        lines.append(f"🏆 {match['tournament']}")

    if match.get("start_time"):
        lines.append(f"📅 Today · {match['start_time']}")

    return "\n".join(lines)


@router.message(Command("start"), IsOwner())
async def cmd_start(
    message: Message,
    state: FSMContext,
):
    await state.clear()
    await state.set_state(SearchFlow.select_sport)

    await message.answer(
        "Выберите спорт:",
        reply_markup=kb_sports(),
    )


@router.callback_query(
    F.data.startswith("sport:"),
    IsOwner(),
)
async def cb_sport(
    callback: CallbackQuery,
    state: FSMContext,
):
    sport = callback.data.split(":", 1)[1]
    icon = ICONS.get(sport, "🎯")

    await state.update_data(sport=sport)
    await state.set_state(SearchFlow.enter_name)

    await callback.message.edit_text(
        f"{icon} {sport.replace('-', ' ').title()} selected\n\n"
        "Напиши название команды или игрока:"
    )

    await callback.answer()


@router.message(
    SearchFlow.enter_name,
    IsOwner(),
    F.text,
)
async def on_name_entered(
    message: Message,
    state: FSMContext,
):
    query = message.text.strip()

    data = await state.get_data()
    sport = data.get("sport", "football")
    icon = ICONS.get(sport, "🎯")

    status_message = await message.answer(
        "🔍 Searching SofaScore…"
    )

    events = await ss.get_todays_events(sport)

    if not events:
        await status_message.edit_text(
            "⚠️ SofaScore не вернул матчи на сегодня."
        )
        return

    matches = search_matches(
        events=events,
        query=query,
    )

    if not matches:
        await status_message.edit_text(
            f"Ничего не найдено по запросу: {query}\n\n"
            "Попробуй написать короче, например только "
            "фамилию или часть названия."
        )
        return

    await state.update_data(matches=matches)
    await state.set_state(SearchFlow.select_match)

    await status_message.edit_text(
        f"{icon} Найдено матчей: {len(matches)}\n\n"
        "Выбери нужный матч:",
        reply_markup=kb_matches(matches),
    )


@router.callback_query(
    F.data == "match:search",
    IsOwner(),
)
async def cb_search_again(
    callback: CallbackQuery,
    state: FSMContext,
):
    data = await state.get_data()
    sport = data.get("sport", "football")
    icon = ICONS.get(sport, "🎯")

    await state.set_state(SearchFlow.enter_name)

    await callback.message.edit_text(
        f"{icon} Напиши другое название команды или игрока:"
    )

    await callback.answer()


@router.callback_query(
    F.data.startswith("match:"),
    IsOwner(),
)
async def cb_match_selected(
    callback: CallbackQuery,
    state: FSMContext,
):
    if callback.data == "match:search":
        return

    match_index = int(
        callback.data.split(":", 1)[1]
    )

    data = await state.get_data()
    matches = data.get("matches", [])

    if match_index >= len(matches):
        await callback.answer(
            "Ошибка. Начни заново через /start",
            show_alert=True,
        )
        return

    selected_match = matches[match_index]

    await callback.message.edit_text(
        format_selected_match(selected_match)
    )

    await state.clear()
    await callback.answer()


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing in .env")

    dispatcher = Dispatcher(
        storage=MemoryStorage()
    )

    dispatcher.include_router(router)

    log.info("Bot started")

    await bot.delete_webhook(
        drop_pending_updates=True
    )

    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
