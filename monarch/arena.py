# 🏆 Arena Engine — لدر رتبه‌بندی؛ فصل هفتگی، matchmaking بر اساس rating
import math
import random

import config
import db
from db import now


def season_key() -> str:
    d = db.local_now()
    return f"S{(int(d.strftime('%j')) // config.ARENA_SEASON_DAYS) + 1}-{d.year}"


def ensure_season() -> dict:
    cur = season_key()
    st = db.db().getv("arena_season", {}) or {}
    if st.get("season") == cur:
        return st
    prev = dict(st)
    if prev.get("season"):
        settle_season(prev)
    st = dict(season=cur, started=now(), board={})
    db.db().setv("arena_season", st)
    return st


def rating_of(uid: int) -> float:
    p = db.db().player(uid) or {}
    return float(p.get("arena_rating") or 1000)


def find_match(uid: int) -> dict:
    """حریف هم‌سطح؛ بازه با هر جست‌وجو گشادتر می‌شود (هیچ‌وقت صف بی‌انتها نمی‌ماند)."""
    ensure_season()
    r = rating_of(uid)
    p = db.db().player(uid) or {}
    for band in (60, 130, 260, 520, 1200):
        rows = db.db().q("""SELECT user_id,name,rank,arena_rating,hp,max_hp FROM players
                            WHERE user_id<>? AND dead_until<? AND rank BETWEEN ? AND ?
                              AND ABS(arena_rating-?)<=? AND xp>0
                            ORDER BY ABS(arena_rating-?) LIMIT 6""",
                         (int(uid), now(), max(1, int(p.get("rank") or 1) - 2),
                          int(p.get("rank") or 1) + 2, r, band, r))
        rows = [x for x in rows if not (x.get("hp") or 0) <= 0]
        if rows:
            return dict(ok=True, opp=random.choice(rows), band=band)
    return dict(ok=False, msg="🏆 رقیب هم‌سطح پیدا نشد — فصل را با /hunt شروع کن.")


def challenge(uid: int, chat: dict, opp_uid: int = None) -> dict:
    import player as PL
    p = PL.get(uid)
    if not p:
        return dict(ok=False, msg="🔒 /start")
    if PL.on_cd(uid, "arena"):
        return dict(ok=False, msg=f"⏳ {PL.cd_left(uid, 'arena'):.0f} ثانیه.")
    left = arena_left(uid)
    if left <= 0:
        return dict(ok=False, msg="🏆 سهمیه‌ی روزانه‌ی آرنا تمام شد (۶ نبرد).")
    if PL.is_dead(p):
        return dict(ok=False, msg="☠️ عامل در Recovery Mode است.")
    if not opp_uid:
        fm = find_match(uid)
        if not fm.get("ok"):
            return fm
        opp_uid = int(fm["opp"]["user_id"])
    if int(opp_uid) == int(uid):
        return dict(ok=False, msg="🚫 دوئل با خود؟ MONARCH رد می‌کند.")
    o = PL.get(opp_uid)
    if not o:
        return dict(ok=False, msg="🔒 حریف ثبت‌شده نیست.")
    if PL.is_dead(o):
        return dict(ok=False, msg="☠️ حریف down است — «/duel» بعداً.")
    import combat
    res = combat.start(uid, "arena", chat=chat, opp_uid=opp_uid)
    if res.get("ok"):
        st = res["state"]
        st["arena"] = True
        st["meta"]["arena"] = True
        st["meta"]["opp_uid"] = int(opp_uid)
        combat._save(res["cid"], st)
        db.db().apply(uid, arena_fights=int(p.get("arena_fights") or 0) + 1)
        mark_used(uid)          # سهمیه‌ی روزانه هنگام ورود کسر می‌شود (ضد اسپمِ آرنا)
    return res


def arena_left(uid: int) -> int:
    p = db.db().player(uid) or {}
    today = db.local_day()
    used = 0 if p.get("day") != today else int((db.jload(p.get("flags"), {}) or {}).get("arena_used", 0))
    return max(0, config.ARENA_DAILY - used)


def mark_used(uid: int):
    import player as PL
    p = PL.get(uid)
    if not p:
        return
    PL.roll_missions(uid)
    fl = db.jload(p.get("flags"), {}) or {}
    fl["arena_used"] = int(fl.get("arena_used", 0)) + 1
    PL.set_row(uid, flags=db.jdump(fl))


