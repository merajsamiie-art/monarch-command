# 🎮 Handlers — aiogram 3 | اسلش + پیشوند فارسی «مانارچ» + دکمه‌ها
import asyncio
import logging
import random
import time

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardButton as B, Message

import abilities as AB
import arena
import balance
import bosses
import combat
import config
import db
import division
import economy
import events
import expedition
import kb
import player as PL
import raid as RA
import research
import texts
import titans as TN
import ui
from db import now

log = logging.getLogger("monarch.handlers")
router = Router()

ALIASES = {
    "me": ["من", "status", "پروفایل"], "codex": ["databank", "دیتابیس", "titan"],
    "dossier": ["پرونده", "file"], "track": ["ردیابی", "signal"],
    "sample": ["نمونه"], "analyze": ["تحلیل"], "lab": ["آزمایشگاه"],
    "bond": ["پیوند"], "puzzle": ["پازل", "رمز"], "hunt": ["شکار"],
    "fight": ["جنگ", "نبرد"], "boss": ["باس"], "raid": ["رید"],
    "arena": ["آرنا"], "duel": ["دوئل"], "explore": ["کاوش", "expedition"],
    "shop": ["فروشگاه"], "inv": ["کوله", "inventory"], "equip": ["مجهز"],
    "market": ["بازار"], "sell": ["فروش"], "vault": ["خزنه"],
    "missions": ["مأموریت", "mission"], "daily": ["روزانه", "checkin"],
    "top": ["رنکینگ", "rank", "لدر"], "div": ["سازمان", "division"],
    "scan": ["اسکن", "منطقه"], "bounty": ["جایزه", "bod"],
    "help": ["راهنما", "commands"], "rules": ["قوانین"], "clearance": ["رتبه"],
    "use": ["مصرف"], "upgrade": ["ارتقا"],
}

_MEM_CACHE = {}          # uid -> (ok, ts)
_FEED = {}               # chat_id -> message_id of live combat feed
_THROTTLE = {}           # uid -> [ts, ...] penalties
_BURST = {}              # uid -> [ts, ...] سقفِ انفجارِ بی‌صدا
_CARD_SEEN = {}          # (uid, tid) -> ts : کارت تصویری یک‌بار


# ─────────── helpers ───────────
def _chat_id_of(m) -> int:
    """chat_id از Message یا CallbackQuery (هر دو مسیر نبرد را داریم)."""
    if isinstance(m, Message):
        return int(m.chat.id)
    msg = getattr(m, "message", None)
    return int(msg.chat.id) if msg and getattr(msg, "chat", None) else int(config.PUBLIC_CHAT_ID or 0)


async def reply(m, text: str, markup=None, feed=False, cid=None, photo=None):
    """پاسخ MONARCH؛ اگر `photo` داده شود و تازه‌سازی لازم باشد، کارت تصویری می‌فرستد.

    فیدِ نبرد هرگز عکس نمی‌فرستد (ضداسپم) — فقط پیام‌های «یک‌بار‌دیدنی» مثل پرونده.
    """
    if photo and not feed:
        tgt = m if isinstance(m, Message) else m.message
        try:
            src = photo
            if isinstance(photo, str) and not photo.startswith("http"):
                from aiogram.types import InputFile
                src = InputFile(photo)
            elif isinstance(photo, str) and photo.startswith("http"):
                pass                      # تلگرام خودش URL را می‌گیرد
            return await tgt.answer_photo(src, caption=text[:1024], reply_markup=markup)
        except Exception as e:
            log.debug("photo card failed (%s) — text fallback", str(e)[:80])
    try:
        if feed and cid:
            key = _chat_id_of(m)
            mid = _FEED.get(key)
            if not mid:
                row = db.db().one("SELECT msg_id FROM combats WHERE id=?", (int(cid),))
                mid = (row or {}).get("msg_id")
            if mid:
                try:
                    await m.bot.edit_message_text(text=text, chat_id=key, message_id=int(mid),
                                                  reply_markup=markup)
                    return
                except Exception:
                    _FEED.pop(key, None)     # پیام قدیمی نمی‌رسد → از نو ارسال می‌شود
        sent = await (m.answer(text, reply_markup=markup) if isinstance(m, Message)
                      else m.message.answer(text, reply_markup=markup))
        if feed and sent and cid:
            _FEED[_chat_id_of(m)] = sent.message_id
            db.db().ex("UPDATE combats SET msg_id=? WHERE id=?", (sent.message_id, int(cid)))
        return sent
    except TelegramForbiddenError:
        return None
    except TelegramBadRequest as e:
        log.warning("bad request: %s", str(e)[:160])
        return await (m.answer("⚠️ SYSTEM: پیام کوتاه‌تر شد — خطای فرمت.", ) if isinstance(m, Message) else None)


async def _ans(c: CallbackQuery, text: str, markup=None, show_alert=False):
    try:
        await c.answer(text[:200], show_alert=show_alert)
    except Exception:
        pass


def name_of(m: Message) -> str:
    u = m.from_user
    return (u.full_name if u and u.full_name else f"AGENT{u.id}")[:48]


def chat_of(m: Message) -> dict:
    cid = m.chat.id
    kind = "group" if str(cid).startswith("-100") or m.chat.type in ("group", "supergroup") else "private"
    events.ensure_chat(cid, m.chat.title or "PRIVATE", kind)
    row = db.db().one("SELECT * FROM chats WHERE chat_id=?", (int(cid),)) or {}
    row["chat_id"] = int(cid)
    return row


def guard(m: Message) -> dict:
    """ثبت بازیکن + تیک + فعال‌سازی چت. برگرداندن ردیف بازیکن."""
    p = PL.ensure_player(m.from_user.id, name_of(m), m.from_user.username)
    PL.tick(m.from_user.id)
    PL.note_chat(m.from_user.id, m.chat.id)
    p = PL.get(m.from_user.id)
    if p and p.get("lab_titan") and float(p.get("lab_until") or 0) and float(p["lab_until"]) <= now():
        r = research.lab_check(m.from_user.id)
        if r.get("msg"):
            asyncio.create_task(reply(m, r["msg"]))
    return p or {}


# ─────────── گیت کانال + ضداسپم ───────────
async def member_ok(bot: Bot, uid: int) -> bool:
    if not config.REQUIRE_CHANNEL or config.is_admin(uid) or not config.CHANNEL_ID:
        return True
    hit = _MEM_CACHE.get(uid)
    if hit and now() - hit[1] < config.MEMBERSHIP_CACHE:
        return hit[0]
    ok = False
    try:
        mem = await bot.get_chat_member(config.CHANNEL_ID, uid)
        ok = (mem.status or "").lower() in ("member", "administrator", "creator")
    except TelegramForbiddenError:
        ok = True                      # ربات از کانال بیرون انداخته شده → گیت را نمی‌بندیم
    except Exception:
        ok = True
    _MEM_CACHE[uid] = (ok, now())
    return ok


def spam_ok(uid: int) -> tuple:
    """Rate limit پلکانی: پنجره ۱۲ ثانیه، بیشتر از ۹ دستور → جریمه."""
    t = time.time()
    q = [x for x in _THROTTLE.get(uid, []) if t - x < config.SPAM_WINDOW + config.SPAM_DECAY]
    recent = [x for x in q if t - x < config.SPAM_WINDOW]
    if len(recent) > config.SPAM_MAX:
        n = max(0, len(recent) - config.SPAM_MAX)
        wait = min(config.SPAM_PENALTY_MAX, config.SPAM_PENALTY * (1.6 ** n))
        _THROTTLE[uid] = q
        return False, wait
    q.append(t)
    _THROTTLE[uid] = q[-40:]
    return True, 0


_SPAM_WARN = {}          # uid -> ts : فقط یک هشدار در هر دقیقه (ضداسپمِ خودِ ربات)


async def gate(m: Message, admin_ok: bool = True) -> bool:
    uid = m.from_user.id
    ok, wait = spam_ok(uid)
    if not ok:
        t = now()
        if t - float(_SPAM_WARN.get(uid) or 0) > 60:
            _SPAM_WARN[uid] = t
            await reply(m, f"⏳ <b>RATE LIMIT</b> — {wait:.0f} ثانیه صبر کن؛ "
                           f"MONARCH از اسپم خوشش نمی‌آید.")
        return False
    if config.REQUIRE_CHANNEL and not await member_ok(m.bot, uid):
        await reply(m, texts.NO_CLEARANCE.format(channel=config.CHANNEL_URL),
                    kb.kb([[(config.CHANNEL_URL, "📢 عضویت در کانال")]]))
        return False
    return True


