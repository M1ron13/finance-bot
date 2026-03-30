import asyncio
import json
import os
import hashlib
from telethon import TelegramClient, events

API_ID    = int(os.environ["API_ID"])
API_HASH  = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
TARGET    = os.environ["TARGET"]

SOURCE_CHANNELS = [
    "qara_aqqu", "nb_kz", "bull_bell",
    "finmentorkz", "manualanomics", "FINANCEkaz", "rankingkz",
    "tengenomika", "usamarke1", "financenews13", "alfawealth",
    "monetarity", "financeview", "eurobonds", "ptfinchannel",
    "investingcorp",
]

# Казахстанские финансовые слова — ОБЯЗАТЕЛЬНО одно из них
KZ_FINANCE = [
    "тенге", "қазақстан", "казахстан", "нбрк", "нацбанк",
    "kase", "aix", "енпф", "kaspi", "halyk", "бцк", "forte",
    "jusan", "народный банк", "банк центркредит",
    "минфин казахстан", "акимат", "самрук",
]

# Глобальные финансовые слова — тоже подходят
GLOBAL_FINANCE = [
    "доллар", "евро", "валюта", "курс валют",
    "ставка фрс", "фрс", "центробанк", "мвф",
    "нефть", "газ", "золото", "уран",
    "биткоин", "крипта", "криптовалюта",
    "акции", "облигации", "биржа", "etf",
    "инфляция", "дефляция", "рецессия",
    "санкции", "импорт", "экспорт",
    "дивиденды", "доходность", "ипотека",
]

# Срочные — постим с пометкой СРОЧНО
URGENT_WORDS = [
    "девальвация", "дефолт", "обвал рынка", "кризис",
    "экстренное заседание", "резко упал", "резко вырос",
    "повысил базовую ставку", "снизил базовую ставку",
]

# Чёрный список — явная реклама и мусор
BLACKLIST = [
    "подборка каналов", "топовых каналов", "наши каналы",
    "подпишись на наш", "viralist", "giveaway", "розыгрыш",
    "пассивный доход", "инвестируй с нами",
    "перейти по ссылке", "жми сюда", "кликай",
    # Российский мусор который не касается КЗ
    "в госдуме", "кремль", "путин", "мобилизация",
    "сво ", "всу ", "украин", "донбасс",
]

SEEN_FILE = "seen_news.json"

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_seen(seen_list):
    seen_list = seen_list[-2000:]
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen_list, f, ensure_ascii=False, indent=2)

def get_hash(text):
    return hashlib.md5(text.strip().lower().encode()).hexdigest()

def is_blacklisted(text):
    t = text.lower()
    return any(word in t for word in BLACKLIST)

def is_finance(text):
    t = text.lower()
    return any(word in t for word in KZ_FINANCE + GLOBAL_FINANCE)

def is_urgent(text):
    t = text.lower()
    return any(word in t for word in URGENT_WORDS)

def is_duplicate(text, seen_texts):
    words = set(text.lower().split())
    if not words:
        return False
    for prev in seen_texts[-100:]:
        prev_words = set(prev.lower().split())
        overlap = len(words & prev_words) / len(words)
        if overlap > 0.8:
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
    await reader.start()
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
        text = getattr(msg, 'message', '') or getattr(msg, 'text', '') or ""
        text = text.strip()
        source = getattr(event.chat, "username", "unknown")

        # Слишком короткий
        if len(text) < 80:
            return

        # Чёрный список
        if is_blacklisted(text):
            print(f"[БЛОК] из @{source}: {text[:60]}...")
            return

        # Не финансовая новость
        if not is_finance(text):
            print(f"[НЕ ФИНАНСЫ] из @{source}: {text[:60]}...")
            return

        h = get_hash(text)

        # Точный дубликат
        if h in seen_hashes:
            print(f"[ДУБЛИКАТ] из @{source}")
            return

        urgent = is_urgent(text)

        # Похожая новость (80% порог — строже)
        if not urgent and is_duplicate(text, seen_texts):
            print(f"[ПОХОЖЕЕ] из @{source}")
            return

        prefix = "🚨 СРОЧНО\n\n" if urgent else "📰\n\n"
        post = f"{prefix}{text}\n\n📌 @{source}"

        try:
            await poster.send_message(TARGET, post)
            seen_hashes.add(h)
            seen_texts.append(text[:500])
            seen_data.append({"hash": h, "text": text[:500], "source": source})
            save_seen(seen_data)
            tag = "🚨 СРОЧНО" if urgent else "✅ запостил"
            print(f"[{tag}] из @{source}: {text[:60]}...")
        except Exception as e:
            print(f"[ОШИБКА] {e}")

    print("Жду новых постов...\n")
    await reader.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
