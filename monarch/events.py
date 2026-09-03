# 🌍 Event Engine — ضربان ۲۴/۷ بازی (بی‌صدا در پس‌زمینه، پیام‌ها فشرده)
import asyncio
import logging
import random

import balance
import bosses
import config
import db
import titans as TN
from db import now

log = logging.getLogger("monarch.events")


def seed_admin_settings():
    """اولین اجرا: تنظیمات پیش‌فرض + بیدار کردن دیتابیس."""
    d = db.db()
    if not d.getv("boot_version"):
        d.setv("boot_version", 2)
        d.setv("last_alert", 0)
    return True


def active_chats(limit: int = 40) -> list:
    """چت‌هایی که واقعاً بازیکن فعال دارند (نه لیست بی‌انتها)."""
    rows = db.db().q("""SELECT c.* FROM chats c
                        WHERE c.kind='group' AND (c.last_news IS NULL OR 1=1)
                          AND EXISTS (SELECT 1 FROM chat_users u WHERE u.chat_id=c.chat_id
                                      AND u.last_active > ?)
                        ORDER BY (SELECT MAX(last_active) FROM chat_users u WHERE u.chat_id=c.chat_id) DESC
                        LIMIT ?""", (now() - 3 * 86400, limit))
    return rows


def ensure_chat(chat_id: int, title: str = None, kind: str = "group") -> dict:
    d = db.db()
    r = d.one("SELECT * FROM chats WHERE chat_id=?", (int(chat_id),))
    if not r:
        zone = random.choice(list(TN.ENVS.keys()))
        danger = random.randint(1, 3)
        d.ex("INSERT INTO chats(chat_id,kind,zone,danger,title,created_at) VALUES(?,?,?,?,?,?)",
             (int(chat_id), kind, zone, danger, (title or "")[:48], now()))
        r = d.one("SELECT * FROM chats WHERE chat_id=?", (int(chat_id),))
    return r


def set_zone(chat_id: int, zone: str) -> bool:
    if zone not in TN.ENVS:
        return False
    ensure_chat(chat_id)
    db.db().ex("UPDATE chats SET zone=?, danger=MIN(5,MAX(1,danger+?)) WHERE chat_id=?",
               (zone, 0, int(chat_id)))
    return True


def zone_of(chat_id: int) -> str:
    r = db.db().one("SELECT zone FROM chats WHERE chat_id=?", (int(chat_id),))
    return (r or {}).get("zone") or "ocean"


def bump_danger(chat_id: int, delta: int = 1):
    db.db().ex("UPDATE chats SET danger=MIN(5,MAX(1,danger+?)) WHERE chat_id=?", (int(delta), int(chat_id)))


# ─────────── چرخه‌ها ───────────
def cycle_bosses():
    """زلزله → اسپاون باس در گروه‌های فعال (ضداسپم: حداکثر ۱ هشدار / هر چت / پنجره)."""
    fired = []
    for chat in active_chats(12):
        if bosses.active(chat["chat_id"]):
            continue
        if now() - float(chat.get("last_alert") or 0) < config.ALERT_COOLDOWN_CHAT:
            continue
        if random.random() > config.BOSS_CHANCE:
            continue
        res = bosses.spawn(chat["chat_id"])
        if res.get("ok"):
            db.db().ex("UPDATE chats SET last_alert=? WHERE chat_id=?", (now(), chat["chat_id"]))
            bump_danger(chat["chat_id"], 1)
            fired.append(res)
    return fired


def cycle_raid():
    """برنامه‌ریزی رید جهانی: سه‌شنبه و جمعه، ساعت ۲۱ تهران."""
    st = db.db().getv("raid", {}) or {}
    if st.get("status") == "live" and float(st.get("ends_at", 0)) > now():
        return {}
    if st.get("status") == "live":
        import raid
        return dict(expired=raid.finish(won=False))
    wd = db.weekday_local()
    hh = db.local_hour()
    key = f"raid_sched:{db.local_day()}:{wd}"
    if wd in config.RAID_WEEKDAYS and hh >= 20 and not db.db().getv(key):
        db.db().setv(key, 1)
        import raid
        return dict(started=raid.start())
    return {}


def cycle_division_war():
    """جنگ Division: پنجشنبه ۲۰:۰۰ شروع، ۲۴ ساعت مهلت تخصیص."""
    w = db.db().getv("war_state", {}) or {}
    if w.get("status") == "open" and float(w.get("ends_at", 0)) <= now():
        res = __import__("division").war_resolve()
        return dict(resolved=res)
    if w.get("status") == "open":
        return {}
    wd, hh = db.weekday_local(), db.local_hour()
    key = f"war_sched:{db.local_day()}"
    if wd in (5,) and hh >= 20 and not db.db().getv(key):
        db.db().setv(key, 1)
        divs = db.db().q("SELECT id,name,level,xp FROM divisions ORDER BY xp DESC LIMIT 6")
        if len(divs) >= 2:
            pairs = [dict(a=divs[i]["id"], b=divs[i + 1]["id"], focus={}) for i in range(0, len(divs) - 1, 2)]
            __import__("division").war_start(pairs, hours=24)
            return dict(started=pairs)
    return {}