# ═══════════════ شروع / راهنما ═══════════════
@router.message(CommandStart())
async def cmd_start(m: Message, command: CommandObject = None):
    uid = m.from_user.id
    PL.ensure_player(uid, name_of(m), m.from_user.username)
    PL.tick(uid)
    PL.note_chat(uid, m.chat.id)
    chat = chat_of(m)
    if not await member_ok(m.bot, uid) and config.REQUIRE_CHANNEL:
        await reply(m, texts.NO_CLEARANCE.format(channel=config.CHANNEL_URL),
                    kb.kb([[(config.CHANNEL_URL, "📢 عضویت در کانال")]]))
        return
    ref = (command.args or "").strip()
    p = PL.get(uid)
    fresh = now() - float(p.get("created_at") or 0) < 20
    if ref.startswith("ref:") and fresh:
        try:
            inv = int(ref.split(":")[1])
            if inv != uid and float(p.get("xp") or 0) == 0:
                PL.add_res(inv, credits=300, fdata=1)
                PL.add_res(uid, credits=150)
                PL.add_xp(inv, 8)
                await reply(m, f"🤝 <b>RECRUIT LINKED</b> — {PL.name_of(inv)} تو را معرفی کرد؛ "
                               f"🪙 +۱۵۰ MC · 📡 +۱ داده")
        except (ValueError, IndexError):
            pass
    if not fresh:
        act = combat.active_of(uid)
        await reply(m, f"🛰 <b>WELCOME BACK</b> — {p['name']}\n"
                       f"🎖 {PL.rank_label(p)} · ❤️ {ui.n(p['hp'])}/{ui.n(p['max_hp'])} · "
                       f"🔋 {ui.n(p['energy'])}\n"
                       + (f"⚔️ درگیری فعال داری: <code>/fight</code>" if act else "✅ وضعیت پایدار"),
                    kb.main_menu(p, has_combat=bool(act)))
        return
    await reply(m, texts.START.format(name=p["name"]), kb.main_menu(p))
    if m.chat.type in ("group", "supergroup"):
        await reply(m, texts.WELCOME_GROUP.format(zone=TN.ENVS.get(chat.get("zone"), "—"),
                                                  danger=chat.get("danger", 1)))


@router.message(Command("help"))
async def cmd_help(m: Message):
    await reply(m, texts.HELP, kb.kb([[("rules", "⚖️ قوانین نبرد"), ("menu:main", "🛰 منو")]]))


@router.message(Command("rules"))
async def cmd_rules(m: Message):
    await reply(m, texts.RULES)


async def cmd_join(m: Message):
    await reply(m, f"👥 <b>MONARCH OPS GROUP</b>\n{config.GROUP_URL}\n\n"
                   f"📢 <b>کانال آموزشی</b>\n{config.CHANNEL_URL}")


# ═══════════════ پرونده و پیشرفت ═══════════════
@router.message(Command("me"))
async def cmd_me(m: Message):
    p = guard(m)
    if not p:
        return
    if PL.is_dead(p):
        left = PL.dead_left(p)
        await reply(m, texts.DEAD.format(left=f"{left/60:.1f}", drop="▪️ پس از احیا محاسبه می‌شود"))
        return
    extra = []
    stx = expedition.status(m.from_user.id)
    if stx.get("active"):
        extra.append(f"🗺 کاوش فعال: {TN.ENVS.get(expedition.ZONES.get(stx['zone'], {}).get('env'), stx['zone'])} · {ui.dur(stx['left'])}")
    if stx.get("ready"):
        extra.append("📦 کاوش آماده‌ی تحویل است — /explore claim")
    if p.get("lab_titan"):
        extra.append(f"🔬 آزمایشگاه: {p['lab_titan']} · {ui.eta(float(p['lab_until']))}")
    act = combat.active_of(m.from_user.id)
    if act:
        extra.append(f"⚔️ نبرد فعال: <code>/fight</code> (پرونده {act['row']['id']})")
    txt = PL.card(p)
    if extra:
        txt += "\n\n" + "\n".join(extra)
    await reply(m, txt, kb.kb([[("menu:codex", "🦖 دیتابیس"), ("menu:missions", "📅 روزانه")],
                              [("menu:shop", "🪙 فروشگاه"), ("menu:div", "🏢 Division")]]))


@router.message(Command("clearance"))
async def cmd_clearance(m: Message):
    p = guard(m)
    rank = int(p.get("rank") or 1)
    lines = [f"🎖 <b>CLEARANCE FILE</b> — {p['name']}",
             f"رتبه‌ی فعلی: <b>{PL.rank_label(p)}</b> <code>(Rank {rank})</code>",
             f"✨ {ui.bar(float(p.get('xp') or 0), balance.xp_need(rank), 14)} "
             f"<i>{ui.n(p.get('xp'))}/{ui.n(balance.xp_need(rank))} XP</i>", "", "🪜 <b>نردبان دسترسی</b>"]
    for k, r in balance.RANKS.items():
        done = "✅" if rank >= r["need"] else "🔒"
        lines.append(f"{done} {r['emj']} {r['name']} — رنک <code>{r['need']}</code>")
    lines += ["", "🔓 <b>دروازه‌ی کشف تایتان</b>"]
    for rar, g in balance.GATE.items():
        lines.append(f"▪️ {rar:<10} رنک {g['rank']} · 🧬{g['dna']} · 💎{g['cores']} · 📡{g['fdata']} · ⚔️{g['kills']} kill")
    await reply(m, "\n".join(lines))


@router.message(Command("top"))
async def cmd_top(m: Message, command: CommandObject = None):
    guard(m)
    mode = (command.args or "power").split()[0]
    rows = PL.leaderboard(mode, 12)
    ttl = dict(power="🏆 قدرت رزمی", xp="✨ تجربه", boss="🕹 باس‌کُش", raid="🌍 رید",
               kills="⚔️ شکار", arena="🏆 آرنا", research="🔬 پژوهش", deaths="☠️ مرگ").get(mode, "🏆")
    lines = [f"{ttl} <b>· MONARCH RANKING</b>", ui.divider()]
    med = ["🥇", "🥈", "🥉"]
    for i, r in enumerate(rows, 1):
        v = ui.n(r.get("v")) if mode != "power" else ui.n(r.get("v"))
        lines.append(f"{med[i-1] if i <= 3 else f'{i}.'} <b>{(r.get('name') or '')[:18]}</b> · "
                     f"<code>R{r.get('rank')}</code> · <b>{v}</b>")
    if not rows:
        lines.append("<i>هیچ پرونده‌ای ثبت نشده — اولین باش.</i>")
    dts = division.top(5)
    if dts and mode in ("power", "boss"):
        lines += ["", "🏢 <b>DIVISIONS</b>"]
        for i, d in enumerate(dts, 1):
            lines.append(f"{i}. {d['name']} <code>[{d['tag']}]</code> L{d['level']} · "
                         f"🪙{ui.n(d['credits'])} · {int(d['wins'])}W")
    await reply(m, "\n".join(lines),
                kb.list_menu([(k, k) for k in ("power", "xp", "boss", "raid", "arena", "research", "deaths")],
                             "top", per_row=3, back="menu:main"))


@router.callback_query(F.data.startswith("top:"))
async def cb_top(c: CallbackQuery):
    mode = c.data.split(":")[1]
    rows = PL.leaderboard(mode, 12)
    lines = [f"🏆 <b>MONARCH RANKING</b> · {mode}", ui.divider()]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. <b>{(r.get('name') or '')[:18]}</b> · <code>R{r.get('rank')}</code> · {ui.n(r.get('v'))}")
    try:
        await c.message.edit_text("\n".join(lines),
                                  reply_markup=kb.list_menu([(k, k) for k in
                                                             ("power", "xp", "boss", "raid", "arena", "research", "deaths")],
                                                             "top", per_row=3, back="menu:main"))
    except TelegramBadRequest:
        pass
    await c.answer()


