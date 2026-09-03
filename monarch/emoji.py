# ✨ Emoji Registry — منبع واحد ایموجی (کد هیچ‌جا ایموجی خام ندارد)
# هر کلید → {"u": ایموجی یونیکد, "x": custom_emoji_id (اختیاری، از data/emoji.json)}
# اگر data/emoji.json پک سفارشی تلگرام را داشته باشد، خروجی <tg-emoji> می‌شود.
import json
import os

_REGISTRY = {
    # ── system ──
    "satellite": "🛰", "shield_doc": "🗄", "access": "🔓", "denied": "🔒",
    "alert": "🚨", "radar": "📡", "classified": "🗝", "file": "📁",
    "check": "✅", "cross": "❌", "hourglass": "⏳", "lock": "🔐",
    "warning": "⚠️", "binary": "🧮", "brief": "🗒",
    # ── combat ──
    "sword": "⚔️", "heavy": "💥", "guard": "🛡", "dodge": "⚡",
    "counter": "🎯", "ability": "☄️", "charge": "🔋", "retreat": "🏃",
    "clash": "🌀", "crit": "❗️", "miss": "🕳", "block": "🧱", "flee": "💨",
    # ── titan / godzilla ──
    "godzilla": "🦖", "kong": "🦍", "mothra": "🦋", "ghidorah": "🐉",
    "rodan": "🔥", "mecha": "🤖", "anguirus": "🦔", "destoroyah": "☠️",
    "spacegod": "🌌", "biollante": "🧬", "gigan": "👽", "hedorah": "🟢",
    "megalon": "⚡", "caesar": "🦁", "titanosaurus": "🦕", "battra": "🌪",
    "jet": "🚁", "moguera": "🛰", "baragon": "🦡", "kumonga": "🕷",
    "kamacuras": "🦗", "ebirah": "🦞", "manda": "🐍", "gorosaurus": "🥋",
    "varan": "🦎", "orga": "👾", "megaguirus": "🦟", "monsterx": "👹",
    "keizer": "🐲", "skar": "⛓", "shimo": "❄️", "suko": "🐒",
    "tiamat": "🌊", "scylla": "🦑", "behemoth": "🐘", "methuselah": "🌿",
    "amhuluk": "🪝", "abaddon": "🪳", "muto": "🦇", "skullcrawler": "💀",
    "warbat": "🦴", "atom": "☢️", "crown": "👑", "spark": "🟣",
    # ── boss ──
    "boss": "🕹", "skull": "💀", "phase": "🔄", "rage": "😡", "eye": "👁",
    "horns": "🐗", "mech": "🦾", "queen": "🕸", "breach": "🌒",
    # ── death ──
    "dead": "☠️", "coffin": "⚰️", "respawn": "❤️‍🩹", "vitals": "🫀", "sirens": "📢",
    # ── loot / economy ──
    "coin": "🪙", "core": "💎", "dna": "🧬", "cell": "🔋", "material": "🔩",
    "data": "📡", "crate": "📦", "loot": "🎁", "sell": "🏷", "gear": "⚙️",
    "medkit": "🩹", "chip": "🔲", "blueprint": "📐",
    # ── event / world ──
    "ocean": "🌊", "city": "🏙", "volcano": "🌋", "ice": "❄️", "jungle": "🌲",
    "hollow": "🕳", "nuclear": "☢️", "space": "🌌", "storm": "🌩",
    "quake": "🌍", "signal": "📶", "mission": "🗺", "trophy": "🏆",
    "flame": "🔥", "div": "🏢", "light": "✨", "dark": "🌑",
    "gem": "💎", "acid": "🧪", "swarm": "🐜", "blade": "🗡", "solar": "☀️",
    "flight": "🪽", "intel": "🧠", "web": "🕸", "frost": "🧊", "plasma": "🟣",
    "tusk": "🦷", "claw": "🪝", "bolt": "🌩", "toxic": "☣️", "spiral": "🌀", "war": "⚔️", "research": "🔬", "track": "🎧",
}

_CUSTOM = {}
_LOADED = False


def load():
    """بارگذاری نگاشت custom-emoji (اگر data/emoji.json موجود باشد)."""
    global _LOADED, _CUSTOM
    _LOADED = True
    path = os.path.join(os.path.dirname(__file__), "data", "emoji.json")
    try:
        with open(path, encoding="utf-8") as f:
            _CUSTOM = json.load(f).get("custom", {})
    except Exception:
        _CUSTOM = {}
    return _CUSTOM


def has_custom() -> bool:
    if not _LOADED:
        load()
    return bool(_CUSTOM)


def set_custom(mapping: dict):
    """ادمین/اسکریپت می‌تواند در زمان اجرا پک را فعال کند."""
    global _CUSTOM, _LOADED
    _LOADED = True
    _CUSTOM = dict(mapping or {})


def raw(key: str, default="🛰") -> str:
    if not key:
        return default
    if not _LOADED:
        load()
    if key in _REGISTRY:
        return _REGISTRY[key]
    # اگر همین‌جا ایموجیِ واقعی داده شده (مثلاً «🥉») همان را برمی‌گردانیم؛
    # این اجازه می‌دهد داده‌ها یک‌بار در زمان build حل شوند و دوباره‌خوانی خراب نشود.
    if len(str(key)) <= 4 and not str(key).isascii():
        return str(key)
    return default


def of(key: str, default="🛰") -> str:
    """ایموجیِ یونیکدِ خالص (برای ذخیره در داده‌ها و لیبل دکمه — بدون تگ HTML)."""
    return raw(key, default)


def get(key: str, default="🛰") -> str:
    """HTML-ready: در صورت وجود پک سفارشی، <tg-emoji> می‌سازد."""
    sym = raw(key, default)
    eid = _CUSTOM.get(key)
    if eid:
        return f'<tg-emoji emoji-id="{eid}">{sym}</tg-emoji>'
    return sym


def strip_tags(text: str) -> str:
    """برای لاگ/تست: حذف تگ‌های tg-emoji."""
    out, i = [], 0
    while True:
        a = text.find("<tg-emoji", i)
        if a < 0:
            out.append(text[i:])
            break
        b = text.find(">", a)
        c = text.find("</tg-emoji>", b)
        if b < 0 or c < 0:
            out.append(text[i:])
            break
        out.append(text[i:a])
        out.append(text[b + 1:c])
        i = c + len("</tg-emoji>")
    return "".join(out)
