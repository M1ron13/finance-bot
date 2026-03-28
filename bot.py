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
    "qara_aqqu", "nb_kz", "investingcorp", "bull_bell",
    "finmentorkz", "manualanomics", "FINANCEkaz", "rankingkz",
    "tengenomika", "usamarke1", "financenews13", "alfawealth",
    "monetarity", "financeview", "eurobonds", "ptfinchannel",
]
 
# Обязательные финансовые слова — пост выйдет ТОЛЬКО если есть хотя бы одно
FINANCE_WORDS = [
    "тенге", "доллар", "евро", "валюта", "курс",
    "банк", "кредит", "депозит", "ставка", "нбрк",
    "инфляция", "экономика", "бюджет", "налог", "ввп",
    "акции", "облигации", "биржа", "kase", "aix",
    "инвестиции", "дивиденды", "доходность", "фонд", "etf",
    "нефть", "газ", "золото", "уран", "металл",
    "биткоин", "крипта", "криптовалюта", "стейблкоин",
    "фрс", "минфин", "мвф", "центробанк",
    "импорт", "экспорт", "торговля", "санкции",
    "ипотека", "займ", "микрофинанс", "страховк",
    "пенсионн", "енпф", "социальн",
    "тариф", "комиссия", "процент", "купон",
    "размещени", "погашени", "выпуск облигац",
    "казахстан", "алматы", "астана", "қазақстан",
]
 
# Срочные слова — постим с пометкой СРОЧНО
URGENT_WORDS = [
    "девальвация", "дефолт", "обвал", "кризис", "экстренн",
    "повысил ставку", "снизил ставку", "резко упал", "резко вырос",
]
 
# Спам — всегда блокируем
SPAM_WORDS = [
    "подпишись", "подписывайтесь", "подписаться",
    "подборка каналов", "топовых каналов", "топовые каналы",
    "рекомендуем", "реклама", "промо", "партнёр",
    "перейти по ссылке", "viralist", "присоединяйтесь",
    "под управлением", "публичный портфель",
    "розыгрыш", "giveaway", "конкурс", "приз",
    "скидка", "только сегодня", "успей",
    "заработай", "пассивный доход",
    "инвестируй с нами", "наш канал", "наши каналы",
    "перейди", "жми", "кликай",
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
 
def is_spam(text):
    return any(word in text.lower() for word in SPAM_WORDS)
 
def is_finance(text):
    return any(word in text.lower() for word in FINANCE_WORDS)
 
def is_urgent(text):
    return any(word in text.lower() for word in URGENT_WORDS)
 
def is_duplicate(text, seen_texts):
    words = set(text.lower().split())
    for prev in seen_texts[-50:]:
        prev_words = set(prev.lower().split())
        if len(words) == 0:
            continue
        if len(words & prev_words) / len(words) > 0.75:
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
    await reader.start(bot_token=BOT_TOKEN)
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
 
        if len(text) < 60:
            return
 
        source = getattr(event.chat, "username", "unknown")
 
        # 1. Фильтр спама
        if is_spam(text):
            print(f"[СПАМ] из @{source}: {text[:60]}...")
            return
 
        # 2. Фильтр — только финансовые новости
        if not is_finance(text):
            print(f"[НЕ ФИНАНСЫ] из @{source}: {text[:60]}...")
            return
 
        h = get_hash(text)
 
        # 3. Точный дубликат
        if h in seen_hashes:
            print(f"[ДУБЛИКАТ] из @{source}")
            return
 
        urgent = is_urgent(text)
 
        # 4. Похожая новость (порог поднят до 75%)
        if not urgent and is_duplicate(text, seen_texts):
            print(f"[ПОХОЖЕЕ] из @{source}")
            return
 
        prefix = "🚨 СРОЧНО\n\n" if urgent else "📰\n\n"
        post = f"{prefix}{text}\n\n📌 @{source}"
 
        try:
            await poster.send_message(TARGET, post)
            seen_hashes.add(h)
            seen_texts.append(text[:300])
            seen_data.append({"hash": h, "text": text[:300], "source": source})
            save_seen(seen_data)
            tag = "СРОЧНО" if urgent else "запостил"
            print(f"[{tag}] из @{source}: {text[:60]}...")
        except Exception as e:
            print(f"[ОШИБКА] {e}")
 
    print("Жду новых постов...\n")
    await reader.run_until_disconnected()
 
if __name__ == "__main__":
    asyncio.run(main())