# ═══════════════ دیتابیس / دوسیه ═══════════════
@router.message(Command("codex"))
async def cmd_codex(m: Message):
    guard(m)
    await reply(m, codex_text(m.from_user.id), codex_kb(m.from_user.id))


def codex_text(uid: int, page: int = 0) -> str:
    roster = sorted(TN.TITANS.values(), key=lambda t: (-balance.titans_rarity_idx(t["rar"]), t["name"]))
    per = 12
    chunk = roster[page * per:(page + 1) * per]
    lines = [f"📁 <b>MONARCH DATABASE</b> · <code>{len(TN.TITANS)} پرونده</code>",
             f"صفحه {page+1}/{max(1, -(-len(roster)//per))} · کشف‌شده توسط تو: "
             f"<b>{len(research.known_rows(uid))}</b>", ui.divider()]
    for t in chunk:
        known = research.is_known(uid, t["id"])
        if known:
            r = research.row(uid, t["id"])
            stg = int(r.get("stage") or 0)
            flag = f"{research.STAGES[stg]['label']}" + (f" · 👑B{r.get('bond')}" if r.get("bond") else "")
            lines.append(f"{t['emj']} <code>{t['id'][:12]}</code> — <b>{t['name']}</b>\n"
                         f"     {flag} · {ui.threat_stars(t['threat'])}")
        else:
            lines.append(f"🕳 <code>UNKNOWN-{abs(hash(t['id'])) % 900 + 100}</code> — "
                         f"<b>UNKNOWN TITAN</b>\n     <i>STATUS: CLASSIFIED</i>")
    lines += ["", "<i>📡 /track برای بازکردن پرونده‌ها · /dossier &lt;id&gt; برای جزییات</i>"]
    return "\n".join(lines)


def codex_kb(uid: int, page: int = 0):
    roster = sorted(TN.TITANS.values(), key=lambda t: (-balance.titans_rarity_idx(t["rar"]), t["name"]))
    per = 12
    items = [(t["id"], t["name"] if research.is_known(uid, t["id"]) else f"UNKNOWN {abs(hash(t['id'])) % 900 + 100}")
             for t in roster[page * per:(page + 1) * per]]
    rows = [[(f"dx:{tid}:{page}", nm[:22]) for tid, nm in items[i:i + 2]] for i in range(0, len(items), 2)]
    nav = []
    if page > 0:
        nav.append((f"cxp:{page-1}", "◀️"))
    nav.append(("menu:main", "🛰 منو"))
    if (page + 1) * per < len(roster):
        nav.append((f"cxp:{page+1}", "▶️"))
    rows.append(nav)
    return kb.kb(rows)


@router.callback_query(F.data.startswith("cxp:"))
async def cb_codex_page(c: CallbackQuery):
    page = int(c.data.split(":")[1])
    try:
        await c.message.edit_text(codex_text(c.from_user.id, page), reply_markup=codex_kb(c.from_user.id, page))
    except TelegramBadRequest:
        pass
    await c.answer()


@router.callback_query(F.data.startswith("dx:"))
async def cb_dossier(c: CallbackQuery):
    _, tid, page = (c.data.split(":") + ["0"])[:3]
    t = TN.get(tid)
    if not t:
        await c.answer("پرونده یافت نشد", show_alert=True)
        return
    try:
        await c.message.edit_text(research.dossier(c.from_user.id, t), reply_markup=kb.kb([[(f'dx:{tid}:{page}', '🔄 بروزرسانی'), (f'hunt:{tid}', '⚔️ شکار'), (f'bond:{tid}', '👑 پیوند')], [(f'cxp:{page}', '↩️ دیتابیس')]]))
    except TelegramBadRequest:
        pass
    # کارت تصویری: حداکثر یک‌بار برای هر پرونده در هر ۶ ساعت (ضداسپم)
    key = (int(c.from_user.id), str(tid))
    if ui.titan_photo(tid) and now() - float(_CARD_SEEN.get(key) or 0) > 21600:
        _CARD_SEEN[key] = now()
        await reply(c, research.dossier(c.from_user.id, t), photo=ui.titan_photo(tid))
    await c.answer()


@router.message(Command("dossier"))
async def cmd_dossier(m: Message, command: CommandObject = None):
    guard(m)
    arg = (command.args or "").strip()
    if not arg:
        await reply(m, texts.TITAN_CLASSIFIED, kb.kb([[("menu:codex", "📁 دیتابیس")]]))
        return
    hit = TN.search(arg) or []
    if not hit:
        await reply(m, "🗄 هیچ پرونده‌ای با این نام نیست. «/codex»")
        return
    if len(hit) > 1 and arg.lower() not in [t["id"] for t in hit]:
        await reply(m, "🔎 چند پرونده:\n" + "\n".join(f"▪️ <code>{t['id']}</code> — {t['name']}" for t in hit[:8]))
        return
    t = TN.get(arg) if TN.get(arg) else hit[0]
    await reply(m, research.dossier(m.from_user.id, t),
                kb.kb([[(f"hunt:{t['id']}", "⚔️ شکار"), (f"bond:{t['id']}", "👑 پیوند")]]),
                photo=ui.titan_photo(t["id"]))


# ═══════════════ تحقیق ═══════════════
@router.message(Command("track"))
async def cmd_track(m: Message):
    if not await gate(m):
        return
    guard(m)
    chat = chat_of(m)
    r = research.track(m.from_user.id, chat, chat.get("zone"))
    await reply(m, r.get("msg", "❔"))
    if r.get("ok") and r.get("advanced"):
        t = TN.get(r["tid"]) or {}
        await reply(m, f"🚨 <b>FILE OPENED</b> — {t.get('name', 'UNKNOWN')}\n"
                       f"«/dossier {t.get('id')}» برای پرونده · «/sample {t.get('id')}» برای نمونه")


@router.message(Command("sample"))
async def cmd_sample(m: Message, command: CommandObject = None):
    if not await gate(m):
        return
    guard(m)
    tid = resolve_tid(command.args)
    if not tid:
        await reply(m, "🧬 نمونه‌برداری روی چه چیزی؟ <code>/sample anguirus</code>\n"
                       "آخرین هدف: " + str(db.db().getv(f"lasttarget:{m.from_user.id}", "—")))
        return
    r = research.sample(m.from_user.id, tid, chat_of(m))
    await reply(m, r.get("msg", "❔"))
    if "AGENT DOWN" in (r.get("msg") or ""):
        PL.die(m.from_user.id, "SAMPLING")


@router.message(Command("analyze"))
async def cmd_analyze(m: Message, command: CommandObject = None):
    if not await gate(m):
        return
    guard(m)
    tid = resolve_tid(command.args)
    if not tid:
        await reply(m, "🔬 هدف مشخص نیست — <code>/analyze &lt;titan&gt;</code>")
        return
    r = research.analyze(m.from_user.id, tid)
    await reply(m, r.get("msg", "❔"))


@router.message(Command("lab"))
async def cmd_lab(m: Message):
    guard(m)
    p = guard(m)
    if not p.get("lab_titan"):
        await reply(m, "🔬 صف آزمایشگاه خالی است — <code>/analyze &lt;titan&gt;</code>")
        return
    left = float(p["lab_until"]) - now()
    if left > 0:
        await reply(m, f"⏳ تحلیل {p['lab_titan']} — {ui.dur(left)} مانده.\n"
                       f"🏢 ارتقای Laboratory سرعت را بالا می‌برد.")
        return
    r = research.lab_check(m.from_user.id)
    await reply(m, r.get("msg", "✅ تحلیل کامل شد."))


@router.message(Command("bond"))
async def cmd_bond(m: Message, command: CommandObject = None):
    if not await gate(m):
        return
    guard(m)
    args = (command.args or "").strip().split()
    if args and args[0].lower() in ("up", "ارتقا"):
        tid = resolve_tid(" ".join(args[1:]))
        if not tid:
            await reply(m, "👑 <code>/bond up &lt;titan&gt;</code>")
            return
        r = research.bond_up(m.from_user.id, tid)
        await reply(m, r.get("msg", "❔"))
        return
    tid = resolve_tid(" ".join(args))
    if not tid:
        rows = research.known_rows(m.from_user.id)
        ready = [r for r in rows if int(r["stage"] or 0) >= 4 and not int(r["bond"] or 0)]
        if not ready:
            await reply(m, texts.TITAN_CLASSIFIED)
            return
        t = TN.get(ready[0]["titan_id"])
        await reply(m, f"👑 آماده‌ی پیوند: <b>{t['name']}</b>\n<code>/bond {t['id']}</code>")
        return
    r = research.bond(m.from_user.id, tid)
    await reply(m, r.get("msg", "❔"))


