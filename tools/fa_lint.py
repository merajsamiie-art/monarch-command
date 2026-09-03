#!/usr/bin/env python3
# 🈂️ fa_lint — «هیچ واژۀ لاتین در متنِ کاربر نمی‌ماند»
"""بررسی زنده‌ی متن‌هایی که بازیکن واقعاً می‌بیند.

botِ ساختگی + دیتابیس موقت → مجموعه‌ای از دستورهای واقعی → اسکنِ پاسخ‌ها.
فارسی/رقم/ایموجی/برچسب‌های HTML مجازاند؛ واژۀ لاتین (۳ حرف به بالا) خطاست،
مگر در ALLOW (دستورهای اسلش، شناسۀ تایتان برای /dossier، واحدهای علمی).

    python3 tools/fa_lint.py            # گزارش
    python3 tools/fa_lint.py --strict   # کدِ خروج ۱ در صورت تخلف
"""
import asyncio
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "monarch"))

import test_game as T                                          # noqa: E402
import player as PL                                            # noqa: E402
import events                                                   # noqa: E402

# ── برداشتِ متن از مسیر واقعی (Update → handler → FakeSession) ──────────────
TEXT_CMDS = ("/start", "/help", "/rules", "/me", "/profile", "/codex", "/clearance",
             "/titans", "/roster", "/dossier godzilla", "/dossier kong", "/dossier mechagodzilla",
             "/abilities", "/bond", "/combat", "/hunt suko", "/hunt king_ghidorah", "/boss",
             "/raid", "/explore", "/exp", "/missions", "/daily", "/shop", "/market", "/exchange",
             "/top", "/ranking", "/rank", "/arena", "/div", "/divisions", "/war", "/research",
             "/scan", "/kb", "/kb rules", "/cache", "/inventory", "/inv", "/status", "/zone",
             "/news", "/faq", "/join", "/board", "/leaderboard", "/event", "/items", "/craft")
BTN_CB = ("menu:codex", "menu:main", "menu:missions", "menu:explore", "menu:shop", "menu:div",
          "mis:claim", "dv:fac", "dv:top", "dv:war", "ra:join", "ra:strike", "ra:focus",
          "ra:shield", "ra:repair", "ra:analyze", "ra:regroup", "ar:me", "ar:go", "fac:lab")

ALLOW_RE = re.compile(
    r"^("
    r"[a-z0-9_]{2,20}"                     # شناسۀ تایتان/باس در دستور اسلش
    r"|/(?:start|help|rules|me|profile|codex|clearance|titans|roster|dossier|abilities|bond|combat"
    r"|hunt|boss|raid|explore|exp|missions|daily|shop|market|exchange|top|ranking|rank|arena|div"
    r"|divisions|war|research|scan|kb|cache|inventory|inv|status|zone|news|faq|join|board"
    r"|leaderboard|event|items|craft|new)"
    r"[:/a-z0-9_]*"
    r"|t\.me/[A-Za-z0-9_+.-]+"
    r"|godzilla|kong|mothra|ghidorah|mecha[\w-]*|suko|c++|html|ur[li]|api|id|db|http[s]?|www|jpg|png"
    r")$", re.I)

WORD = re.compile(r"[A-Za-z][A-Za-z0-9_.'\-]{2,}")
TAG = re.compile(r"</?[a-zA-Z][^>]*>")


def scan(text):
    """واژه‌های لاتینِ غیرمجاز در یک پیام (تگ‌های HTML حذف می‌شوند)."""
    body = TAG.sub(" ", text or "")
    body = re.sub(r"/[A-Za-z_]{2,16}(?:[ &<>;\u200c]+[A-Za-z0-9_\-]{1,16})+", " CMD ", body)
    out = []
    for m in WORD.finditer(body):
        w = m.group(0).strip(".'-")
        if not w or ALLOW_RE.match(w):
            continue
        out.append(w)
    return out


def main(strict=False):
    from aiogram.types import CallbackQuery, Update, User
    bot, sess = T.build_bot()
    uid, chat = 10001, -100901
    PL.ensure_player(uid, "Lint Agent", "lint")
    PL.set_row(uid, rank=9)
    T.fund(uid, credits=90_000, cores=400)
    T.equip_all(uid, 9)
    p = PL.get(uid)
    PL.set_row(uid, hp=p["max_hp"])
    events.ensure_chat(chat, "مانارچ لینت", "group")
    PL.note_chat(uid, chat)
    d = T.main_dp()

    errors = []

    import handlers as H

    async def go():
        for text in TEXT_CMDS:
            for st in ("_THROTTLE", "_BURST", "_SPAM_WARN", "_CARD_SEEN"):   # سقفِ ضداسپمِ lint نیست
                getattr(H, st, {}).clear()
            try:
                await d.feed_update(bot, Update(update_id=1, message=T.message(bot, text, uid, chat)))
            except Exception as exc:                      # خطای هندلر خودش هم تخلف است
                errors.append(f"{text} → {type(exc).__name__}: {exc}")
            await asyncio.sleep(0)
        for cb in BTN_CB:
            for st in ("_THROTTLE", "_BURST", "_SPAM_WARN"):
                getattr(H, st, {}).clear()
            q = CallbackQuery(id="cb", from_user=User(id=uid, is_bot=False, first_name="Lint"),
                              chat_instance="ci", data=cb,
                              message=T.message(bot, "/start", uid, chat)).as_(bot)
            await d.feed_update(bot, Update(update_id=2, callback_query=q))
    asyncio.run(go())

    texts = [d.get("text") or d.get("caption") or "" for n, d in sess.calls
             if n in ("sendMessage", "editMessageText", "sendPhoto", "editMessageCaption")]
    if errors:
        print("❌ خطای هندلر:")
        for e in errors[:10]:
            print("   " + e)
    hits = []
    for t in texts:
        bad = scan(t)
        if bad:
            hits.append((sorted(set(bad)), t))
    print(f"پیام‌های برداشت‌شده: {len(texts)} · خطاها: {len(errors)}")
    if errors:
        return 1
    if not texts:
        print("❌ هیچ پاسخی ثبت نشد — lint چیزی ندیده است")
        return 1
    if not hits:
        print("✅ هیچ واژۀ لاتینِ غیرمجاز در متن‌های کاربر نیست")
        return 0
    print(f"⚠️  {len(hits)} پیام هنوز لاتین دارد:")
    seen = set()
    for bad, t in hits:
        key = tuple(bad)
        if key in seen:
            continue
        seen.add(key)
        line = re.sub(r"\s+", " ", TAG.sub(" ", t)).strip()
        print(f"   {', '.join(bad):44} ← {line[:110]}")
    return 1 if strict else 0


if __name__ == "__main__":
    sys.exit(main("--strict" in sys.argv))
