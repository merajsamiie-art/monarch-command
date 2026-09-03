#!/usr/bin/env python3
"""📢 انتشارِ آموزش‌ها در کانال — سریِ «پروندۀ آموزشی مانارچ».

همۀ متن‌ها از خودِ بازی می‌آیند (texts.LESSONS / RULES / TITAN_CLASSIFIED) تا
کانال و ربات هیچ‌وقت دو حرفِ متفاوت نزنند. وضعیتِ انتشار در
``monarch/data/channel_posts.json`` می‌ماند، پس اجرای دوباره فقط چیزهای
نوشده را می‌فرستد (و ``--force`` همه را از نو می‌فرستد).

    BOT_TOKEN=xxxx python3 tools/post_channel.py --dry-run      # پیش‌نمایش
    BOT_TOKEN=xxxx python3 tools/post_channel.py --pin           # ارسال + پینِ شمارهٔ ۰۰۰
    BOT_TOKEN=xxxx python3 tools/post_channel.py --only 003      # یک پروندۀ خاص
    BOT_TOKEN=xxxx python3 tools/post_channel.py --force         # انتشارِ کاملِ سری

اگر کانال را عوض کنی، ``CHANNEL_ID`` (یا ``--channel``) را بده.
"""
import argparse
import asyncio
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: F401  → monarch/ را به sys.path اضافه می‌کند

import config           # noqa: E402
import texts            # noqa: E402
import ui               # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "monarch", "data", "channel_posts.json")

FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa_num(x) -> str:
    """رقمِ فارسی برای متنِ رواییِ کانال (کدهای پرونده لاتین می‌مانند)."""
    return str(x).translate(FA_DIGITS)


FAQ = [
    ("کِی می‌توانم گودزیلا را بگیرم؟",
     "وقتی پرونده‌اش کامل شود: سیگنال → مشاهده → نمونه → تحلیل → پیوند. "
     "هیچ خریدی این مسیر را کوتاه نمی‌کند؛ فقط زمان و انتخابِ درست."),
    ("گروهمان بازی را باز نمی‌کند؟",
     "مانارچ در گروه‌های کم‌عضو (زیر ۵ نفر) اجرا نمی‌شود. اعضای بیشتری دعوت کن، "
     "یا از گروه اصلیِ فرماندهی استفاده کن (آنجا بدونِ سقف فعال است)."),
    ("چرا ربات در پیوی جوابِ بازی نمی‌دهد؟",
     "همۀ بازی در گروه می‌چرخد — نبرد، کاوش، یورش و رنکینگ گروهی‌اند. "
     "در پیوی فقط دروازۀ ورود هست: «من را به گروه اضافه کن»."),
    ("باید ربات ادمین باشد؟",
     "برای نبرد نه؛ برای پروفایلِ گروه، پیام‌های رسمی و ویرایشِ فیدِ نبرد بله. "
     "حداقل «مدیریت پیام‌ها» و «تغییر اطلاعات» را بده."),
    ("اسپم کردن فایده دارد؟",
     "نه. سقفِ نرخ دارد، پیام‌ها ویرایش می‌شوند تا گروه شلوغ نشود، و "
     "کردارِ پیاپیِ بی‌برنامه آسیبِ کمتری می‌زند."),
    ("اگر بمیرم چه می‌شود؟",
     "۱۰ دقیقه حالتِ بازیابی، افتِ اعتبار و منابعِ محافظت‌نشده. "
     "هستۀ تایتان هرگز نمی‌افتد؛ خزانهٔ سازمان هم ریسک را کم می‌کند."),
    ("رتبه چطور بالا می‌رود؟",
     "تجربه از نبرد، پژوهش، کاوش و مأموریت روزانه. دروازه‌های رتبه با "
     "/clearance دیده می‌شوند."),
    ("پرداخت = بُرد؟",
     "خیر. هیچ فروشی تایتان یا بُرد نمی‌دهد؛ فقط ابزارِ لجستیکی. "
     "یک تایتانِ محدود با شرایطِ درست، سطحِ امگا را می‌اندازد."),
]