@router.callback_query(F.data.startswith("bond:"))
async def cb_bond(c: CallbackQuery):
    tid = c.data.split(":")[1]
    guard(c.message)
    r = research.bond(c.from_user.id, tid)
    await c.answer((r.get("msg") or "❔")[:180].replace("<b>", "").replace("</b>", ""), show_alert=True)


def resolve_tid(args) -> str:
    a = (args or "").strip().lower()
    if not a:
        return ""
    if a in TN.TITANS:
        return a
    last = a.split()[-1] if " " in a else a
    if last in TN.TITANS:
        return last
    hits = TN.search(a)
    return hits[0]["id"] if hits else ""


@router.message(Command("puzzle"))
async def cmd_puzzle(m: Message):
    if not await gate(m):
        return
    guard(m)
    r = research.puzzle_new(m.from_user.id)
    if not r.get("ok"):
        await reply(m, r.get("msg", "❔"))
        return
    rows = [[(f"pz:{oid}", nm[:20])] for nm, oid in zip(r["opts"], r["ids"])]
    await reply(m, f"🧮 <b>MONARCH CIPHER</b>\n\n{r['q']}\n\n<i>پاسخ درست → +{config.PUZZLE_POINTS} امتیاز تحقیق</i>",
                kb.kb(rows))


@router.callback_query(F.data.startswith("pz:"))
async def cb_puzzle(c: CallbackQuery):
    tid = c.data.split(":")[1]
    r = research.puzzle_answer(c.from_user.id, tid)
    await c.answer((r.get("msg") or "")[:190].replace("<b>", "").replace("</b>", ""), show_alert=True)
    try:
        await c.message.edit_reply_markup(None)
    except TelegramBadRequest:
        pass


# ═══════════════ نبرد ═══════════════
@router.message(Command("hunt"))
async def cmd_hunt(m: Message, command: CommandObject = None):
    if not await gate(m):
        return
    guard(m)
    tid = resolve_tid(command.args)
    if not tid:
        rows = sorted(TN.TITANS.values(), key=lambda t: t["power"])[:10]
        items = [(t["id"], f"{t['emj']} {t['name']}") for t in rows]
        await reply(m, "⚔️ <b>HUNT CONSOLE</b>\nیک هدف انتخاب کن (یا <code>/hunt &lt;id&gt;</code>).\n"
                       "<i>تایتان‌های بالاتر از رتبه‌ی تو قفل‌اند.</i>",
                    kb.list_menu(items, "hunt", per_row=2))
        return
    chat = chat_of(m)
    r = combat.start(m.from_user.id, "hunt", chat=chat, titan_id=tid)
    await combat_reply(m, r)


@router.callback_query(F.data.startswith("hunt:"))
async def cb_hunt(c: CallbackQuery):
    tid = c.data.split(":")[1]
    guard(c.message)
    if not await gate(c.message):
        return
    chat = chat_of(c.message)
    r = combat.start(c.from_user.id, "hunt", chat=chat, titan_id=tid)
    await combat_reply(c.message, r)
    await c.answer()


@router.message(Command("fight"))
async def cmd_fight(m: Message):
    guard(m)
    act = combat.active_of(m.from_user.id)
    if not act:
        await reply(m, "⚔️ درگیری فعالی نداری — <code>/hunt</code> یا <code>/boss</code>")
        return
    cid = act["row"]["id"]
    await reply(m, combat.feed(act["st"], ["🛰 فید بازیابی شد."]),
                kb.combat_menu(cid, combat.options(cid, m.from_user.id)), feed=True, cid=cid)


async def combat_reply(m, r: dict):
    if not r.get("ok") and not r.get("text") and not r.get("feed"):
        await reply(m, r.get("msg", "❔"))
        return
    if r.get("msg") and not r.get("state"):
        await reply(m, r["msg"])
        return
    if r.get("ended"):
        _FEED.pop(int(m.chat.id), None)
        await reply(m, r.get("feed") or r.get("text"), None)
        return
    cid = r["cid"]
    await reply(m, r.get("feed") or r.get("msg"),
                kb.combat_menu(cid, combat.options(cid, m.from_user.id)), feed=True, cid=cid)


@router.callback_query(F.data.startswith("cbt:"))
async def cb_combat(c: CallbackQuery):
    parts = c.data.split(":")
    if parts[1] == "resume":
        act = combat.active_of(c.from_user.id)
        if not act:
            await c.answer("نبرد فعالی نیست", show_alert=True)
            return
        cid = act["row"]["id"]
        try:
            await c.message.edit_text(combat.feed(act['st'], ['🛰 ادامه بده.']), reply_markup=kb.combat_menu(cid, combat.options(cid, c.from_user.id)))
        except TelegramBadRequest:
            pass
        await c.answer()
        return
    cid = int(parts[1])
    action = parts[2] if len(parts) > 2 else "info"
    arg = parts[3] if len(parts) > 3 else None
    row, st = None, None
    if action in ("info", "help"):
        act = combat.active_of(c.from_user.id)
        if act and int(act["row"]["id"]) == cid:
            txt = combat.feed(act["st"], [texts.RULES[:600] if action == "help" else "🛰 وضعیت فعلی."])
            try:
                await c.message.edit_text(txt, reply_markup=kb.combat_menu(cid, combat.options(cid, c.from_user.id)))
            except TelegramBadRequest:
                pass
        await c.answer()
        return
    r = combat.act(cid, c.from_user.id, action, arg)
    if r.get("ok") is False and not r.get("feed") and not r.get("ended"):
        await c.answer((r.get("msg") or r.get("why") or "❔")[:190]
                       .replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", ""),
                       show_alert=True)
        return
    if r.get("ended"):
        _FEED.pop(int(c.message.chat.id), None)
        try:
            await c.message.edit_text(r.get("feed") or r.get("text"), reply_markup=None)
        except TelegramBadRequest:
            await reply(c.message, r.get("text") or r.get("feed") or "")
        await c.answer()
        return
    try:
        await c.message.edit_text(r['feed'], reply_markup=kb.combat_menu(cid, combat.options(cid, c.from_user.id)))
        _FEED[int(c.message.chat.id)] = c.message.message_id
        db.db().ex("UPDATE combats SET msg_id=? WHERE id=?", (c.message.message_id, cid))
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            await reply(c.message, r.get("feed", ""), kb.combat_menu(cid, combat.options(cid, c.from_user.id)),
                        feed=True, cid=cid)
    await c.answer()


# ═══════════════ باس / منطقه ═══════════════
@router.message(Command("boss"))
async def cmd_boss(m: Message):
    if not await gate(m):
        return
    guard(m)
    chat = chat_of(m)
    a = bosses.active(chat["chat_id"])
    if not a:
        res = bosses.spawn(chat["chat_id"], force=True)
        if not res.get("ok"):
            await reply(m, "🕹 MONARCH در این بخش تهدید فعالی ثبت نکرده — <code>/scan</code> را ببین.")
            return
        await reply(m, res["text"])
        return
    r = bosses.engage(m.from_user.id, chat)
    if r.get("ok"):
        await combat_reply(m, r)
    else:
        await reply(m, r.get("msg", "❔"))