def cycle_news(bot, interval_h: float = None):
    """خبر فشرده‌ی گروه (حداکثر هر ۴ ساعت در هر چت) — یک پیام، چند خط."""
    for chat in active_chats(8):
        if now() - float(chat.get("last_news") or 0) < (interval_h or config.GROUP_NEWS_HOURS) * 3600:
            continue
        db.db().ex("UPDATE chats SET last_news=? WHERE chat_id=?", (now(), chat["chat_id"]))
        txt = news_packet(chat)
        if txt:
            try:
                asyncio.get_event_loop().create_task(_send(bot, chat["chat_id"], txt))
            except RuntimeError:
                pass


async def _send(bot, chat_id, text):
    from aiogram.exceptions import TelegramForbiddenError
    try:
        await bot.send_message(chat_id, text)
    except (TelegramForbiddenError, Exception):
        pass


def news_packet(chat: dict) -> str:
    """بسته‌ی خبری: وضعیت منطقه + سیگنال + باس + رید + رنکینگ — همه در یک پیام."""
    import ui
    import player as PL
    import raid as RA
    zone = chat.get("zone") or "ocean"
    st = RA.state()
    act = bosses.active(chat["chat_id"])
    lines = [f"{E('radar')} <b>MONARCH DAILY FEED</b> · {TN.ENVS.get(zone, zone)}",
             f"▪️ خطر منطقه: <code>{'▰' * int(chat.get('danger') or 1)}{'▱' * (5 - int(chat.get('danger') or 1))}</code>"]
    if act:
        b = bosses.by_id(act["bid"])
        lines.append(f"🕹 تهدید فعال: <b>{b.get('name')}</b> · {ui.bar(act['state'].get('hp', 0), act['state'].get('max_hp', 1))} "
                     f"⏱ {ui.eta(float(chat.get('boss_until') or 0))}")
    if st and not st.get("over"):
        lines.append(f"🌒 <b>WORLD RAID</b> — {st.get('name')} · HP {int(100 * float(st['hp']) / max(1.0, float(st['max_hp'])))}% · «/raid»")
    sig = random.choice(list(TN.TITANS.values()))
    if random.random() < 0.6:
        lines.append(f"📶 سیگنال تازه در {TN.ENVS.get(random.choice(list(TN.ENVS.keys())), '')} — «/track»")
    top = db.db().q("SELECT name,rank FROM players ORDER BY rank DESC, xp DESC LIMIT 3")
    if top:
        lines.append("🏆 برترین‌ها: " + " · ".join(f"{t['name'][:14]} (R{t['rank']})" for t in top))
    lines.append(f"<i>{E('atom')} {random.choice(LORE_LINES)}</i>")
    return "\n".join(lines)


LORE_LINES = [
    "هر تایتان یک پرونده است؛ هر پرونده یک هشدار.",
    "سکوت لرزه‌ای بدترین خبر است — یعنی نفس می‌کشد.",
    "MONARCH نمی‌جنگد تا مطمئن نشود؛ بعد هم دیگر عقب نمی‌نشیند.",
    "ضربه‌ی اتمی یک انتخاب است، نه یک عادت.",
    "آن‌ها از قبل اینجا بودند؛ ما تازه متوجه شدیم.",
    "تجهیزات تو را زنده نگه می‌دارد؛ پیوند تایتان تو را فرمانده می‌کند.",
    "هیچ غنیمتی رایگان نیست — ۱۰ دقیقه Recovery بهایش است.",
    "خاکسترِ یک تایتان، داده‌ی تایتان بعدی است.",
]


def E(key):
    import emoji
    return emoji.get(key)