def settle(win_uid: int, lose_uid: int, win_score: int = 1, lose_score: int = 0) -> dict:
    """Elo با K متغیر؛ هیچ‌چیز با پول خریده نمی‌شود."""
    rw, rl = rating_of(win_uid), rating_of(lose_uid)
    exp_w = 1 / (1 + 10 ** ((rl - rw) / 400))
    k = config.ARENA_K * (1.25 if rl > rw else 0.9)
    new_w = round(rw + k * (1 - exp_w), 1)
    new_l = round(max(800, rl - k * exp_w), 1)
    d = db.db()
    d.apply(win_uid, arena_rating=new_w,
            arena_wins=int((d.player(win_uid) or {}).get("arena_wins") or 0) + 1,
            arena_fights=int((d.player(win_uid) or {}).get("arena_fights") or 0) + 1)
    d.apply(lose_uid, arena_rating=new_l,
            arena_losses=int((d.player(lose_uid) or {}).get("arena_losses") or 0) + 1,
            arena_fights=int((d.player(lose_uid) or {}).get("arena_fights") or 0) + 1)
    tier = tier_of(new_w)
    import player as PL
    PL.add_res(win_uid, credits=round(240 + new_w * 0.35, 0), fdata=1)
    PL.add_xp(win_uid, 16)
    return dict(ok=True, win=new_w, lose=new_l, tier=tier,
                msg=f"🏆 <b>RATING UPDATED</b>\n🟢 {PL.name_of(win_uid)}: {rw:.0f} → <b>{new_w:.0f}</b>\n"
                    f"🔴 {PL.name_of(lose_uid)}: {rl:.0f} → <b>{new_l:.0f}</b>\n"
                    f"🎖 رده‌ی آرنا: <b>{tier['name']}</b>")


def tier_of(rating: float) -> dict:
    for t in TIERS[::-1]:
        if rating >= t["min"]:
            return t
    return TIERS[0]


TIERS = [dict(key="unranked", name="Unranked", emj="⚪", min=0),
         dict(key="bronze", name="Bronze Clearance", emj="🥉", min=1000),
         dict(key="silver", name="Silver Clearance", emj="🥈", min=1150),
         dict(key="gold", name="Gold Clearance", emj="🥇", min=1320),
         dict(key="platinum", name="Alpha Clearance", emj="💠", min=1500),
         dict(key="monarch", name="MONARCH Class", emj="👑", min=1700)]


def ladder(limit: int = 10) -> list:
    return db.db().q("""SELECT user_id,name,rank,arena_rating,arena_wins,arena_losses FROM players
                        ORDER BY arena_rating DESC LIMIT ?""", (limit,))


def board_text(uid: int = None) -> str:
    ensure_season()
    rows = ladder(10)
    st = db.db().getv("arena_season", {}) or {}
    lines = [f"🏆 <b>ARENA LADDER</b> · <code>{st.get('season','—')}</code>",
             (f"<i>سهمیه‌ی امروز تو: {arena_left(int(uid))}/{config.ARENA_DAILY}</i>" if uid else
              f"<i>سهمیه‌ی روزانه‌ی هر عامل: {config.ARENA_DAILY} نبرد</i>"), ""]
    for i, r in enumerate(rows, 1):
        t = tier_of(float(r.get("arena_rating") or 1000))
        lines.append(f"{i}. {t['emj']} <b>{r['name']}</b> · <code>{float(r['arena_rating']):.0f}</code> "
                     f"<i>{int(r.get('arena_wins') or 0)}W/{int(r.get('arena_losses') or 0)}L</i>")
    if not rows:
        lines.append("<i>لدر خالی است — «/duel» اولین دوئل را ثبت می‌کند.</i>")
    return "\n".join(lines)


def settle_season(st: dict):
    """پایان فصل: جایزه بر اساس رده."""
    rows = ladder(20)
    import player as PL
    for i, r in enumerate(rows, 1):
        t = tier_of(float(r.get("arena_rating") or 1000))
        prize = max(0, round(40000 / i, 0))
        PL.add_res(int(r["user_id"]), credits=prize, cores=3 if i <= 3 else 1)
        PL.add_xp(int(r["user_id"]), 60)
        db.db().feed("arena_season", f"{st.get('season')}:{r['user_id']}:{i}")
    db.db().setv("arena_last_payout", dict(season=st.get("season"), n=len(rows)))


def season_report() -> str:
    last = db.db().getv("arena_last_payout", {}) or {}
    if not last:
        return "🏆 فصل آرنا در جریان است؛ پایانی در کار نیست."
    return f"🏆 <b>SEASON {last.get('season')}</b> — جایزه به {int(last.get('n') or 0)} عامل پرداخت شد."