@router.message(Command("scan"))
async def cmd_scan(m: Message):
    guard(m)
    chat = chat_of(m)
    a = bosses.active(chat["chat_id"])
    zone = chat.get("zone") or "ocean"
    lines = [f"📡 <b>SECTOR SCAN</b> · {TN.ENVS.get(zone, zone)}",
             f"🌡 خطر: {ui.bar(int(chat.get('danger') or 1), 5, 5)} <code>{chat.get('danger', 1)}/5</code>",
             f"👥 عاملان فعال ۲۴ ساعت اخیر: <b>{db.db().one('SELECT COUNT(*) c FROM chat_users WHERE chat_id=? AND last_active>?', (chat['chat_id'], now()-86400))['c']}</b>"]
    if a:
        b = bosses.by_id(a["bid"])
        st = a["state"]
        lines += ["", f"🕹 <b>{b['name']}</b> · {b['tier']}",
                  f"❤️ {ui.bar(st.get('hp', 0), st.get('max_hp', 1), 12)} <code>{ui.n(st.get('hp'))}</code>",
                  f"⏱ پنجره: {ui.dur(a['left'])} · 👥 شرکت‌کننده: {len(st.get('participants') or {})}",
                  "", f"<i>{b.get('lore', '')}</i>",
                  "▸ <code>/boss</code> برای ورود به نبرد · دیگران با همان نبرد /join نمی‌کنند؛ "
                  "در نبردِ فعال دکمه‌ی «Support Ally» دارند."]
    else:
        pool = bosses.eligible(zone)
        lines += ["", "<i>هیچ تهدید فعالی ثبت نشده.</i>",
                  f"📶 امضاهای شناسایی‌شده در این بخش: <b>{len(pool)}</b>",
                  "<i>MONARCH هر چند دقیقه یک‌بار زلزله را اسکن می‌کند.</i>"]
    await reply(m, "\n".join(lines))


# ═══════════════ رید جهانی ═══════════════
@router.message(Command("raid"))
async def cmd_raid(m: Message, command: CommandObject = None):
    guard(m)
    args = (command.args or "").strip().lower()
    if args.startswith("join"):
        r = RA.join(m.from_user.id)
        await reply(m, r.get("msg", r.get("ok") and "✅" or "❔"))
        return
    if args in RA.ACTIONS:
        r = RA.act(m.from_user.id, args)
        await reply(m, r.get("msg", "❔"))
        return
    if args == "board":
        await reply(m, RA.board())
        return
    await reply(m, RA.board(),
                kb.kb([[("ra:strike", "⚔️ Strike"), ("ra:focus", "💥 Focus")],
                       [("ra:shield", "🛡 Shield"), ("ra:repair", "🩹 Repair")],
                       [("ra:analyze", "🔬 Analyze"), ("ra:regroup", "🔋 Regroup")],
                       [("ra:join", "🛰 پیوستن"), ("menu:main", "🛰 منو")]]))


@router.callback_query(F.data.startswith("ra:"))
async def cb_raid(c: CallbackQuery):
    key = c.data.split(":")[1]
    guard(c.message)
    if key == "join":
        r = RA.join(c.from_user.id)
        await c.answer((r.get("msg") or "")[:180], show_alert=True)
        return
    r = RA.act(c.from_user.id, key)
    txt = r.get("msg") or RA.board()
    try:
        await c.message.edit_text(f'{txt}\n\n▬▬▬▬▬▬▬▬▬▬▬▬\n' + RA.board(), reply_markup=kb.kb([[('ra:strike', '⚔️ Strike'), ('ra:focus', '💥 Focus')], [('ra:shield', '🛡 Shield'), ('ra:repair', '🩹 Repair')], [('ra:analyze', '🔬 Analyze'), ('ra:regroup', '🔋 Regroup')]]))
    except TelegramBadRequest:
        pass
    await c.answer()


# ═══════════════ کاوش ═══════════════
@router.message(Command("explore"))
async def cmd_explore(m: Message, command: CommandObject = None):
    if not await gate(m):
        return
    guard(m)
    args = (command.args or "").strip().lower()
    if args.startswith("claim"):
        r = expedition.claim(m.from_user.id, chat_of(m))
        await reply(m, r.get("msg", "❔"))
        if r.get("encounter"):
            chat = chat_of(m)
            cr = combat.start(m.from_user.id, "hunt", chat=chat, titan_id=r["encounter"])
            await combat_reply(m, cr)
        return
    if args.startswith("report") or args.startswith("abort"):
        st = expedition.status(m.from_user.id)
        if args.startswith("abort"):
            r = expedition.abort(m.from_user.id)
            await reply(m, r.get("msg", "❔"))
            return
        if not st:
            await reply(m, "🗺 کاوش فعالی نداری.")
            return
        z = expedition.ZONES.get(st["zone"], {})
        await reply(m, f"🗺 <b>ACTIVE EXPEDITION</b>\n{z.get('name', st['zone'])} · سطح {st['tier']}\n"
                       + (f"⏱ {ui.dur(st['left'])} تا بازگشت" if st.get("active") else "✅ آماده‌ی تحویل: /explore claim"),
                    kb.kb([[("menu:explore", "🗺 انتخاب منطقه")]]))
        return
    p = PL.get(m.from_user.id)
    items = [(k, f"{z['name'].split(' ', 1)[0]} {z['name'].split(' ', 1)[-1][:14]} · {z['mins'][0]}m")
             for k, z in expedition.available(p)]
    await reply(m, "🗺 <b>EXPEDITION CONSOLE</b>\nمنطقه را انتخاب کن؛ تیم ۹ تا ۴۰ دقیقه درگیر است.\n"
                  "<i>بعضی کاوش‌ها برنمی‌گردند. بعضی گنج پیدا می‌کنند.</i>",
                kb.list_menu(items, "exp", per_row=1, back="menu:main"))


@router.callback_query(F.data.startswith("exp:"))
async def cb_exp(c: CallbackQuery):
    zone = c.data.split(":")[1]
    guard(c.message)
    r = expedition.start(c.from_user.id, zone, chat_of(c.message))
    await c.answer((r.get("msg") or "")[:190].replace("<b>", "").replace("</b>", ""), show_alert=True)


# ═══════════════ آرنا ═══════════════
@router.message(Command("arena"))
async def cmd_arena(m: Message):
    if not await gate(m):
        return
    guard(m)
    await reply(m, arena.board_text(m.from_user.id),
                kb.kb([[("ar:go", "⚔️ یافتن حریف"), ("ar:me", "📊 آمار من")]]))


@router.callback_query(F.data.startswith("ar:"))
async def cb_arena(c: CallbackQuery):
    key = c.data.split(":")[1]
    guard(c.message)
    if key == "me":
        p = PL.get(c.from_user.id) or {}
        t = arena.tier_of(float(p.get("arena_rating") or 1000))
        await c.answer(f"{t['emj']} {t['name']} · {float(p.get('arena_rating') or 1000):.0f} "
                       f"({int(p.get('arena_wins') or 0)}W/{int(p.get('arena_losses') or 0)}L)", show_alert=True)
        return
    r = arena.challenge(c.from_user.id, chat_of(c.message))
    if r.get("ok"):
        await combat_reply(c.message, r)
    else:
        await c.answer((r.get("msg") or "❔")[:190], show_alert=True)
    await c.answer()


@router.message(Command("duel"))
async def cmd_duel(m: Message, command: CommandObject = None):
    if not await gate(m):
        return
    guard(m)
    target = None
    if m.reply_to_message and m.reply_to_message.from_user:
        target = m.reply_to_message.from_user.id
    elif command and command.args:
        txt = command.args
        digits = "".join(ch for ch in txt if ch.isdigit())
        if digits:
            target = int(digits)
    if not target:
        await reply(m, "🎯 یک پیامِ حریف را Reply کن یا <code>/duel &lt;id&gt;</code>")
        return
    r = arena.challenge(m.from_user.id, chat_of(m), int(target))
    await combat_reply(m, r)


# ═══════════════ اقتصاد ═══════════════
@router.message(Command("shop"))
async def cmd_shop(m: Message, command: CommandObject = None):
    guard(m)
    await reply(m, shop_text(m.from_user.id), shop_kb())


def shop_text(uid: int, kind: str = None) -> str:
    p = PL.get(uid) or {}
    inv_ = PL.inv(uid)
    lines = [f"🪙 <b>MONARCH QUARTERMASTER</b> · 🪙 {ui.n(p.get('credits'))} MC",
             "<i>هیچ آیتم پولی قدرت نمی‌فروشد — همه‌چیز با بازی باز می‌شود.</i>", ui.divider()]
    for iid, it in economy.catalog(kind):
        if it.get("kind") == "material":
            continue
        have = int((inv_.get(iid) or {}).get("qty") or 0)
        lock = "🔒" if int(p.get("rank") or 1) < it.get("need_rank", 1) else ("✅" if have else "▫️")
        mods = " ".join(f"{k}+{v}" for k, v in (it.get("mods") or {}).items())
        lines.append(f"{lock} <code>{iid}</code> — <b>{it['name']}</b> ×{have}\n"
                     f"     🪙{int(it['cost']):,} · R{it.get('need_rank', 1)} · <i>{mods or it.get('desc', '')[:40]}</i>")
    return "\n".join(lines)


