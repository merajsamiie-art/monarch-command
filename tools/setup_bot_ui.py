#!/usr/bin/env python3
"""🪪 یکسان‌سازی هویت: دستورات منو، نام/بیو/توضیح بات، عکس و توضیح کانال/گروه.

    python3 tools/setup_bot_ui.py                              # منو + نام + بیو + توضیح
    python3 tools/setup_bot_ui.py --channel -1004499194759     # + عکس/عنوان/توضیح کانال
    python3 tools/setup_bot_ui.py --group -100… --channel -100…

نکته: تلگرام API برای **عکس پروفایل بات** متد ندارد — فایل `assets/bot_avatar.jpg`
را از حسابِ مالکِ بات (یا هر راهِ دستی) آپلود کن. عکس کانال/گروه را همین‌جا ست می‌کند
(به‌شرط ادمین‌بودن بات با مجوز «تغییر اطلاعات»).
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: F401

import config  # noqa: E402
import handlers  # noqa: E402

AVATARS = {"bot": "assets/bot_avatar.jpg", "channel": "assets/channel_avatar.jpg",
           "group": "assets/group_avatar.jpg"}


def _cmds():
    """منوی /commands — از COMMAND_MAP واقعی، تا منو هیچ‌وقت با کد نخواند."""
    from aiogram.types import BotCommand
    out, seen = [], set()
    for name, (fn, _takes) in handlers.COMMAND_MAP.items():
        if name in seen:
            continue
        seen.add(name)
        doc = (fn.__doc__ or "").strip().split("\n")[0]
        out.append(BotCommand(command=name, description=(doc or name)[:48]))
    return out[:37]


async def _try(bot, label, coro):
    try:
        await coro
        print(f"✔ {label}")
        return True
    except Exception as e:
        print(f"⚠️ {label}: {str(e)[:130]}")
        return False


async def main(a):
    from aiogram import Bot
    from aiogram.types import FSInputFile
    bot = Bot(token=config.BOT_TOKEN)
    me = await bot.get_me()
    print(f"🤖 {me.full_name} · @{me.username} · id={me.id}")
    await _try(bot, f"منوی /commands ({len(_cmds())} مورد)", bot.set_my_commands(_cmds()))
    await _try(bot, "نام بات", bot.set_my_name(name=f"🦖☢️ {config.BRAND}"))
    await _try(bot, "بیوی کوتاه", bot.set_my_short_description(
        getattr(config, "TAGLINE", "🦖☢️ MONARCH COMMAND")[:120]))
    await _try(bot, "توضیح بات", bot.set_my_description(
        f"🦖☢️ {config.BRAND} — بازی نوردی/استراتژیک گروهی تلگرام: شکار تایتان‌های canon، "
        f"پرونده‌های طبقه‌بندی‌شده، تقسیم‌ها و باس‌های جهانی.\n"
        f"📖 آموزش و اخبار: {config.CHANNEL_URL}\n"
        f"🛰 گروه عملیات: {config.GROUP_URL}\n"
        f"▸ برای شروع: /start"))
    for who, chat_id in (("channel", a.channel), ("group", a.group)):
        if not chat_id:
            continue
        cid = int(chat_id)
        fp = os.path.join(_path.ROOT, AVATARS[who])
        if os.path.exists(fp):
            await _try(bot, f"عکس {who}", bot.set_chat_photo(chat_id=cid, photo=FSInputFile(fp)))
        else:
            print(f"— {AVATARS[who]} پیدا نشد")
        if who == "channel":
            await _try(bot, "عنوان کانال", bot.set_chat_title(
                chat_id=cid, title=f"🦖☢️ {config.BRAND} · ARCHIVE"))
            await _try(bot, "توضیح کانال", bot.set_chat_description(
                chat_id=cid, description=f"آرشیو پرونده‌ها، آموزش، اخبار باس‌ها و رویدادهای {config.BRAND}."))
        else:
            from aiogram.types import MenuButtonCommands
            await _try(bot, "دکمه‌ی منوی گروه", bot.set_chat_menu_button(
                chat_id=cid, menu_button=MenuButtonCommands()))
    print("— عکس پروفایل بات: دستی آپلود شود →", AVATARS["bot"])
    await bot.session.close()
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default="")
    ap.add_argument("--channel", default="")
    sys.exit(asyncio.run(main(ap.parse_args())))
