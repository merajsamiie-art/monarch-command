# ▶️ MONARCH COMMAND — نقطه‌ی شروع
import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import admin
import balance
import combat
import db
import emoji as EMJ
import events
import handlers
import titans as TN
from config import BOT_TOKEN

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("monarch")

COMMANDS = [
    ("start", "شروع / ورود به مانارچ"),
    ("me", "کارت عامل و وضعیت"),
    ("codex", "دیتابیس تایتان‌ها"),
    ("dossier", "پرونده‌ی کامل یک تایتان"),
    ("track", "ردیابی سیگنال لرزه‌ای"),
    ("sample", "نمونه‌برداری میدانی"),
    ("analyze", "شروع سیکل آزمایشگاه"),
    ("lab", "نتیجه‌ی آزمایشگاه"),
    ("bond", "پیوند با تایتان / ارتقای آن"),
    ("hunt", "شکار داوطلبانه"),
    ("fight", "ادامه‌ی نبرد فعال"),
    ("boss", "عملیات باس گروهی"),
    ("scan", "وضعیت منطقه"),
    ("raid", "رید جهانی"),
    ("explore", "اعزام تیم کاوش"),
    ("arena", "آرنای رتبه‌ای"),
    ("duel", "دوئل با عامل دیگر"),
    ("puzzle", "رمزنگاری مانارچ"),
    ("shop", "فروشگاه مانارچ"),
    ("inv", "کوله و تجهیزات"),
    ("equip", "مجهزکردن تجهیز"),
    ("upgrade", "ارتقای تجهیز"),
    ("market", "بازار منابع"),
    ("sell", "فروش منبع"),
    ("vault", "خزنه‌ی سازمان"),
    ("missions", "مأموریت‌های روزانه"),
    ("daily", "حضور روزانه"),
    ("div", "سازمان: ساخت / تسهیلات / جنگ"),
    ("bounty", "گرفتن جایزه برای سر یک عامل"),
    ("top", "رنکینگ"),
    ("clearance", "الزامات رتبه و دروازه‌ها"),
    ("rules", "قوانین نبرد"),
    ("help", "دستورنامه"),
    ("ref", "لینک معرفی"),
]


async def bootstrap_meta(bot: Bot):
    """یک‌بار در هر استارت: منوی دستورات + توضیح ربات."""
    try:
        await bot.set_my_commands([(c, d) for c, d in COMMANDS])
        await bot.set_my_commands([], scope=None)
        await bot.set_my_description(
            "🛰 مانارچ COMMAND — MMORPG گروهیِ دنیای Kaiju.\n"
            "همه با صفر شروع می‌کنند: ردیابی کن، نمونه بگیر، تحلیل کن، شکار کن، "
            "باس بزن، سازمان بساز و روزی با Godzilla روبه‌رو شو.\n"
            "🦖 THE TITANS ARE ALREADY HERE.")
        await bot.set_my_short_description(
            "☢️ MMORPG تایتان‌ها در تلگرام · ۲۴/۷ زنده · بدون Pay-to-Win")
        await bot.set_my_name("فرماندهی مانارچ")
    except Exception:
        log.exception("meta update failed")


async def main():
    assert BOT_TOKEN, "BOT_TOKEN تنظیم نشده (env یا .env)"
    db.init()
    EMJ.load()
    TN.load_overlays()
    if not balance.load_cache():
        log.info("⚖️ کش تعادل یافت نشد — کالیبراسیون…")
        balance.calibrate(quick=16)
        log.info("⚖️ %d تایتان کالیبره شد", len(balance.CAL))
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(handlers.router)
    dp.include_router(admin.router)
    handlers.reg_slash(dp)
    events.seed_admin_settings()
    await bootstrap_meta(bot)

    engine = events.Engine(bot, interval=560)
    engine.start()
    log.info("🛰 MONARCH COMMAND ONLINE · %d titan · %d abilities · %d bosses",
             len(TN.TITANS), len(__import__("abilities").ABILITIES), len(__import__("bosses").BOSSES))
    try:
        await dp.start_polling(bot, allowed_updates=["message", "callback_query", "my_chat_member"],
                               close_bot_session=True)
    finally:
        engine.stop()
        db.db().close()


if __name__ == "__main__":
    asyncio.run(main())