def shop_kb(kind: str = None) -> "InlineKeyboardMarkup":
    p = PL.get(0) or {}
    rows = [[(f"sk:{k}", label) for k, label in
             (("rig", "🥼 Rig"), ("weapon", "🔫 سلاح"), ("module", "⚙️ ماژول"), ("consumable", "🧪 مصرفی"))]]
    items = db.db().q("SELECT 1")
    rows += []
    return kb.kb(rows + [[("menu:main", "🛰 منو")]])


@router.callback_query(F.data.startswith("sk:"))
async def cb_shop(c: CallbackQuery):
    kind = c.data.split(":")[1]
    rows = [[(f"buy:{iid}", f"{it['name'][:20]} · {int(it['cost']):,}")]
            for iid, it in economy.catalog(kind)
            if it.get("kind") != "material"]
    half = (len(rows) + 1) // 2
    grid = [x for pair in zip(rows[:half], rows[half:]) for x in pair if x]
    grid.append([("menu:main", "🛰 منو")])
    try:
        await c.message.edit_text(shop_text(c.from_user.id, kind), reply_markup=kb.kb(grid))
    except TelegramBadRequest:
        pass
    await c.answer()


@router.callback_query(F.data.startswith("buy:"))
async def cb_buy(c: CallbackQuery):
    iid = c.data.split(":")[1]
    guard(c.message)
    r = economy.buy(c.from_user.id, iid)
    await c.answer((r.get("msg") or "").replace("<b>", "").replace("</b>", "")[:190], show_alert=True)
    if r.get("ok"):
        try:
            await c.message.edit_text(shop_text(c.from_user.id))
        except TelegramBadRequest:
            pass


@router.message(Command("inv"))
async def cmd_inv(m: Message):
    guard(m)
    uid = m.from_user.id
    inv_ = PL.inv(uid)
    lines = [f"🎒 <b>FIELD LOCKER</b> — {PL.name_of(uid)}", ui.divider()]
    if not inv_:
        lines.append("<i>خالی. /shop را ببین.</i>")
    for iid, row in inv_.items():
        it = economy.ITEMS.get(iid) or {}
        lvl = PL.item_level(uid, iid)
        lines.append(f"{'⚙️' if row['equipped'] else '▫️'} <code>{iid}</code> ×{row['qty']} — {it.get('name', iid)}"
                     + (f" <code>MK+{lvl}</code>" if lvl else ""))
        if it.get("kind") == "consumable":
            lines.append(f"     <i>{it.get('desc', '')}</i>")
    p = PL.get(uid)
    res = " · ".join(f"{m2['icon']} {ui.n(p.get(k))}" for k, m2 in economy.RES.items())
    lines += ["", f"💼 {res}"]
    rows = [[(f"eq:{iid}", (economy.ITEMS.get(iid) or {}).get("name", iid)[:18])] for iid in list(inv_)[:6]]
    rows.append([("menu:shop", "🪙 فروشگاه"), ("menu:main", "🛰 منو")])
    await reply(m, "\n".join(lines), kb.kb(rows))


@router.callback_query(F.data.startswith("eq:"))
async def cb_equip(c: CallbackQuery):
    iid = c.data.split(":")[1]
    guard(c.message)
    r = PL.equip(c.from_user.id, iid)
    await c.answer((r.get("msg") or "")[:180].replace("<b>", "").replace("</b>", ""), show_alert=True)


@router.message(Command("equip"))
async def cmd_equip(m: Message, command: CommandObject = None):
    guard(m)
    iid = (command.args or "").strip().split()[-1] if command and command.args else ""
    if not iid:
        await reply(m, "⚙️ <code>/equip &lt;item_id&gt;</code> — لیست: /inv")
        return
    r = PL.equip(m.from_user.id, iid)
    await reply(m, r.get("msg", "❔"))


@router.message(Command("use"))
async def cmd_use(m: Message, command: CommandObject = None):
    guard(m)
    iid = (command.args or "").strip().split()[-1] if command and command.args else ""
    r = PL.use_item(m.from_user.id, iid) if iid else dict(ok=False, msg="🎒 <code>/use cs_stim</code>")
    await reply(m, r.get("msg", "❔"))


@router.message(Command("upgrade"))
async def cmd_upgrade(m: Message, command: CommandObject = None):
    if not await gate(m):
        return
    guard(m)
    iid = (command.args or "").strip().split()[-1] if command and command.args else ""
    if not iid:
        await reply(m, "⚙️ <code>/upgrade &lt;item_id&gt;</code> · هر سطح +۱۲٪ مودها")
        return
    r = economy.upgrade(m.from_user.id, iid)
    await reply(m, r.get("msg", "❔"))


@router.message(Command("market"))
async def cmd_market(m: Message):
    guard(m)
    p = PL.get(m.from_user.id)
    lines = [f"🏷 <b>MONARCH EXCHANGE</b> · <code>tick {int(now() // 600) % 144}</code>",
             f"🪙 موجودی تو: <b>{ui.n(p.get('credits'))} MC</b>", ui.divider(), economy.market_board(),
             "", "<i>هر ۱۰ دقیقه یک‌بار قیمت جابه‌جا می‌شود؛ Titan Core و MC قابل‌فروش نیستند.</i>",
             "▸ <code>/sell dna 5</code>"]
    await reply(m, "\n".join(lines))


@router.message(Command("sell"))
async def cmd_sell(m: Message, command: CommandObject = None):
    guard(m)
    parts = (command.args or "").split()
    if len(parts) < 2:
        await reply(m, "🏷 <code>/sell &lt;res&gt; &lt;qty&gt;</code> · res: dna|cells|mats|fdata")
        return
    key = parts[0].lower()
    alias = {"dna": "dna", "🧬": "dna", "cells": "cells", "🔋": "cells", "cell": "cells",
             "mats": "mats", "material": "mats", "🔩": "mats", "data": "fdata", "fdata": "fdata",
             "📡": "fdata", "credits": "credits", "🪙": "credits"}.get(key, key)
    try:
        qty = float("".join(ch for ch in parts[1] if ch.isdigit() or ch == "."))
    except ValueError:
        qty = 0
    r = economy.sell(m.from_user.id, alias, qty)
    await reply(m, r.get("msg", "❔"))


@router.message(Command("bounty"))
async def cmd_bounty(m: Message, command: CommandObject = None):
    if not await gate(m):
        return
    guard(m)
    parts = (command.args or "").split()
    tgt = None
    amt = 0
    if m.reply_to_message and m.reply_to_message.from_user:
        tgt = m.reply_to_message.from_user.id
    for p_ in parts:
        d = "".join(ch for ch in p_ if ch.isdigit())
        if d and len(d) > 5:
            tgt = int(d)
        elif d:
            amt = float(d)
    if not tgt or not amt:
        await reply(m, f"🎯 <code>/bounty @agent {config.BOUNTY_MIN}</code> یا Reply روی پیام هدف")
        return
    r = economy.bounty_place(m.from_user.id, tgt, amt)
    await reply(m, r.get("msg", "❔"))


@router.message(Command("vault"))
async def cmd_vault(m: Message, command: CommandObject = None):
    guard(m)
    p = PL.get(m.from_user.id)
    parts = (command.args or "").split()
    if not parts:
        await reply(m, f"🏦 <b>VAULT</b>\n🪙 داخل خزنه: <b>{ui.n(p.get('vault'))}</b> / {ui.n(PL.vault_capacity(p))}\n"
                       f"<i>منابع داخل خزنه هنگام مرگ Drop نمی‌شوند.</i>\n"
                       f"▸ <code>/vault 500</code> · <code>/vault out 500</code>",
                    kb.kb([[("vt:1000", "🪙 ۱۰۰۰"), ("vt:5000", "🪙 ۵۰۰۰"), ("vt:out", "↩️ برداشت")]]))
        return
    if parts[0].lower() in ("out", "برداشت"):
        amt = float("".join(ch for ch in (parts[1] if len(parts) > 1 else "0") if ch.isdigit()) or 0)
        r = PL.vault_withdraw(m.from_user.id, amt or float(p.get("vault") or 0))
    else:
        amt = float("".join(ch for ch in parts[0] if ch.isdigit()) or 0)
        r = PL.vault_store(m.from_user.id, amt)
    await reply(m, r.get("msg", "❔"))