def cycle_channel(bot):
    """پست‌های کانال: درس روزانه، باس‌نیوز، رنکینگ هفتگی."""
    hh = db.local_hour()
    d = db.db()
    if hh == config.TUTORIAL_HOUR and not d.getv(f"tut:{db.local_day()}"):
        d.setv(f"tut:{db.local_day()}", 1)
        import texts
        i = int(now() // 86400) % len(texts.LESSONS)
        lesson = texts.LESSONS[i]
        _dispatch(bot, config.CHANNEL_ID,
                  f"📖 <b>MONARCH MANUAL · درس {i+1:02d}</b>\n\n{lesson['title']}\n\n{lesson['body']}\n\n"
                  f"<i>🛰 {config.BRAND} — {config.CHANNEL_URL}</i>")
    if db.weekday_local() == config.RANK_DAY and hh == config.RANK_HOUR \
            and not d.getv(f"rank:{db.local_day()}"):
        d.setv(f"rank:{db.local_day()}", 1)
        _dispatch(bot, config.CHANNEL_ID, ranking_post())
    if hh == 9 and not d.getv(f"bossnews:{db.local_day()}"):
        d.setv(f"bossnews:{db.local_day()}", 1)
        bid = bosses.pick(random.choice(list(TN.ENVS.keys())), random.randint(2, 4))
        b = bosses.by_id(bid)
        _dispatch(bot, config.CHANNEL_ID,
                  f"👑 <b>BOSS NEWS</b>\n\n"
                  f"🚨 MONARCH ALERT — SEISMIC ACTIVITY DETECTED.\n\n"
                  f"🦖 TITAN: <b>{b['name']}</b>\n"
                  f"📍 LOCATION: {TN.ENVS.get((b.get('zones') or ['city'])[0], '—')}\n"
                  f"☢️ THREAT: <b>{'CRITICAL' if b['tier'] in ('LEGENDARY','ALPHA','WORLD') else 'SEVERE'}</b>\n\n"
                  f"<i>{b.get('lore','')}</i>\n\n"
                  f"▸ در گروه: <code>/boss</code> · <code>/raid join</code>")


def ranking_post() -> str:
    import player as PL
    import ui
    rows = PL.leaderboard("power", 12)
    lines = ["🏆 <b>ALPHA PROTOCOL — رنکینگ هفتگی</b>",
             "<i>قدرت = نبرد + تحقیق + پیوند؛ رتبه با پول نمی‌خرد.</i>", ""]
    medals = ["🥇", "🥈", "🥉"]
    for i, r in enumerate(rows, 1):
        lines.append(f"{medals[i-1] if i <= 3 else f'{i}.'} <b>{(r.get('name') or '')[:18]}</b> "
                     f"· <code>R{r.get('rank')}</code> · {ui.n(r.get('v'))}")
    dr = __import__("division").top(5)
    if dr:
        lines += ["", "🏢 <b>DIVISIONS</b>"]
        for i, d in enumerate(dr, 1):
            lines.append(f"{i}. {d['name']} <code>[{d['tag']}]</code> · L{d['level']} · "
                         f"{int(d['wins'])}W")
    import research
    rr = research.discovery_ranking(5)
    if rr:
        lines += ["", "🔬 <b>BEST RESEARCHERS</b>"]
        for row in rr:
            lines.append(f"▪️ {PL.name_of(int(row['user_id']))} — {int(row['c'])} پرونده‌ی باز‌شده")
    lines += ["", f"<i>🛰 {config.BRAND} · {config.GROUP_URL}</i>"]
    return "\n".join(lines)


def _dispatch(bot, chat_id, text):
    if not chat_id or not text:
        return
    try:
        asyncio.create_task(_send(bot, chat_id, text))
    except RuntimeError:
        pass


# ─────────── موتور ───────────
class Engine:
    def __init__(self, bot, interval: int = None):
        self.bot = bot
        self.interval = interval or config.EVENT_INTERVAL
        self.task = None
        self.tick_count = 0

    def start(self):
        self.task = asyncio.create_task(self.loop())

    def stop(self):
        if self.task:
            self.task.cancel()

    async def loop(self):
        log.info("🌍 Event Engine روشن — هر %d ثانیه", self.interval)
        while True:
            try:
                await asyncio.sleep(self.interval)
                self.tick_count += 1
                import combat
                combat.gc()
                fired = cycle_bosses()
                for res in fired:
                    _dispatch(self.bot, res["chat_id"], res["text"])
                r = cycle_raid()
                if r.get("started"):
                    _dispatch(self.bot, config.CHANNEL_ID, r["started"]["text"])
                    for chat in active_chats(12):
                        _dispatch(self.bot, chat["chat_id"], r["started"]["text"])
                w = cycle_division_war()
                if w.get("resolved"):
                    txt = "⚔️ <b>DIVISION WAR — نتایج</b>\n\n" + "\n\n".join(
                        f"🏢 {db.db().one('SELECT name FROM divisions WHERE id=?', (x['a'],))['name']} "
                        f"{x['sa']:.0f} vs {x['sb']:.0f} "
                        f"{db.db().one('SELECT name FROM divisions WHERE id=?', (x['b'],))['name']}"
                        for x in w["resolved"])
                    _dispatch(self.bot, config.CHANNEL_ID, txt)
                cycle_news(self.bot)
                cycle_channel(self.bot)
                if self.tick_count % 4 == 0:
                    try:
                        import player as PL
                        PL.recalc_power_cache()
                    except Exception:
                        pass
                for chat in active_chats(12):
                    for res in bosses.decay():
                        msg = (res.get("settled") or {}).get("msg")
                        if msg:
                            _dispatch(self.bot, res["chat_id"], f"🕹 <b>OPERATION UPDATE</b>\n{msg}")
            except asyncio.CancelledError:
                break
            except Exception:
                log.exception("event loop tick failed")
                await asyncio.sleep(20)
