# 🚪 دروازۀ ورود — «تمامِ بازی در گروه می‌چرخد»
"""سه قاعده، یک فایل:

▪️ **پیوی**: هیچ دستوری از بازی اجرا نمی‌شود؛ فقط کارتِ «من را به گروه اضافه کن».
▪️ **گروه**: باید بیش از ۴ عضو داشته باشد (``config.MIN_MEMBERS``، پیش‌فرض ۵) —
   گروه خلوت صحنۀ نبرد نمی‌شود و ربات هم برای «اجازه نداری» گروه را شلوغ نمی‌کند.
▪️ **گروهِ اصلی**: هیچ محدودیتی ندارد؛ از ``GROUP_ID`` (محیط) یا ``/setmain``
   داخلِ خودِ گروه شناخته می‌شود و این استثنا در دیتابیس می‌ماند.

شمارشِ اعضا کش می‌شود (``COUNT_TTL``) و اگر تلگرام عدد را ندهد دروازہ بسته
نمی‌شود (شکستِ API نباید بازی را بخواباند). متن‌ها همین‌جا تولید می‌شوند تا
همه‌ی مسیرها (اسلش، پیشوندِ فارسی، دکمه‌ها) یک کارت ببینند.
"""
import logging

import config
import db
import fa
import kb as KEYB
import ui
from db import now

log = logging.getLogger("monarch.access")

COUNT_TTL = 900            # کشِ شمارشِ اعضا (ثانیه)
NOTICE_COOL = 15 * 60      # هر کاربر/چت/دلیل، یک اخطار در ۱۵ دقیقه
PV_ALLOW = {"start", "help", "join"}    # در پیوی فقط دروازہ و دستورنامۀ ورود

_counts = {}               # chat_id -> (member_count, ts)
_noticed = {}              # (uid, chat_id, why) -> ts


# ───────────────────────── تشخیصِ چت ─────────────────────────
def is_private(chat, chat_id=None) -> bool:
    ctype = str(getattr(chat, "type", "") or "")
    if ctype:
        return ctype == "private"
    return int(chat_id or 0) > 0


def is_channel(chat) -> bool:
    return str(getattr(chat, "type", "") or "") == "channel"


def main_groups() -> set:
    """گروه‌های آزادِ اصلی: تنظیماتِ محیط + آنچه با /setmain ثبت شده."""
    out = set(getattr(config, "MAIN_GROUPS", set()) or set())
    try:
        for r in db.db().q("SELECT key, value FROM kv WHERE key LIKE 'main:%'"):
            if str(r["value"]) == "1":
                out.add(int(str(r["key"]).split(":")[1]))
    except Exception:                                # جدولِ نبوده/دیتابیسِ خام
        pass
    return out


def is_main(chat_id) -> bool:
    return int(chat_id) in main_groups()


def mark_main(chat_id, on: bool = True) -> None:
    db.db().setv(f"main:{int(chat_id)}", "1" if on else "0")


def cached_count(chat_id):
    hit = _counts.get(int(chat_id))
    if hit and now() - hit[1] < COUNT_TTL:
        return hit[0]
    return None


async def members(bot, chat_id):
    """عضوِ گروه، با کش؛ ``None`` یعنی نفهمیدیم (و آنگاه دروازہ باز می‌ماند)."""
    cid = int(chat_id)
    hit = cached_count(cid)
    if hit is not None:
        return hit
    n = None
    try:
        n = int(await bot.get_chat_member_count(cid))
    except Exception as e:                           # بلاک/فد/چتِ حذف‌شده
        log.debug("member count failed for %s: %s", cid, str(e)[:80])
        n = None
    _counts[cid] = (n, now())
    return n


def forget(chat_id) -> None:
    _counts.pop(int(chat_id), None)


# ───────────────────────── حکمِ نهایی ─────────────────────────
async def verdict(bot, chat, uid: int, chat_id: int = None) -> tuple:
    """``(ok, why, count)`` — why ∈ ``""|pv|small|channel``."""
    chat_id = int(chat_id if chat_id is not None else chat.id)
    if config.is_admin(uid):
        return True, "", -1
    if is_private(chat, chat_id):
        return False, "pv", 0
    if is_channel(chat):
        return False, "channel", 0
    if is_main(chat_id):
        return True, "main", -1
    n = await members(bot, chat_id)
    if n is None:
        return True, "unknown", 0
    need = int(getattr(config, "MIN_MEMBERS", 5))
    return (n >= need), ("" if n >= need else "small"), n