@router.callback_query(F.data.startswith("vt:"))
async def cb_vault(c: CallbackQuery):
    v = c.data.split(":")[1]
    guard(c.message)
    r = PL.vault_withdraw(c.from_user.id, 1e12) if v == "out" else PL.vault_store(c.from_user.id, float(v))
    await c.answer((r.get("msg") or "")[:180].replace("<b>", "").replace("</b>", ""), show_alert=True)


# ═══════════════ روزانه / مأموریت ═══════════════
@router.message(Command("missions"))
async def cmd_missions(m: Message):
    guard(m)
    p = PL.get(m.from_user.id)
    st = db.jload(p.get("missions"), {}) or {}
    claims = [(mid, f"🎁 {economy.MISSIONS[mid]['name'][:20]}") for mid, r in st.items()
              if r.get("done") and not r.get("got")]
    lines = [f"📅 <b>DAILY OPS</b> · {db.local_day()}",
             f"🔥 استریک حضور: <b>{int(p.get('streak') or 0)}</b> · 🎫 چک‌این امروز: "
             f"{'✅' if p.get('last_seen_day') == db.local_day() else '⬜'}", ui.divider(),
             economy.mission_board(m.from_user.id), "",
             f"📊 جمع منابع: 🪙{ui.n(p.get('credits'))} · 💎{ui.n(p.get('cores'))} · "
             f"🧬{ui.n(p.get('dna'))} · 🔩{ui.n(p.get('mats'))} · 📡{ui.n(p.get('fdata'))}"]
    rows = [[("mis:claim", "🎁 دریافت جوایز")] if claims else []]
    rows.append([("daily", "📅 حضور روزانه"), ("menu:main", "🛰 منو")])
    await reply(m, "\n".join(lines), kb.kb(rows))


@router.callback_query(F.data == "mis:claim")
async def cb_claim(c: CallbackQuery):
    p = PL.get(c.from_user.id)
    st = db.jload(p.get("missions"), {}) or {}
    msgs = []
    for mid, r in st.items():
        if r.get("done") and not r.get("got"):
            res = economy.claim_mission(c.from_user.id, mid)
            if res.get("ok"):
                msgs.append(res["msg"])
    await c.answer("\n".join(msgs)[:190].replace("<b>", "").replace("</b>", "") if msgs else "چیزی برای دریافت نیست",
                   show_alert=True)
    if msgs:
        try:
            await c.message.edit_text("\n\n".join(msgs))
        except TelegramBadRequest:
            pass


@router.message(Command("daily"))
async def cmd_daily(m: Message):
    guard(m)
    r = economy.checkin(m.from_user.id)
    await reply(m, r.get("msg", "❔") + f"\n\n📅 مأموریت‌ها:\n{economy.mission_board(m.from_user.id)}")


# ═══════════════ Division ═══════════════
@router.message(Command("div"))
async def cmd_div(m: Message, command: CommandObject = None):
    if not await gate(m):
        return
    guard(m)
    parts = (command.args or "").split()
    if not parts:
        await reply(m, division.card(m.from_user.id),
                    kb.kb([[("dv:fac", "⚙️ تسهیلات"), ("dv:top", "🏆 برترین‌ها")],
                           [("dv:war", "⚔️ جنگ"), ("menu:main", "🛰 منو")]]))
        return
    key = parts[0].lower()
    arg = " ".join(parts[1:])
    if key in ("create", "ساخت"):
        bits = arg.rsplit(" ", 1)
        name, tag = (bits[0], bits[1]) if len(bits) == 2 else (arg, "")
        r = division.create(m.from_user.id, name, tag)
    elif key in ("join", "پیوستن"):
        r = division.join(m.from_user.id, arg)
    elif key in ("leave",):
        r = division.leave(m.from_user.id)
    elif key in ("disband",):
        r = division.disband(m.from_user.id)
    elif key in ("fac",):
        r = division.fac_up(m.from_user.id, arg.split()[0] if arg else "radar")
    elif key in ("deposit", "سپرده"):
        r = division.deposit(m.from_user.id, float("".join(ch for ch in arg if ch.isdigit()) or 0))
    elif key in ("withdraw", "برداشت"):
        r = division.withdraw(m.from_user.id, float("".join(ch for ch in arg if ch.isdigit()) or 0))
    elif key in ("promote",):
        tgt = "".join(ch for ch in arg if ch.isdigit())
        r = division.promote(m.from_user.id, int(tgt)) if tgt else dict(ok=False, msg="🎖 /div promote <id>")
    elif key in ("war",):
        nums = [float("".join(ch for ch in x if (ch.isdigit() or ch == ".")) or 0) for x in arg.split()]
        if len(nums) != 3:
            r = dict(ok=False, msg="⚔️ <code>/div war 40 35 25</code> → Assault / Defense / Intel (مجموع ۱۰۰)")
        else:
            r = division.deploy(m.from_user.id, dict(zip(division.LANES, nums)))
    elif key in ("top",):
        rows = division.top(10)
        r = dict(ok=True, msg="🏢 <b>DIVISION REGISTRY</b>\n" + "\n".join(
            f"{i}. <b>{d['name']}</b> <code>[{d['tag']}]</code> · L{d['level']} · "
            f"🪙{ui.n(d['credits'])} · {int(d['wins'])}W" for i, d in enumerate(rows, 1)))
    else:
        r = dict(ok=False, msg="❔ <code>/div [create|join|leave|fac|war|deposit|withdraw|promote|top]</code>")
    await reply(m, r.get("msg", "❔"))


@router.callback_query(F.data.startswith("dv:"))
async def cb_div(c: CallbackQuery):
    key = c.data.split(":")[1]
    guard(c.message)
    if key == "fac":
        rows = [[(f"fac:{k}", f"{m['name']} · L{division.facility_of(c.from_user.id, k)}")]
                for k, m in division.FACILITIES.items()]
        try:
            await c.message.edit_text('⚙️ <b>FACILITIES</b> — هزینه از خزانه\u200cی Division\n<i>هر سطح با /div fac &lt;key&gt; ساخته می\u200cشود.</i>', reply_markup=kb.kb(rows + [[('menu:main', '🛰 منو')]]))
        except TelegramBadRequest:
            pass
    elif key == "top":
        rows = division.top(10)
        txt = "🏢 <b>DIVISION REGISTRY</b>\n" + "\n".join(
            f"{i}. <b>{d['name']}</b> L{d['level']} · 🪙{ui.n(d['credits'])}" for i, d in enumerate(rows, 1))
        try:
            await c.message.edit_text(txt)
        except TelegramBadRequest:
            pass
    elif key == "war":
        w = division.war_open()
        txt = ("⚔️ <b>DIVISION WAR</b>\n" +
               (f"جنگ فعال است · {ui.dur(w['left'])} تا تسویه\n"
                f"تخصیص: <code>/div war 40 35 25</code> (Assault/Defense/Intel)"
                if w.get("active") else "جنگی فعال نیست.\nپنجشنبه ۲۰:۰۰ تهران —_pairs بر اساس XP._"))
        try:
            await c.message.edit_text(txt)
        except TelegramBadRequest:
            pass
    await c.answer()


@router.callback_query(F.data.startswith("fac:"))
async def cb_fac(c: CallbackQuery):
    k = c.data.split(":")[1]
    guard(c.message)
    r = division.fac_up(c.from_user.id, k)
    await c.answer((r.get("msg") or "")[:190].replace("<b>", "").replace("</b>", ""), show_alert=True)


