# 🛡 Admin Console — کنترل دنیای بازی (فقط ADMIN_IDS)
import random

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import balance
import bosses
import config
import db
import division
import emoji as EMJ
import events
import expedition
import kb
import player as PL
import raid as RA
import research
import titans as TN
import ui
from db import now

router = Router()


def is_admin(uid: int) -> bool:
    return config.is_admin(int(uid))


async def a(m: Message) -> bool:
    if not is_admin(m.from_user.id):
        await m.answer("🔒 <b>ACCESS DENIED</b>\n<code>MONARCH SECURITY</code> — این پرونده برای تو نیست.")
        return False
    return True


@router.message(Command("ad"))
async def panel(m: Message):
    if not await a(m):
        return
    d = db.db()
    stats = dict(
        players=d.one("SELECT COUNT(*) c FROM players")["c"],
        live=d.one("SELECT COUNT(*) c FROM combats WHERE status='live'")["c"],
        raids=d.one("SELECT COUNT(*) c FROM raids")["c"],
        divs=d.one("SELECT COUNT(*) c FROM divisions")["c"],
        bonds=d.one("SELECT COUNT(*) c FROM bonds WHERE stage>=5")["c"],
        chats=d.one("SELECT COUNT(*) c FROM chats WHERE kind='group'")["c"],
    )
    txt = (f"🛡 <b>MONARCH COMMAND — CONTROL</b>\n▬▬▬▬▬▬▬▬▬▬▬▬\n"
           f"▪️ بازیکنان: <b>{stats['players']}</b> · چت‌های فعال: <b>{stats['chats']}</b>\n"
           f"▪️ نبردهای زنده: <b>{stats['live']}</b> · پیوندهای فعال: <b>{stats['bonds']}</b>\n"
           f"▪️ Division‌ها: <b>{stats['divs']}</b> · ریدها: <b>{stats['raids']}</b>\n"
           f"▪️ ساعت: {db.local_now().strftime('%H:%M')} تهران · چهارشنبه/جمعه رید\n"
           f"▪️ تعادل: {len(balance.CAL or {})}/{len(TN.TITANS)} تایتان کالیبره\n"
           f"▪️ ایموجی سفارشی: {'✅ فعال' if EMJ.has_custom() else '⬪ یونیکد'}")
    rows = [[("adm:spawn", "🕹 اسپاون باس"), ("adm:zone", "🌍 منطقه")],
            [("adm:raid", "🌒 شروع رید"), ("adm:war", "⚔️ جنگ Division")],
            [("adm:audit", "⚖️ ممیزی تعادل"), ("adm:news", "📰 فید گروه‌ها")],
            [("adm:bcast", "📢 پخش کانال"), ("adm:wipe", "🧹 بسته‌نبرد ها")]]
    await m.answer(txt, reply_markup=kb.kb(rows))


@router.callback_query(F.data.startswith("adm:"))
async def cb(c: CallbackQuery):
    if not is_admin(c.from_user.id):
        await c.answer("denied", show_alert=True)
        return
    key = c.data.split(":")[1]
    if key == "spawn":
        chats = events.active_chats(6)
        out = []
        for ch in chats:
            r = bosses.spawn(ch["chat_id"], force=True)
            if r.get("ok"):
                out.append(f"{ch['chat_id']}: {bosses.by_id(r['bid'])['name']}")
        await c.answer("اسپاون: " + (" | ".join(out) if out else "چت فعالی نیست"), show_alert=True)
    elif key == "zone":
        zones = list(TN.ENVS.keys())
        rows = [[(f"az:{z}", TN.ENVS[z])] for z in zones]
        try:
            await c.message.edit_text('🌍 منطقه\u200cی چت فعلی را انتخاب کن:', reply_markup=kb.kb(rows + [[('adm:close', '✖️')]]))
        except Exception as ez:
            await c.answer(str(ez)[:150], show_alert=True)
    elif key == "raid":
        r = RA.start()
        await c.answer("رید شروع شد" if r.get("ok") else "❔", show_alert=True)
    elif key == "war":
        divs = db.db().q("SELECT id FROM divisions ORDER BY xp DESC LIMIT 4")
        pairs = [dict(a=divs[i]["id"], b=divs[i + 1]["id"], focus={}) for i in range(0, len(divs) - 1, 2)]
        division.war_start(pairs, hours=6) if pairs else None
        await c.answer(f"جنگ با {len(pairs)} جفت شروع شد" if pairs else "Division کافی نیست", show_alert=True)
    elif key == "audit":
        r = balance.audit(trials=18)
        lines = [f"⚖️ <b>BALANCE AUDIT</b> · span {r['span']}× · {r['calibrated']}/{r['n']} کالیبره",
                 ui.divider()]
        for row in r["rows"][:14]:
            lines.append(f"▪️ {row['name'][:16]:<17}{row['rar'][:9]:<10} "
                         f"smart <code>{row['smart']:.2f}</code> spam <code>{row['spam']:.2f}</code> "
                         f"under <code>{row['underleveled']:.2f}</code>")
        lines += ["", "<b>PROBLEMS</b>: " + ("<i>none</i>" if not r["problems"] else "")]
        lines += [f"▪️ {p}" for p in r["problems"][:12]]
        try:
            await c.message.edit_text("\n".join(lines)[:3900])
        except Exception:
            await c.message.answer("\n".join(lines)[:3900])
    elif key == "news":
        for ch in events.active_chats(8):
            db.db().ex("UPDATE chats SET last_news=0 WHERE chat_id=?", (ch["chat_id"],))
        await c.answer("فید گروه‌ها برای چرخه‌ی بعد صف شد", show_alert=True)
    elif key == "wipe":
        n = combat_gc()
        await c.answer(f"{n} نبرد رهاشده بسته شد", show_alert=True)
    elif key == "close":
        try:
            await c.message.edit_reply_markup(None)
        except Exception:
            pass
    await c.answer()


