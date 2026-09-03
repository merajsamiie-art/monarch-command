#!/usr/bin/env python3
"""🪪 یکسان‌سازی هویت: دستورات منو، توضیح/بیو، عکس پروفایل بات، دکمه‌ی منوی گروه، کپشن کانال.

    python3 tools/setup_bot_ui.py                 # منو + بیو + توضیح
    python3 tools/setup_bot_ui.py --photos        # + ست کردن عکس پروفایل (assets/bot_avatar.jpg)
    python3 tools/setup_bot_ui.py --group -100…   # + منوی گروه (SetChatMenuButton)

اگر بات در گروه/کانال ادمین نباشد، آن بخش با هشدار رد می‌شود (ربات نمی‌تواند خودش را ادمین کند).
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: F401

import config  # noqa: E402
import handlers  # noqa: E402


def _cmds():
    from aiogram.types import BotCommand
    out = []
    for name in ("start", "me", "hunt", "boss", "raid", "arena", "codex", "track",
                 "explore", "shop", "inv", "missions", "div", "top", "rules", "help"):
        if name in handlers.COMMAND_MAP:
            doc = (handlers.COMMAND_MAP[name][0].__doc__ or name).strip().split("\n")[0][:44]
            out.append(BotCommand(command=name, description=doc or name))
    return out[:37]


async def main(a):
    from aiogram import Bot
    import emoji
    bot = Bot(token=config.BOT_TOKEN)
    me = await bot.get_me()
    print(f"🤖 {me.full_name} · @{me.username}")
    await bot.set_my_commands(_cmds())
    await bot.set_my_short_description(config.TAGLINE[:120])
    await bot.set_my_description(
        f"🦖☢️ {config.BRAND} — بازیِ نوردی/استراتژیک تلگرام: شکار تایتان‌ها، پرونده‌های "
        f"محرمانه، سازمان‌ها و باس‌های جهانی.\n"
        f"📖 آموزش و اخبار: {config.CHANNEL_URL}\n"
        f"🛰 گروه عملیات: {config.GROUP_URL}\n"
        f"▸ برای شروع: /start")
    print("✔ منو، بیو و توضیح ست شد")
    if a.photos:
        for p in ("assets/bot_avatar.jpg", "assets/channel_avatar.jpg", "assets/group_avatar.jpg"):
            fp = os.path.join(_path.ROOT, p)
            print(f"{'✔' if os.path.exists(fp) else '—'} {p} {'ست شد' if os.path.exists(fp) else 'پیدا نشد'}")
        av = os.path.join(_path.ROOT, "assets", "bot_avatar.jpg")
        if os.path.exists(av):
            from aiogram.types import InputFile
            await bot.set_my_photo(photo=InputFile(av))
            print("✔ عکس پروفایل بات")
    if a.group:
        from aiogram.types import BotCommand, InputFile
        try:
            await bot.set_chat_menu_button(chat_id=int(a.group),
                                            menu_button=BotCommand)
            print(f"✔ دکمه‌ی منوی گروه {a.group}")
        except Exception as e:
            print(f"⚠️ منوی گروه: {str(e)[:120]}")
        av = os.path.join(_path.ROOT, "assets", "group_avatar.jpg")
        if os.path.exists(av) and a.photos:
            try:
                await bot.set_chat_photo(chat_id=int(a.group), photo=InputFile(av))
                print("✔ عکس گروه")
            except Exception as e:
                print(f"⚠️ عکس گروه: {str(e)[:120]}")
    if a.channel:
        av = os.path.join(_path.ROOT, "assets", "channel_avatar.jpg")
        try:
            if os.path.exists(av):
                from aiogram.types import InputFile
                await bot.set_chat_photo(chat_id=int(a.channel), photo=InputFile(av))
            await bot.set_chat_description(chat_id=int(a.channel),
                                           description=f"🦖☢️ {config.BRAND} — آرشیو پرونده‌ها، آموزش، اخبار باس‌ها.")
            await bot.set_chat_title(chat_id=int(a.channel),
                                      title=f"🦖☢️ {config.BRAND} · ARCHIVE")
            print(f"✔ کانال {a.channel} هویت‌دار شد")
        except Exception as e:
            print(f"⚠️ کانال: {str(e)[:140]}")
    await bot.session.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--photos", action="store_true")
    ap.add_argument("--group", default="")
    ap.add_argument("--channel", default="")
    asyncio.run(main(ap.parse_args()))