GROUP_RULES = (f"▪️ بازی فقط در گروه می‌چرخد — در پیوی فقط دروازۀ ورود است\n"
               f"▪️ گروه باید بیش از {fa_num(int(config.MIN_MEMBERS) - 1)} عضو داشته باشد\n"
               f"▪️ گروه اصلیِ فرماندهی بدونِ سقفِ عضو فعال است\n"
               f"▪️ من را به گروهت اضافه کن: https://t.me/{config.BOT_USER}?startgroup=true")


def _strip(t: str) -> str:
    return re.sub(r"<[^>]+>", "", t)


def lesson_card(idx: int, total: int, title: str, body: str) -> str:
    rows = [f"<i>{'تمرینِ میدانی' if idx % 2 else 'مرجعِ فرماندهی'}</i>", "",
            *[f" ▪️ {ln}" if ln.strip() else "" for ln in body.split("\n")],
            "", ui.chip(f"پروندۀ {fa_num(f'{idx:03d}')} از {fa_num(total)}", "🗂 ")]
    return ui.card(_strip(title), rows, sub="آموزشِ مانارچ", stamp="عمومی",
                   code=f"EDU-{idx:03d}", note="این پرونده در کانال بایگانی می‌شود.")


def faq_card() -> str:
    rows = []
    for q, a in FAQ:
        rows += [f"❓ <b>{q}</b>", f"▪️ {a}", ""]
    if rows:
        rows.pop()
    return ui.card("پرسش‌های مکررِ مانارچ", rows, sub="هشت پرسش، هشت پاسخ",
                   stamp="عمومی", code="EDU-FAQ",
                   note="هر پرسشِ تازه در گروه به فرماندهی گفته شود.")


def start_card() -> str:
    rows = [
        "🛰 <b>مانارچ یک جهانِ زنده است</b> — نه یک‌بار بازی، نه فروشِ قدرت.",
        "",
        ui.sect("سه حرکتِ اول"),
        " ۱. <code>/start</code> در گروه — پروندۀ پرسنلی‌ات باز می‌شود",
        " ۲. <code>/track</code> — نخستین سیگنال لرزه‌ای را بگیر",
        " ۳. <code>/analyze</code> — نمونه را به پروندۀ رسمی برسان",
        "",
        ui.sect("قواعدِ دروازۀ بازی"),
        GROUP_RULES,
        "",
        ui.sect("هر روز"),
        " <code>/daily</code> · <code>/missions</code> · سیگنالِ روزانه · "
        "سه‌شنبه و جمعه یورشِ جهانی",
    ]
    return ui.card("شروعِ سریع — پروندۀ ۰۰۰", rows, sub="اگر تازه آمده‌ای، از همین‌جا",
                   stamp="عمومی", code="EDU-000",
                   note="تایتان‌ها از قبل اینجا بودند.")


def series() -> list:
    """پرونده‌های کانال: (کلید، متن). ترتیب = ترتیبِ انتشار."""
    out = [("000-start", start_card())]
    n = len(texts.LESSONS)
    for i, l in enumerate(texts.LESSONS, 1):
        out.append((f"lesson-{i:02d}", lesson_card(i, n, l["title"], l["body"])))
    out += [
        ("protocol", ui.card("پروتکلِ نبرد", _strip(texts.RULES).split("\n"),
                            sub="قوانینی که بالانس روی آن‌ها ساخته شده", stamp="عمومی",
                            code="EDU-RULE", note="هر نبردی با این‌ها سنجیده می‌شود.")),
        ("titan-files", ui.card("دیتابیسِ مانارچ", _strip(texts.TITAN_CLASSIFIED).split("\n"),
                                  sub="چه چیزی هنوز باز نشده", stamp="محرمانه",
                                  code="EDU-DB", note=" ناشناخته‌ها را تو باید پیدا کنی.")),
        ("faq", faq_card()),
        ("manual", ui.card("دستورنامۀ کامل", _strip(texts.HELP).split("\n"),
                             sub="هر چیزی که می‌توانی بنویسی", stamp="عمومی",
                             code="EDU-HAND", note="دستورهای فارسی هم کار می‌کنند: «مانارچ من».")),
    ]
    return out


