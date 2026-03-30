import asyncio
import json
import os
import hashlib
from telethon import TelegramClient, events

API_ID    = int(os.environ["API_ID"])
API_HASH  = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
TARGET    = os.environ["TARGET"]
PHONE     = os.environ.get("PHONE", "")

SOURCE_CHANNELS = [
    "qara_aqqu", "nb_kz", "investingcorp", "bull_bell",
    "finmentorkz", "manualanomics", "FINANCEkaz", "rankingkz",
    "tengenomika", "usamarke1", "financenews13", "alfawealth",
    "monetarity", "financeview", "eurobonds", "ptfinchannel",
]

# Корни слов — ищем вхождение, поэтому "банк" найдёт "банковский", "банков", "банке"
FINANCE_ROOTS = [
    # Казахстан
    "казахстан", "қазақстан", "нбрк", "нацбанк", "kase", "aix",
    "енпф", "kaspi", "halyk", "бцк", "forte", "jusan", "самрук",
    # Валюты и курсы
    "тенге", "доллар", "евро", "валют", "курс",
    # Банки и финансы
    "банк", "кредит", "депозит", "ипотек", "займ", "микрофинанс",
    # Рынки
    "бирж", "акци", "облигац", "etf", "фонд", "индекс",
    # Макро
    "инфляц", "ставк", "бюджет", "ввп", "экономик", "рецессия",
    "дефляц", "дефолт", "девальвац",
    # Сырьё
    "нефт", "газ", "золот", "уран", "металл", "сырь",
    # Крипта
    "биткоин", "крипт", "блокчейн", "стейблкоин",
    # Глобальные
    "фрс", "мвф", "центробанк", "минфин",
    "санкц", "импорт", "экспорт", "торговл",
    "дивиденд", "доходност", "прибыл", "убыток",
    "инвестиц", "капитал", "актив", "портфел",
    "тариф", "комисси", "процент", "купон",
    "размещен", "погашен", "выпуск",
    "страхов", "пенсионн",
    # Компании
    "мосбирж", "nasdaq", "s&p", "dow jones",
]

URGENT_WORDS = [
    "девальвац", "дефолт", "обвал", "кризис",
    "экстренн", "резко упал", "резко вырос",
    "повысил ставку", "снизил ставку",
]

BLACKLIST = [
    "подборка каналов", "топовых каналов", "наши каналы",
    "подпишись на наш", "viralist", "giveaway", "розыгрыш",
    "пассивный доход", "инвестируй с нами",
    "в госдуме", "кремль", "мобилизац",
    "сво ", "украин", "донбасс",
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
    return any(root in t for root in FINANCE_ROOTS)

def is_urgent(text):
    t = text.lower()
    return any(word in t for word in URGENT_WORDS)

def is_duplicate(text, seen_texts):
    words = set(text.lower().split())
    if not words:
        return False
    for prev in seen_texts[-100:]:
        prev_words = set(prev.lower().split())
        if len(words & prev_words) / len(words) > 0.8:
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

    await reader.start(phone=PHONE)
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

        if len(text) < 60:
            return

        if is_blacklisted(text):
            print(f"[БЛОК] из @{source}: {text[:60]}...")
            return

        if not is_finance(text):
            print(f"[НЕ ФИНАНСЫ] из @{source}: {text[:60]}...")
            return

        h = get_hash(text)

        if h in seen_hashes:
            print(f"[ДУБЛИКАТ] из @{source}")
            return

        urgent = is_urgent(text)

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