def may_notify(uid: int, chat_id: int, why: str) -> bool:
    """ضداسپمِ خودِ دروازہ: یک بار در ``NOTICE_COOL``، بقیه بی‌صدا."""
    key = (int(uid), int(chat_id), why)
    t = now()
    if t - float(_noticed.get(key) or 0) < NOTICE_COOL:
        return False
    _noticed[key] = t
    return True


# ───────────────────────── کارت‌ها ─────────────────────────
def _bot_link() -> str:
    return f"https://t.me/{config.BOT_USER}?startgroup=true"


def pv_rows() -> list:
    return [[(_bot_link(), "➕ افزودنِ ربات به گروه")],
            [(config.GROUP_URL, "👥 گروهِ اصلیِ مانارچ"),
             (config.CHANNEL_URL, "📢 کانالِ فرماندهی")]]


def pv_text(name: str = "") -> str:
    rows = [
        f"👤 {name}" if name else "👤 مهمانِ مانارچ",
        "",
        "اینجا فقط دروازۀ ورود است؛ هیچ نبردی در پیوی راه نمی‌رود.",
        "همۀ بازی در گروه می‌چرخد: ردیابی، نمونه‌برداری، شکار، باس،"
        " یورشِ جهانی، سازمان و رتبۀ هفتگی.",
        "",
        ui.sect("چطور وارد شوی"),
        " ▪️ ربات را به گروه خودت اضافه کن (اولین پیام را خودم می‌فرستم)",
        f" ▪️ گروه باید بیش از {fa.fa_num(int(getattr(config, 'MIN_MEMBERS', 5)) - 1)} عضو داشته باشد",
        " ▪️ در گروهِ اصلیِ مانارچ: <code>/start</code>",
        "",
        "<i>🛰 گروهِ اصلیِ مانارچ بدونِ محدودیتِ عضو فعال است</i>",
    ]
    return ui.card("فرماندۀ مانارچ · دروازۀ ورود", rows,
                   sub="پیوی · فقط عضوگیری", stamp="دسترسیِ گروهی",
                   code=abs(hash(("pv", name or "guest"))) % 9000 + 1000,
                   note="تایتان‌ها در گروه منتظرند.")


def small_text(count: int) -> str:
    need = int(getattr(config, "MIN_MEMBERS", 5))
    rows = [
        f"▪️ اعضای گروه: <b>{fa.fa_num(count)}</b> {ui.DOT} حداقل لازم: <b>{fa.fa_num(need)}</b>",
        "",
        "مانارچ در گروهِ خلوت اجرا نمی‌شود: نبردِ یک‌نفره نه معنا دارد"
        " نه امنیتِ ضداسپم.",
        "",
        ui.sect("راه‌حل"),
        " ▪️ اعضای بیشتری دعوت کن و دوباره <code>/start</code> بفرست",
        " ▪️ یا به گروهِ اصلیِ مانارچ بپیوند (از هر اندازه‌ای فعال است)",
        " ▪️ فرمانده با <code>/setmain</code> این گروه را آزاد می‌کند",
    ]
    return ui.card("گروه هنوز صحنۀ عملیات نیست", rows,
                   sub="دروازۀ عضویت بسته است", stamp="محدود",
                   code=abs(hash(("small", count))) % 9000 + 1000,
                   note="جهان منتظر می‌ماند — چیزی نمی‌سوزد.")


def channel_text() -> str:
    rows = ["کانالِ فرماندهی تریبونِ اخبار است، نه میدانِ نبرد.", "",
            "▪️ آموزش‌ها، پرونده‌های تایتان و خبرِ باس‌ها اینجا منتشر می‌شود",
            "▪️ بازی در گروه می‌چرخد: <code>/start</code> داخلِ گروه"]
    return ui.card("اینجا کانال است", rows, sub="پخشِ یک‌طرفه",
                   stamp="بدونِ دستور", note="اخبار را بخوان، نبرد را در گروه بده.")


def text_for(why: str, name: str = "", count: int = 0) -> str:
    return {"pv": pv_text(name), "small": small_text(count),
            "channel": channel_text()}.get(why, pv_text(name))


def kb_for(why: str):
    if why == "small":
        return KEYB.kb([[(config.GROUP_URL, "👥 گروهِ اصلیِ مانارچ")],
                        [(_bot_link(), "➕ افزودنِ ربات به گروه")]])
    return KEYB.kb(pv_rows())