def load_state() -> dict:
    try:
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"posted": {}}


def save_state(st: dict) -> None:
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)


def audit(texts_: list) -> list:
    """هیچ واژۀ لاتینی جز دستورهای اسلش/لینک/کد نباید در کانال برود."""
    bad = []
    for key, t in texts_:
        body = re.sub(r"<[^>]+>", " ", t)
        body = re.sub(r"/[a-z_]{2,16}(?:[ \u200c]+[a-z_]{2,16})*", " ", body)
        body = re.sub(r"https?://\S+|t\.me/\S+", " ", body)
        body = re.sub(r"[A-Z][A-Z0-9.\-']{1,11}", " ", body)      # کدِ پرونده
        for w in re.findall(r"[A-Za-z][A-Za-z0-9_.\-']{2,}", body):
            bad.append(f"{key}:{w}")
    return bad


async def run(args) -> int:
    items = series()
    bad = audit(items)
    if bad:
        print("⚠️ واژۀ لاتین در متن‌ها:", ", ".join(sorted(set(bad))[:8]))
        if not args.allow_latin:
            print("   (با --allow-latin می‌توانی ردش کنی)")
    st = load_state()
    todo = [(k, t) for k, t in items if args.force or k not in st["posted"]]
    if args.only:
        todo = [(k, t) for k, t in todo if args.only in k]
    print(f"پرونده‌ها: {len(items)} · آمادهٔ انتشار: {len(todo)} · خشک: {'بله' if args.dry_run else 'نه'}")
    if args.dry_run:
        for k, t in todo:
            print("\n" + "━" * 24 + f"  {k}  ({len(t)} نویسه)" + "\n")
            print(t)
        return 0
    if not config.BOT_TOKEN:
        print("⛔️ BOT_TOKEN لازم است:  BOT_TOKEN=… python3 tools/post_channel.py")
        return 2
    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    chat = args.channel or config.CHANNEL_ID
    pinned = 0
    try:
        for k, t in todo:
            if len(t) > 4090:
                print(f"   ✂️ {k} بلند است ({len(t)}) — کوتاه می‌شود")
                t = t[:4087] + "…"
            try:
                m = await bot.send_message(chat, t, disable_web_page_preview=True)
            except Exception as e:
                print(f"   ❌ {k}: {str(e)[:120]}")
                continue
            st["posted"][k] = {"at": time.strftime("%Y-%m-%d %H:%M"), "id": m.message_id}
            save_state(st)
            print(f"   ✓ {k} → #{m.message_id}")
            if args.pin and pinned < args.pin_max and k.startswith("000"):
                try:
                    await bot.pin_chat_message(chat, m.message_id)
                    pinned += 1
                    print("   📌 پین شد")
                except Exception as e:
                    print("   ⚠️ پین:", str(e)[:80])
            await asyncio.sleep(args.spacing)
    finally:
        await bot.session.close()
    print("✅ پایانِ سری.")
    return 0


def main():
    ap = argparse.ArgumentParser(description="انتشارِ آموزش‌های مانارچ در کانال")
    ap.add_argument("--dry-run", action="store_true", help="فقط چاپ کن")
    ap.add_argument("--force", action="store_true", help="همه را دوباره بفرست")
    ap.add_argument("--only", default="", help="فقط پرونده‌هایی که کلیدشان این را دارد")
    ap.add_argument("--channel", type=int, default=0, help="شناسۀ کانال (پیش‌فرض: CHANNEL_ID)")
    ap.add_argument("--spacing", type=float, default=3.5, help="فاصلهٔ ثانیه‌ای بین پیام‌ها")
    ap.add_argument("--pin", action="store_true", help="پروندۀ ۰۰۰ را پین کن")
    ap.add_argument("--pin-max", type=int, default=1)
    ap.add_argument("--allow-latin", action="store_true")
    a = ap.parse_args()
    raise SystemExit(asyncio.run(run(a)))


if __name__ == "__main__":
    main()