@router.callback_query(F.data.startswith("az:"))
async def cb_zone(c: CallbackQuery):
    if not is_admin(c.from_user.id):
        return
    z = c.data.split(":")[1]
    events.ensure_chat(c.message.chat.id)
    events.set_zone(c.message.chat.id, z)
    await c.answer(f"منطقه → {TN.ENVS.get(z, z)}", show_alert=True)


def combat_gc():
    import combat
    return combat.gc()


# ─────────── دستورهای متنی ادمین ───────────
@router.message(Command("spawn"))
async def spawn(m: Message):
    if not await a(m):
        return
    arg = (m.text or "").split(maxsplit=1)
    bid = arg[1].strip() if len(arg) > 1 else None
    r = bosses.spawn(m.chat.id, bid, force=True)
    await m.answer(r.get("text") or r.get("msg") or "❔")


@router.message(Command("setzone"))
async def setzone(m: Message):
    if not await a(m):
        return
    z = (m.text or "").split()[-1]
    ok = events.set_zone(m.chat.id, z)
    await m.answer(f"🌍 منطقه: {TN.ENVS.get(z, '❔')}" if ok else "❔ منطقه نامعتبر — " + "، ".join(TN.ENVS))


@router.message(Command("setrank"))
async def setrank(m: Message):
    if not await a(m):
        return
    parts = (m.text or "").split()
    uid = m.reply_to_message.from_user.id if (m.reply_to_message and m.reply_to_message.from_user) else None
    rank = None
    for p_ in parts[1:]:
        dg = "".join(ch for ch in p_ if ch.isdigit())
        if dg and uid is None:
            uid = int(dg)
        elif dg:
            rank = int(dg)
    if not uid or not rank:
        await m.answer("🎖 <code>/setrank &lt;id&gt; &lt;rank&gt;</code> یا Reply")
        return
    PL.set_row(uid, rank=max(1, min(40, rank)))
    await m.answer(f"🎖 {PL.name_of(uid)} → Rank {rank}")


@router.message(Command("give"))
async def give(m: Message):
    if not await a(m):
        return
    parts = (m.text or "").split()
    if len(parts) < 3:
        await m.answer("🎁 <code>/give &lt;id&gt; credits 5000</code> · منابع: " + "|".join(economy_keys()))
        return
    uid = int("".join(ch for ch in parts[1] if ch.isdigit()) or 0)
    res = parts[2]
    amt = float("".join(ch for ch in (parts[3] if len(parts) > 3 else "1") if (ch.isdigit() or ch == ".")) or 1)
    PL.add_res(uid, **{res: amt})
    await m.answer(f"🎁 {res} +{amt:g} → {PL.name_of(uid)}")


def economy_keys():
    import economy
    return list(economy.RES.keys())


@router.message(Command("stage"))
async def stage(m: Message):
    if not await a(m):
        return
    parts = (m.text or "").split()
    if len(parts) < 3:
        await m.answer("🔬 <code>/stage &lt;id&gt; &lt;titan&gt; &lt;0-5&gt;</code>")
        return
    uid = int("".join(ch for ch in parts[1] if ch.isdigit()))
    research.set_stage(uid, parts[2], int(parts[3]) if len(parts) > 3 else 4)
    await m.answer(f"🔬 stage={parts[3] if len(parts) > 3 else 4} برای {parts[2]}")


@router.message(Command("bcast"))
async def bcast(m: Message):
    if not await a(m):
        return
    txt = (m.text or "").split(maxsplit=1)
    if len(txt) < 2:
        await m.answer("📢 <code>/bcast متن</code> — به کانال رسمی")
        return
    if not config.CHANNEL_ID:
        await m.answer("🔒 CHANNEL_ID تنظیم نشده")
        return
    try:
        await m.bot.send_message(config.CHANNEL_ID, txt[1])
        await m.answer("✅ پخش شد")
    except Exception as e:
        await m.answer(f"❌ {e}")


@router.message(Command("calibrate"))
async def calibrate(m: Message):
    if not await a(m):
        return
    await m.answer("⚖️ کالیبراسیون مجدد تعادل… (۱۰ تا ۶۰ ثانیه)")
    r = balance.calibrate(force=True, quick=22)
    a_ = balance.audit(trials=18)
    await m.answer(f"✅ {len(r)} تایتان کالیبره · مشکلات: {len(a_['problems'])}\n"
                   + "\n".join(a_["problems"][:8]))