# ═══════════════ منو ═══════════════
@router.callback_query(F.data.startswith("menu:"))
async def cb_menu(c: CallbackQuery):
    key = c.data.split(":")[1]
    guard(c.message)
    uid = c.from_user.id
    p = PL.get(uid)
    act = combat.active_of(uid)
    if key == "main":
        try:
            await c.message.edit_text(f"🛰 <b>MONARCH COMMAND</b> — {p.get('name')}\n🎖 {PL.rank_label(p)} · ❤️ {ui.n(p['hp'])}/{ui.n(p['max_hp'])} · 🔋 {ui.n(p['energy'])} · 🪙 {ui.n(p['credits'])} MC\n📊 Power <b>{PL.power_rating(p):,}</b> · 🔬 پرونده\u200cهای باز <b>{len(research.known_rows(uid))}</b>", reply_markup=kb.main_menu(p, has_combat=bool(act)))
        except TelegramBadRequest:
            pass
    elif key == "codex":
        try:
            await c.message.edit_text(codex_text(uid), reply_markup=codex_kb(uid))
        except TelegramBadRequest:
            pass
    elif key == "track":
        r = research.track(uid, chat_of(c.message), chat_of(c.message).get("zone"))
        await c.answer((r.get("msg") or "")[:190].replace("<b>", "").replace("</b>", ""), show_alert=True)
    elif key == "explore":
        await cmd_explore(c.message)
    elif key == "boss":
        await cmd_boss(c.message)
    elif key == "raid":
        await cmd_raid(c.message, CommandObject())
    elif key == "arena":
        await cmd_arena(c.message)
    elif key == "shop":
        await cmd_shop(c.message)
    elif key == "inv":
        await cmd_inv(c.message)
    elif key == "missions":
        await cmd_missions(c.message)
    elif key == "div":
        await cmd_div(c.message)
    elif key == "top":
        await cmd_top(c.message, CommandObject())
    await c.answer()


@router.message(Command("ref"))
async def cmd_ref(m: Message):
    guard(m)
    await reply(m, f"🤝 <b>RECRUIT PROTOCOL</b>\nلینک تو:\n<code>/start ref:{m.from_user.id}</code>\n"
                   f"هر عاملِ تازه 🪙۳۰۰ MC و 📡۱ داده به تو می‌دهد.")


@router.message(Command("report"))
async def cmd_report(m: Message):
    guard(m)
    d = db.db()
    players = d.one("SELECT COUNT(*) c FROM players")["c"]
    live = d.one("SELECT COUNT(*) c FROM combats WHERE status='live'")["c"]
    divs = d.one("SELECT COUNT(*) c FROM divisions")["c"]
    hour = db.local_now().strftime("%H:%M")
    await reply(m, f"🛰 <b>SYSTEM REPORT</b>\n"
                  f"▪️ بازیکنان: <b>{players}</b>\n"
                  f"▪️ نبردهای فعال: <b>{live}</b>\n"
                  f"▪️ Division‌ها: <b>{divs}</b>\n"
                  f"▪️ ساعت محلی: {hour} تهران")


# ─────────── نگاشت دستور ↔ تابع + پیشوند فارسی ───────────
ARGS, NOARGS = True, False
COMMAND_MAP = {
    "start": (cmd_start, ARGS), "help": (cmd_help, NOARGS), "rules": (cmd_rules, NOARGS),
    "join": (cmd_join, NOARGS), "me": (cmd_me, NOARGS), "clearance": (cmd_clearance, NOARGS),
    "top": (cmd_top, ARGS), "codex": (cmd_codex, NOARGS), "dossier": (cmd_dossier, ARGS),
    "track": (cmd_track, NOARGS), "sample": (cmd_sample, ARGS), "analyze": (cmd_analyze, ARGS),
    "lab": (cmd_lab, NOARGS), "bond": (cmd_bond, ARGS), "puzzle": (cmd_puzzle, NOARGS),
    "hunt": (cmd_hunt, ARGS), "fight": (cmd_fight, NOARGS), "boss": (cmd_boss, NOARGS),
    "scan": (cmd_scan, NOARGS), "raid": (cmd_raid, ARGS), "arena": (cmd_arena, NOARGS),
    "duel": (cmd_duel, ARGS), "explore": (cmd_explore, ARGS), "shop": (cmd_shop, ARGS),
    "inv": (cmd_inv, NOARGS), "equip": (cmd_equip, ARGS), "use": (cmd_use, ARGS),
    "upgrade": (cmd_upgrade, ARGS), "market": (cmd_market, NOARGS), "sell": (cmd_sell, ARGS),
    "bounty": (cmd_bounty, ARGS), "vault": (cmd_vault, ARGS), "missions": (cmd_missions, NOARGS),
    "daily": (cmd_daily, NOARGS), "div": (cmd_div, ARGS), "ref": (cmd_ref, NOARGS),
    "report": (cmd_report, NOARGS),
}

FA = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


async def on_text(m: Message):
    """پیشوند «مانارچ …» و همین‌طور اسلش بدون / در گروه."""
    txt = (m.text or "").strip()
    if not txt:
        return
    if txt.startswith("/") and len(txt.split()) > 0 and not txt[1:2]:
        return
    if txt.startswith(config.PREFIX):
        body = txt[len(config.PREFIX):].strip()
    elif txt.startswith("/"):
        body = txt[1:].strip()
    else:
        return
    if not body:
        return
    parts = body.split(maxsplit=1)
    key = parts[0].lower().translate(FA)
    arg = (parts[1] if len(parts) > 1 else "") or ""
    entry = None
    for name, aliases in ALIASES.items():
        if key == name or key in [a.lower() for a in aliases]:
            entry = COMMAND_MAP.get(name)
            break
    if not entry:
        await reply(m, "❔ دستور ناشناخته — <code>/help</code> یا «مانارچ راهنما»")
        return
    fn, takes_args = entry
    co = CommandObject(prefix="bot", command=key, args=arg or None)
    try:
        await fn(m, co) if takes_args else await fn(m)
    except Exception:
        log.exception("alias dispatch failed: %s", key)


def burst_drop(uid: int) -> bool:
    """سقفِ انفجار: بیش از SPAM_MAX+۳ درخواست در پنجره → پاسخ بی‌صدا دور ریخته می‌شود.

    ربات نباید با «هشدارِ هشدار» خودش اسپم‌ساز شود؛ پس اینجا پیامی فرستاده نمی‌شود.
    """
    t = now()
    q = [x for x in _BURST.get(int(uid), []) if t - x < config.SPAM_WINDOW]
    q.append(t)
    _BURST[int(uid)] = q[-30:]
    return len(q) > config.SPAM_MAX + 3


def _wrap_cmd(name: str, fn, takes_args: bool):
    async def handler(m: Message, co: CommandObject = None):
        if burst_drop(m.from_user.id):
            return None
        if takes_args:
            return await fn(m, co)
        return await fn(m)
    handler.__name__ = f"cmd_{name}"
    handler.__doc__ = fn.__doc__
    return handler


_BURST_WARN = {}         # uid -> ts : یک هشدار در هر ۹۰ ثانیه، بقیه بی‌صدا


async def _burst_notice(event):
    """بازخوردِ سقف نرخ: فقط یک بار، تا خودِ ربات اسپم‌ساز نشود."""
    uid = int(event.from_user.id)
    t = now()
    if t - float(_BURST_WARN.get(uid) or 0) < 90:
        return
    _BURST_WARN[uid] = t
    try:
        if isinstance(event, Message):
            await event.answer("⏳ <b>RATE LIMIT</b> — MONARCH از اسپم خوشش نمی‌آید؛ "
                               "چند لحظه صبر کن، جهان همان‌جا می‌ماند.")
        else:
            await event.answer("⏳ کمی آهسته‌تر، فرمانده.")
    except Exception:
        pass


@router.message.outer_middleware()
async def burst_guard(handler, event, data):
    """سقفِ انفجار روی همه‌ی مسیرها (اسلش/متن آزاد) — پاسخ‌های اضافه بی‌صدا می‌افتند."""
    uid = getattr(getattr(event, "from_user", None), "id", None)
    if uid is not None and burst_drop(int(uid)):
        await _burst_notice(event)
        return None
    return await handler(event, data)


@router.callback_query.outer_middleware()
async def burst_guard_cb(handler, event, data):
    uid = getattr(getattr(event, "from_user", None), "id", None)
    if uid is not None and burst_drop(int(uid)):
        await _burst_notice(event)
        return None
    return await handler(event, data)


def reg_slash(dp):
    """ثبت رسمی اسلش + mirror های فارسی (ترتیب: اسلش اول، متن آزاد آخر)."""
    for name, (fn, takes_args) in COMMAND_MAP.items():
        dp.message.register(_wrap_cmd(name, fn, takes_args), Command(name))
    dp.message.register(on_text, F.text)
