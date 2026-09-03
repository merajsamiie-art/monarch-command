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

COMMANDS = [            # منویِ اسلش در گروه — خلوت: هرچیزِ لازم، نه همه‌چیز
    ("start", "ورود به فصلِ جاری"),
    ("menu", "تابلوی فرماندهی"),
    ("me", "کارتِ عامل"),
    ("codex", "دیتابیسِ تایتان‌ها"),
    ("track", "ردیابیِ سیگنال"),
    ("hunt", "شکارِ داوطلبانه"),
    ("fight", "ادامۀ نبرد"),
    ("boss", "عملیات باس"),
    ("raid", "یورشِ جهانی"),
    ("explore", "تیمِ کاوش"),
    ("shop", "تأمینات"),
    ("missions", "مأموریتِ روزانه"),
    ("top", "رتبۀ هفتگی"),
    ("help", "دستورنامه"),
]

PV_COMMANDS = [         # پیوی فقط دروازہ است: سه چیز، نه بیشتر
    ("start", "من را به گروه اضافه کن"),
    ("help", "دستورنامۀ فرماندهی"),
    ("join", "گروه و کانالِ مانارچ"),
]


def _cmds(pairs):
    from aiogram.types import BotCommand
    return [BotCommand(command=c, description=d) for c, d in pairs]


async def bootstrap_meta(bot: Bot):
    """یک‌بار در هر استارت: منوی اسلش (گروه/پیوی) + هویتِ فارسیِ بات."""
    from aiogram.types import BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats
    try:
        await bot.set_my_commands(_cmds(COMMANDS))
        await bot.set_my_commands(_cmds(COMMANDS), scope=BotCommandScopeAllGroupChats())
        await bot.set_my_commands(_cmds(PV_COMMANDS), scope=BotCommandScopeAllPrivateChats())
        await bot.set_my_name("🦖☢️ فرماندۀ مانارچ")
        await bot.set_my_short_description(
            "نبردهای تایتان در تلگرام — جهانِ زندهٔ ۲۴ ساعته، بدونِ خریدِ بُرد.")
        await bot.set_my_description(
            "🛰 مانارچ — پروندۀ زندهٔ تایتان‌ها\n"
            "همه از صفر شروع می‌کنند: سیگنال بگیر، نمونه بردار، تحلیل کن، شکار کن،"
            " باس بزن، سازمان بساز و روزی روبه‌روی گودزیلا بایست.\n"
            "▪️ بازی فقط در گروه می‌چرخد — من را به گروهت اضافه کن.\n"
            "▪️ آموزش‌ها و پرونده‌ها در کانالِ فرماندهی.\n"
            "🦖 تایتان‌ها از قبل اینجا بودند.")
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
