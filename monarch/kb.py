# ✨ Telegram UI — کیبوردهای inline (aiogram فقط اینجا وارد می‌شود)
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import config
import emoji as EMJ


def kb(rows: list) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t, callback_data=c) for c, t in r if t
    ] for r in rows if r])


def main_menu(p: dict = None, has_combat: bool = False) -> InlineKeyboardMarkup:
    r = []
    if has_combat:
        r.append([("cbt:resume", "⚔️ ادامه‌ی نبرد")])
    r += [
        [("menu:codex", "🦖 دیتابیس تایتان"), ("menu:track", "📡 ردیابی سیگنال")],
        [("menu:explore", "🗺 کاوش"), ("menu:boss", "🕹 عملیات باس")],
        [("menu:raid", "🌍 رید جهانی"), ("menu:arena", "🏆 آرنا")],
        [("menu:shop", "🪙 فروشگاه"), ("menu:inv", "🎒 تجهیز")],
        [("menu:missions", "📅 روزانه"), ("menu:div", "🏢 Division")],
        [("menu:top", "🏆 رنکینگ"), ("help", "📖 دستورنامه")],
        [(config.CHANNEL_URL, "📢 کانال"), (config.GROUP_URL, "👥 گروه")],
    ]
    return kb(r)


def combat_menu(cid: int, opts: list) -> InlineKeyboardMarkup:
    """ردیف‌های اکشن + مهارت‌ها؛ گزینه‌های قفل با 🔒 و دلیل."""
    base, abils = [], []
    for o in opts:
        label = f"{EMJ.of(o.get('emj'), '')} {o['text']}"
        if o.get("hint"):
            label += f" · {o['hint']}"
        if o.get("disabled"):
            label = "🔒" + label
            cb = None
        else:
            cb = o["cb"]
        (base if o["cb"].count(":") == 1 and o["cb"].split(":")[1] in
         ("atk", "heavy", "guard", "dodge", "counter", "charge", "overdrive", "retreat", "assist")
         else abils).append((cb, label))
    rows = []
    for i in range(0, len(base), 3):
        rows.append(base[i:i + 3])
    for i in range(0, len(abils), 2):
        rows.append(abils[i:i + 2])
    rows.append([(f"cbt:{cid}:info", "🛰 وضعیت"), (f"cbt:{cid}:help", "❓ راهنما")])
    return kb(rows)


def list_menu(items: list, cb_prefix: str, per_row: int = 2, back: str = "menu:main") -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(items), per_row):
        rows.append([(f"{cb_prefix}:{x[0]}", x[1]) for x in items[i:i + per_row]])
    if back:
        rows.append([(back, "↩️ بازگشت")])
    return kb(rows)


def confirm(cb_yes: str, label: str = "✅ تأیید", cb_no: str = "menu:main") -> InlineKeyboardMarkup:
    return kb([[(cb_yes, label), (cb_no, "✖️ انصراف")]])
