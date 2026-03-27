import asyncio
import json
import os
import hashlib
from telethon import TelegramClient, events

# ==========================================
# ЗАПОЛНИ ЭТИ 4 СТРОКИ — БОЛЬШЕ НИЧЕГО НЕ ТРОГАЙ
# ==========================================
API_ID       = 12345678          # число с my.telegram.org
API_HASH     = "сюда_вставь"     # строка с my.telegram.org
BOT_TOKEN    = "сюда_вставь"     # токен от @BotFather
TARGET       = "@financeabyl"    # юзернейм твоего канала
# ==========================================

SOURCE_CHANNELS = [
    "qara_aqqu", "nb_kz", "investingcorp", "bull_bell",
    "finmentorkz", "manualanomics", "FINANCEkaz", "rankingkz",
    "tengenomika", "usamarke1", "financenews13", "alfawealth",
    "monetarity", "financeview", "eurobonds", "ptfinchannel",
]

URGENT_WORDS = [
    "ставка", "нбрк", "тенге", "девальвация", "дефолт",
    "инфляция", "санкции", "обвал", "кризис", "экстренн",
    "повысил", "снизил", "доллар", "нефть", "биткоин"
]

SEEN_FILE = "seen_news.json"

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_seen(seen_list):
    seen_list = seen_list[-1000:]
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen_list, f, ensure_ascii=False, indent=2)

def get_hash(text):
    return hashlib.md5(text.strip().lower().encode()).hexdigest()

def is_urgent(text):
    text_lower = text.lower()
    return any(word in text_lower for word in URGENT_WORDS)

def is_duplicate(text, seen_texts):
    words = set(text.lower().split())
    for prev in seen_texts[-50:]:
        prev_words = set(prev.lower().split())
        if len(words) == 0:
            continue
        overlap = len(words & prev_words) / len(words)
        if overlap > 0.6:
            return True
    return False

async def main():
    print("=" * 40)
    print("  Бот запущен!")
    print(f"  Слежу за {len(SOURCE_CHANNELS)} каналами")
    print(f"  Пощу в {TARGET}")
    print("=" * 40)

    reader = TelegramClient("reader_session", API_ID, API_HASH)
    poster = TelegramClient("poster_session", API_ID, API_HASH)
    await poster.start(bot_token=BOT_TOKEN)

    seen_hashes = set()
    seen_data = load_seen()
    seen_texts = [item["text"] for item in seen_data]
    for item in seen_data:
        seen_hashes.add(item.get("hash", ""))

    print(f"  История: {len(seen_data)} новостей загружено\n")

    @reader.on(events.NewMessage(chats=SOURCE_CHANNELS))
    async def handler(event):
        msg = event.message
        text = getattr(msg, 'text', None) or getattr(msg, 'message', None) or ""
        text = text.strip()

        if len(text) < 60:
            return

        h = get_hash(text)
        source = getattr(event.chat, "username", "unknown")

        if h in seen_hashes:
            print(f"[ПРОПУСК] Точная копия из @{source}")
            return

        urgent = is_urgent(text)

        if not urgent and is_duplicate(text, seen_texts):
            print(f"[ПРОПУСК] Похожая новость из @{source}")
            return

        prefix = "🚨 СРОЧНО\n\n" if urgent else "📰\n\n"
        caption = f"{prefix}{text}\n\n📌 @{source}"

        try:
            await poster.send_message(TARGET, caption)

            seen_hashes.add(h)
            seen_texts.append(text[:300])
            seen_data.append({"hash": h, "text": text[:300], "source": source})
            save_seen(seen_data)

            tag = "СРОЧНО" if urgent else "запостил"
            print(f"[{tag}] из @{source}: {text[:60]}...")

        except Exception as e:
            print(f"[ОШИБКА] {e}")

    await reader.start()
    print("Жду новых постов...\n")
    await reader.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
