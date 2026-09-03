#!/usr/bin/env python3
"""🪪 سه‌گانه‌سازیِ هویت: بات، کانال و گروه — هرکدام نام، کپشن و پروفایلِ **خودش**.

خانواده یکی است (مانارچ)، اما سه چهره‌ی متفاوت:

· بات  → ابزارِ بازی: «دستِ تو در میدان»
· کانال → آرشیو: آموزش، دیتابیس تایتان‌ها، پروندۀ گودزیلا، اخبار باس و رویداد، سؤالات متداول
· گروه → میدانِ عملیات: جایی که نبردها، یورش‌ها و کاوش‌ها اجرا می‌شوند

    python3 tools/setup_bot_ui.py                              # منو + نام/بیو/توضیحِ بات
    python3 tools/setup_bot_ui.py --channel -1004499194759     # + هویتِ کانال
    python3 tools/setup_ui.py  --group -100XXXX --channel -1004499194759   # هر سه
    python3 tools/setup_bot_ui.py --all-known                  # از ENV (CHANNEL_ID/GROUP_ID)

نکته: تلگرام API متدی برای **عکس پروفایلِ خودِ بات** ندارد — فایل
`assets/bot_avatar.jpg` را دستی از حسابِ BotFather/بات آپلود کن. عکسِ کانال و
گروه را همین اسکریپت ست می‌کند (بات باید ادمینِ «تغییر اطلاعات» باشد).
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: F401  → monarch/ را به sys.path اضافه می‌کند

import config  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AVATARS = {k: os.path.join(ROOT, "assets", f"{k}_avatar.jpg") for k in ("bot", "channel", "group")}

# ═══════════════ سه هویتِ متفاوت، یک خانواده ═══════════════
BOT = dict(
    name="🦖☢️ فرماندۀ مانارچ",
    short="دستِ تو در میدان: شکار، پژوهش، یورش — شبانه‌روزی زنده است.",
    full=("رباتِ نبرد و پژوهشِ تایتان‌ها برای گروه‌های فارسی.\n"
          "از تازه‌وارثی تا فرماندۀ آلفا: هیچ تایتانی هدیه نمی‌آید؛ باید پیدایش کنی.\n\n"
          "▪️ پرونده‌سازی: /track → /sample → /analyze → /bond\n"
          "▪️ نبرد هشت‌دکمه‌ای با فاز، خشم و نقطۀ ضعف\n"
          "▪️ یورش جهانی، سازمان‌ها، کاوش، صرافی و رتبۀ فصلی\n"
          "▪️ هیچ خریدی قدرت نمی‌فروشد و اسپم برنده نمی‌شود\n\n"
          "▸ برای شروع در گروه: /start"),
)
CHANNEL = dict(
    title="🛰 مانارچ · آرشیوِ پرونده‌ها",
    desc=("آرشیوِ طبقه‌بندی‌شدۀ فرماندۀ مانارچ.\n"
          "▪️ آموزشِ گام‌به‌گام (درس ۰۱ تا ۱۲)\n"
          "▪️ دیتابیس تایتان‌ها و پروندۀ گودزیلا\n"
          "▪️ اخبار باس‌ها، رویدادها و فصلِ آرنا\n"
          "▪️ پرسش‌های متداول و یادداشت‌های تعادل\n\n"
          "▸ بازی در گروه انجام می‌شود؛ عضویت در این کانال برای بازی لازم است."),
)
GROUP = dict(
    title="🦖 فرماندۀ مانارچ · میدانِ عملیات",
    desc=("میدانِ عملیات: نبردها، یورش‌های جهانی، کاوش‌ها و سازمان‌ها این‌جا اجرا می‌شوند.\n"
          "▪️ /start برای ثبت‌نام · /help برای دستورنامه · /rules برای پروتکل\n"
          "▪️ پیام‌های نبرد در یک فیدِ فشرده ویرایش می‌شوند — گروه شلوغ نمی‌شود\n"
          "▪️ مرگ یعنی ۱۰ دقیقه حالتِ بازیابی؛ هستۀ تایتان هرگز نمی‌افتد\n\n"
          "▸ تایتان‌ها از قبل اینجا بودند."),
)


# برچسبِ فارسیِ منوی تلگرام — کلیدها از COMMAND_MAP می‌آیند، پس منو هیچ‌وقت
# با کد نمی‌خواند و هیچ دستورِ مرده‌ای در منو نمی‌ماند.
LABELS = {
    "start": "🛰 شروع و ثبت‌نام عامل",
    "help": "📟 دستورنامه",
    "rules": "⚖️ پروتکلِ نبرد",
    "me": "🪪 کارتِ عامل",
    "clearance": "🎖 رتبه و پیش‌نیازها",
    "codex": "📁 دیتابیس تایتان‌ها",
    "dossier": "🗂 پروندۀ تایتان",
    "track": "📡 رهگیری سیگنال",
    "sample": "🧬 نمونه‌برداری",
    "analyze": "🔬 تحلیلِ نمونه",
    "lab": "🧪 نتیجۀ آزمایشگاه",
    "bond": "👑 پیوند با تایتان",
    "hunt": "⚔️ شکارِ داوطلبانه",
    "fight": "🗡 ادامهٔ نبرد",
    "boss": "🕹 عملیات باس",
    "raid": "🌍 یورشِ جهانی",
    "scan": "🛰 وضعیتِ منطقه",
    "report": "📋 گزارشِ روزانه",
    "explore": "🗺 اعزام تیم کاوش",
    "missions": "✅ مأموریت‌های روزانه",
    "daily": "📅 حضورِ روزانه",
    "top": "🏆 جدولِ رتبه",
    "arena": "🥊 آرنا",
    "duel": "🤺 دوئل",
    "ref": "⚖️ داوریِ نبرد",
    "shop": "🪙 تأمینات",
    "inv": "🎒 کمدِ میدانی",
    "equip": "🥼 تجهیزِ آیتم",
    "use": "💊 مصرفِ آیتم",
    "upgrade": "⚙️ ارتقای تجهیز",
    "market": "🏷 صرافی",
    "sell": "💰 فروشِ منابع",
    "vault": "🏦 خزانهٔ سازمان",
    "bounty": "🎯 جایزۀ شکار",
    "puzzle": "🔐 رمزنگارِ مانارچ",
    "div": "🏢 سازمان‌ها",
    "join": "📌 پیوستن به گروه",
}


def _cmds():
    """منوی /commands — از COMMAND_MAP واقعی + برچسبِ فارسی."""
    from aiogram.types import BotCommand
    import handlers
    keys = sorted(getattr(handlers, "COMMAND_MAP", {}) or {})
    return [BotCommand(command=k, description=LABELS.get(k, "🛰 " + k)[:48]) for k in keys if k][:40]


async def _try(bot, label, coro):
    try:
        await coro
        print(f"  ✓ {label}")
        return True
    except Exception as exc:                      # هر شکست نباید بقیه را متوقف کند
        print(f"  ✗ {label} — {type(exc).__name__}: {str(exc)[:110]}")
        return False


async def main(channel_id=None, group_id=None, skip_menu=False):
    from aiogram import Bot
    tok = config.BOT_TOKEN
    if not tok:
        sys.exit("❌ BOT_TOKEN نیست — در محیط یا فایل .env بگذار (python-dotenv).")
    bot = Bot(token=tok)
    try:
        me = await bot.get_me()
        print(f"🛰 بات: {me.first_name} · @{me.username} · id={me.id}\n")

        if not skip_menu:
            await _try(bot, f"منوی دستورات ({len(_cmds())} فرمان)", bot.set_my_commands(_cmds()))

        # ── ۱) هویتِ بات ──
        print("▸ بات")
        await _try(bot, "نام", bot.set_my_name(BOT["name"], language_code="fa"))
        await _try(bot, "نام (بدونِ زبانِ اختصاصی)", bot.set_my_name(BOT["name"]))
        await _try(bot, "بیوگرافی", bot.set_my_short_description(BOT["short"]))
        await _try(bot, "توضیحِ کامل", bot.set_my_description(BOT["full"]))

        # ── ۲) هویتِ کانال ──
        if channel_id:
            print("▸ کانال")
            await _try(bot, "عنوان", bot.set_chat_title(channel_id, CHANNEL["title"]))
            await _try(bot, "توضیح", bot.set_chat_description(channel_id, CHANNEL["desc"]))
            await _set_photo(bot, channel_id, AVATARS["channel"])

        # ── ۳) هویتِ گروه ──
        if group_id:
            print("▸ گروه")
            await _try(bot, "عنوان", bot.set_chat_title(group_id, GROUP["title"]))
            await _try(bot, "توضیح", bot.set_chat_description(group_id, GROUP["desc"]))
            await _set_photo(bot, group_id, AVATARS["group"])

        print("\n📎 یادآوری: عکس پروفایلِ بات را دستی آپلود کن — "
              f"{os.path.relpath(AVATARS['bot'], ROOT)}")
    finally:
        await bot.session.close()


async def _set_photo(bot, chat_id, path):
    from aiogram.types import FSInputFile
    if not os.path.exists(path):
        print(f"  ✗ عکس پیدا نشد: {path}")
        return
    await _try(bot, "عکس پروفایل", bot.set_chat_photo(chat_id, FSInputFile(path)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="ساختِ سه هویتِ متفاوتِ مانارچ (بات/کانال/گروه)")
    ap.add_argument("--channel", default=os.environ.get("CHANNEL_ID") or None,
                    help="شناسۀ عددی کانال (مثلاً -1004499194759)")
    ap.add_argument("--group", default=os.environ.get("GROUP_ID") or None,
                    help="شناسۀ عددی گروه (بات باید عضو و ادمین باشد)")
    ap.add_argument("--skip-menu", action="store_true", help="منوی دستورات را دست نزن")
    a = ap.parse_args()
    asyncio.run(main(a.channel, a.group, a.skip_menu))
