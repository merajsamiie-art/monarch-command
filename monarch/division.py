# 🏢 Division Engine — سازمان‌های بازیکنان: رادار، آزمایشگاه، خزنه، پدافند، مهندسی
import random

import config
import db
from db import now

FACILITIES = {
    "radar": dict(name="📡 Radar Array", desc="+۱۲٪ بازدهی هر سطح روی ردیابی سیگنال",
                  effect="track"),
    "lab": dict(name="🔬 Laboratory", desc="تحلیل سریع‌تر و شکست کمتر (هر سطح −۳٪ ریسک)",
                effect="research"),
    "storage": dict(name="📦 Secure Storage", desc="ظرفیت خزنه و محافظت در برابر Drop"),
    "defense": dict(name="🛡 Defense Grid", desc="+۵٪ دفاع بازیکنان در نبرد از باس/راید"),
    "engineering": dict(name="⚙️ Engineering", desc="کاهش زمان کاوش و هزینه‌ی ارتقا"),
}

ROLES = ("founder", "commander", "analyst", "agent")


def create(uid: int, name: str, tag: str) -> dict:
    import player as PL
    p = PL.get(uid)
    if not p:
        return dict(ok=False, msg="🔒 /start")
    if member_of(uid):
        return dict(ok=False, msg="🏢 تو عضو یک Division هستی — اول «/div leave».")
    name = (name or "").strip()[:22]
    tag = (tag or "").strip().upper()[:4]
    if len(name) < 3 or len(tag) < 2:
        return dict(ok=False, msg="🏷 نام حداقل ۳ حرف و برچسب ۲ تا ۴ حرف لازم دارد.")
    cost = config.DIV_CREATE_COST
    if float(p.get("credits") or 0) < cost:
        return dict(ok=False, msg=f"🪙 تأسیس Division {cost:,} MC است — الان {float(p['credits']):,.0f}.")
    d = db.db()
    if d.one("SELECT id FROM divisions WHERE name=? OR tag=?", (name, tag)):
        return dict(ok=False, msg="⚠️ این نام یا برچسب ثبت شده است.")
    PL.spend(uid, credits=-cost)
    cur = d.ex("INSERT INTO divisions(name,tag,owner_id,created_at,credits,facilities) "
               "VALUES(?,?,?,?,?,'{}')", (name, tag, int(uid), now(), 2000))
    did = cur.lastrowid
    d.ex("INSERT INTO div_users(user_id,div_id,role,joined) VALUES(?,?,?,?)", (int(uid), did, "founder", now()))
    db.db().feed("division", f"+{did}:{name}")
    return dict(ok=True, did=int(did), id=int(did), tag=tag, name=name,
                msg=(f"🏢 <b>DIVISION ACTIVATED</b>\n{p['name']} → <b>{name}</b> "
                              f"<code>[{tag}]</code>\n🪙 ۲۰۰۰ MC خزانه‌ی اولیه · «/div» برای مدیریت"))


def member_of(uid: int) -> dict:
    return db.db().one("SELECT * FROM div_users WHERE user_id=?", (int(uid),)) or {}


def div_of(did: int) -> dict:
    return db.db().one("SELECT * FROM divisions WHERE id=?", (did,)) or {}


def get_for(uid: int) -> dict:
    m = member_of(uid)
    if not m:
        return {}
    d = div_of(m["div_id"])
    d["role"] = m["role"]
    d["members"] = members(m["div_id"])
    return d


def members(did: int) -> list:
    return db.db().q("""SELECT u.user_id,u.role,u.joined,u.contrib,p.name,p.rank,p.power_cache
                        FROM div_users u LEFT JOIN players p ON p.user_id=u.user_id
                        WHERE u.div_id=? ORDER BY u.contrib DESC""", (did,))


def facility_of(uid: int, key: str) -> int:
    m = member_of(uid)
    if not m:
        return 0
    d = div_of(m["div_id"])
    import json
    try:
        fac = json.loads(d.get("facilities") or "{}")
    except Exception:
        fac = {}
    return int(fac.get(key, 0))


def fac_cost(level: int) -> dict:
    k = 1 + level
    return dict(credits=int(config.DIV_FAC_BASE * (config.DIV_FAC_STEP ** k)),
                mats=int(6 * k), cells=int(4 * k), cores=1 if level >= 3 else 0)


def fac_up(uid: int, key: str) -> dict:
    m = member_of(uid)
    if not m:
        return dict(ok=False, msg="🏢 تو Division نداری.")
    if m["role"] not in ("founder", "commander"):
        return dict(ok=False, msg="🔒 فقط فرمانده می‌تواند ساخت‌وساز کند.")
    if key not in FACILITIES:
        return dict(ok=False, msg="⚙️ تسهیلات ناشناخته.")
    d = div_of(m["div_id"])
    import json
    fac = json.loads(d.get("facilities") or "{}")
    lvl = int(fac.get(key, 0))
    if lvl >= config.DIV_FAC_MAX:
        return dict(ok=False, msg="⚙️ سقف مهندسی MONARCH reached.")
    c = fac_cost(lvl)
    if float(d.get("credits") or 0) < c["credits"]:
        return dict(ok=False, msg=(f"🏦 خزانه کم است: {c['credits']:,} MC لازم · موجود {float(d['credits']):,.0f}. "
                                   f"«/div deposit»"))
    div_spend(m["div_id"], **{k: -v for k, v in c.items() if k != "credits"})
    fac[key] = lvl + 1
    db.db().ex("UPDATE divisions SET facilities=? WHERE id=?", (json.dumps(fac), m["div_id"]))
    return dict(ok=True, msg=(f"⚙️ <b>{FACILITIES[key]['name']}</b> → سطح {lvl + 1}\n"
                              f"🏦 −{c['credits']:,} MC · 🔩{c['mats']} · 🔋{c['cells']}\n"
                              f"<i>{FACILITIES[key]['desc']}</i>"))


DIV_RES = ("credits", "cores", "mats", "cells", "dna", "fdata")


def div_spend(did: int, **deltas):
    d = div_of(did)
    fields = {}
    for k, v in deltas.items():
        if k in DIV_RES:
            fields[k] = max(0.0, float(d.get(k) or 0) + float(v))
    if fields:
        cols = ",".join(f"{k}=?" for k in fields)
        db.db().ex(f"UPDATE divisions SET {cols} WHERE id=?", tuple(fields.values()) + (did,))


def credit_activity(uid: int, kind: str, amount: float = 1):
    """فعالیت اعضا → سهم Division + XP سازمان."""
    m = member_of(uid)
    if not m:
        return
    db.db().ex("UPDATE div_users SET contrib = contrib + ? WHERE user_id=?", (amount, int(uid)))
    xp = {"track": 1, "sample": 2, "hunt_win": 4, "boss": 6, "raid": 8, "exped": 3, "lab": 5,
          "puzzle": 2}.get(kind, 1) * amount
    share = {"hunt_win": 60, "boss": 140, "raid": 90, "exped": 45, "lab": 40}.get(kind, 0) * amount
    d = div_of(m["div_id"])
    div_spend(m["div_id"], credits=share)
    db.db().ex("UPDATE divisions SET xp = xp + ? WHERE id=?", (xp, m["div_id"]))
    lvl = int(d.get("level") or 1)
    need = 400 * lvl * (1 + 0.35 * lvl)
    if float(d.get("xp") or 0) >= need:
        db.db().ex("UPDATE divisions SET level=level+1, xp=xp-? WHERE id=?", (need, m["div_id"]))
        db.db().feed("div_level", f"{m['div_id']}→{lvl + 1}")


def deposit(uid: int, amount: float) -> dict:
    m = member_of(uid)
    if not m:
        return dict(ok=False, msg="🏢 Division نداری.")
    import player as PL
    p = PL.get(uid)
    amt = max(0.0, min(float(amount or 0), float(p.get("credits") or 0)))
    if amt < 50:
        return dict(ok=False, msg="🪙 حداقل واریز ۵۰ MC.")
    PL.spend(uid, credits=-amt)
    div_spend(m["div_id"], credits=amt)
    return dict(ok=True, msg=f"🏦 <b>+{amt:,.0f} MC</b> به خزانه‌ی Division واریز شد.")


def withdraw(uid: int, amount: float) -> dict:
    m = member_of(uid)
    if not m or m["role"] not in ("founder", "commander"):
        return dict(ok=False, msg="🔒 فقط فرمانده برداشت می‌کند.")
    import player as PL
    d = div_of(m["div_id"])
    amt = min(float(amount or 0), float(d.get("credits") or 0))
    if amt < 1:
        return dict(ok=False, msg="🏦 خزانه خالی است.")
    div_spend(m["div_id"], credits=-amt)
    PL.add_res(uid, credits=amt)
    return dict(ok=True, msg=f"🏦 <b>−{amt:,.0f} MC</b> از خزانه (ثبت شد).")


def invite_code(did: int) -> str:
    return f"DIV-{did:04d}"


def join(uid: int, code: str) -> dict:
    m = member_of(uid)
    if m:
        return dict(ok=False, msg="🏢 تو در یک Division دیگر هستی.")
    try:
        did = int(str(code).replace("DIV-", "").strip())
    except Exception:
        return dict(ok=False, msg="🔑 کد نامعتبر — شکل: DIV-0007")
    d = div_of(did)
    if not d:
        return dict(ok=False, msg="🔑 چنین Division‌ای وجود ندارد.")
    if len(members(did)) >= config.DIV_MAX_MEMBERS:
        return dict(ok=False, msg="🏢 ظرفیت تکمیل است.")
    db.db().ex("INSERT OR REPLACE INTO div_users(user_id,div_id,role,joined) VALUES(?,?,?,?)",
               (int(uid), did, "agent", now()))
    import player as PL
    return dict(ok=True, msg=f"🏢 <b>ASSIGNED</b> — {d['name']} <code>[{d['tag']}]</code>\n"
                             f"خوش‌آمد {PL.name_of(uid)}. رادار روشن است.")


def leave(uid: int) -> dict:
    m = member_of(uid)
    if not m:
        return dict(ok=False, msg="🏢 Division نداری.")
    d = div_of(m["div_id"])
    if int(d.get("owner_id") or 0) == int(uid):
        return dict(ok=False, msg="🔒 موسس نمی‌تواند خارج شود — «/div disband».")
    db.db().ex("DELETE FROM div_users WHERE user_id=?", (int(uid),))
    return dict(ok=True, msg=f"🏢 از {d['name']} خارج شدی.")


def disband(uid: int) -> dict:
    m = member_of(uid)
    if not m or int(div_of(m["div_id"]).get("owner_id") or 0) != int(uid):
        return dict(ok=False, msg="🔒 فقط موسس.")
    db.db().ex("DELETE FROM div_users WHERE div_id=?", (m["div_id"],))
    db.db().ex("DELETE FROM divisions WHERE id=?", (m["div_id"],))
    return dict(ok=True, msg="🗑 <b>DIVISION DEACTIVATED</b> — پرونده بایگانی شد.")


def promote(uid: int, target: int) -> dict:
    m = member_of(uid)
    if not m or m["role"] != "founder":
        return dict(ok=False, msg="🔒 فقط موسس ارتقا می‌دهد.")
    t = member_of(target)
    if not t or t["div_id"] != m["div_id"]:
        return dict(ok=False, msg="👤 آن فرد در Division تو نیست.")
    role = "commander" if t["role"] != "commander" else "analyst"
    db.db().ex("UPDATE div_users SET role=? WHERE user_id=?", (role, int(target)))
    return dict(ok=True, msg=f"🎖 نقش تازه: <b>{role}</b>")


def defense_bonus(uid: int) -> float:
    return 0.05 * facility_of(uid, "defense")


def card(uid: int) -> str:
    import ui
    d = get_for(uid)
    if not d:
        return ("🏢 <b>DIVISION REGISTRY</b>\n\n<i>شما به هیچ Division متصل نیستید.</i>\n"
                "«/div create <name> <tag>» · «/div join DIV-0001»")
    import json
    fac = json.loads(d.get("facilities") or "{}")
    lines = [f"🏢 <b>{d['name']}</b> <code>[{d['tag']}]</code> · Level {d['level']}",
             f"🪙 خزانه {float(d.get('credits') or 0):,.0f} MC · 💎{float(d.get('cores') or 0):g} · "
             f"🔩{float(d.get('mats') or 0):g} · 🔋{float(d.get('cells') or 0):g}",
             f"✨ XP سازمان {float(d.get('xp') or 0):,.0f}/{400 * int(d['level']) * (1 + 0.35 * int(d['level'])):,.0f}",
             f"🏆 رکورد: {int(d.get('wins') or 0)}W / {int(d.get('loses') or 0)}L · Morale {float(d.get('morale') or 50):.0f}",
             f"🔑 کد عضویت: <code>{invite_code(d['id'])}</code>", "", "⚙️ <b>FACILITIES</b>"]
    for k, meta in FACILITIES.items():
        lvl = int(fac.get(k, 0))
        cost = fac_cost(lvl)
        lines.append(f"{meta['name']} {ui.bar(lvl, config.DIV_FAC_MAX, 6)} <code>L{lvl}</code> "
                     f"<i>({cost['credits']:,} MC)</i>")
    lines += ["", f"👥 <b>AGENTS ({len(d['members'])}/{config.DIV_MAX_MEMBERS})</b>"]
    for mrow in d["members"][:10]:
        lines.append(f"▪️ {mrow['role'][:4].upper()} · {mrow['name']} "
                     f"<i>R{mrow['rank']} · ⚔{float(mrow['contrib'] or 0):,.0f}</i>")
    return "\n".join(lines)


def top(limit: int = 8) -> list:
    return db.db().q("SELECT name,tag,level,xp,credits,wins,points FROM divisions "
                     "ORDER BY level DESC, xp DESC LIMIT ?", (limit,))


# ─────────── Division War (تاکتیکی، نه Damage Race) ───────────
LANES = config.DIV_WAR_LANES
LANE_NAME = dict(assault="⚔️ Assault", defense="🛡 Bulwark", intel="📡 Intel")
# سه‌روکه‌ی تاکتیکی: Assault > Intel > Defense > Assault
LANE_BEATS = {"assault": "intel", "intel": "defense", "defense": "assault"}


def war_open() -> dict:
    w = db.db().getv("war_state", None)
    if not w:
        return dict(active=False)
    if w.get("status") != "open":
        return dict(active=False, status=w.get("status"))
    left = float(w.get("ends_at", 0)) - now()
    return dict(active=True, ends_at=w["ends_at"], left=left, pairs=w.get("pairs", []))


def war_start(pairs: list, hours: float = 24) -> dict:
    w = dict(status="open", pairs=pairs, ends_at=now() + hours * 3600,
             deploys={}, seed=random.randint(1, 99999))
    db.db().setv("war_state", w)
    return w


def deploy(uid: int, alloc: dict) -> dict:
    """تخصیص نیرو به سه لاین (۰ تا ۱۰۰٪). جنگ با اطلاعات برنده می‌شود، نه با کلیک."""
    m = member_of(uid)
    if not m or m["role"] not in ("founder", "commander"):
        return dict(ok=False, msg="🔒 فرمانده/موسس تخصیص می‌دهد.")
    w = db.db().getv("war_state", {}) or {}
    if w.get("status") != "open":
        return dict(ok=False, msg="⚔️ جنگی فعال نیست.")
    mine = m["div_id"]
    if not any(mine in (p.get("a"), p.get("b")) for p in w.get("pairs", [])):
        return dict(ok=False, msg="⚔️ Division شما در این جنگ ثبت نشده.")
    total = sum(float(alloc.get(k, 0)) for k in LANES)
    if abs(total - 100) > 1:
        return dict(ok=False, msg=f"⚖️ مجموع تخصیص باید ۱۰۰ باشد (الان {total:g}).")
    w["deploys"][str(mine)] = {k: float(alloc.get(k, 0)) for k in LANES}
    db.db().setv("war_state", w)
    return dict(ok=True, msg="⚔️ <b>DEPLOYMENT SEALED</b>\n"
                             + " · ".join(f"{LANE_NAME[k]} {w['deploys'][str(mine)][k]:g}%" for k in LANES))


def war_resolve() -> list:
    """تسویه‌ی جنگ: برتری لاین + مزیت رادار + روحیه."""
    import json
    w = db.db().getv("war_state", {}) or {}
    if w.get("status") != "open":
        return []
    results = []
    for pair in w.get("pairs", []):
        a, b = pair.get("a"), pair.get("b")
        da, db_ = div_of(a), div_of(b)
        if not da or not db_:
            continue
        A = (w.get("deploys", {}) or {}).get(str(a)) or {k: 33.3 for k in LANES}
        B = (w.get("deploys", {}) or {}).get(str(b)) or {k: 33.3 for k in LANES}
        sa = sb = 0.0
        detail = []
        for lane in LANES:
            fa, fb = float(A.get(lane, 0)), float(B.get(lane, 0))
            rad_a = facility_of(int(da["owner_id"]), "radar")
            rad_b = facility_of(int(db_["owner_id"]), "radar")
            va = fa * (1 + 0.03 * rad_a) + (10 if LANE_BEATS[lane] and fb < fa * 0.75 else 0)
            vb = fb * (1 + 0.03 * rad_b) + (10 if LANE_BEATS[lane] and fa < fb * 0.75 else 0)
            # مزیت چرخه‌ای: لاینِ شکارچی، لاینِ طعمه را می‌شکند
            if LANE_BEATS[lane] == pair.get("focus", {}).get(lane):
                va *= 1.12
            bonus_a = 1 + 0.05 * (int(da.get("level") or 1) - 1) + float(da.get("morale") or 50) / 400
            bonus_b = 1 + 0.05 * (int(db_.get("level") or 1) - 1) + float(db_.get("morale") or 50) / 400
            va *= bonus_a
            vb *= bonus_b
            sa += va
            sb += vb
            detail.append(f"{LANE_NAME[lane]} <code>{va:.0f}</code> vs <code>{vb:.0f}</code>")
        winner = a if sa > sb else (b if sb > sa else 0)
        for did, sc, won in ((a, sa, winner == a), (b, sb, winner == b)):
            d = div_of(did)
            db.db().ex("UPDATE divisions SET wins=wins+?, points=points+?, morale=morale+? WHERE id=?",
                       (1 if won else 0, int(round(sc / 10)), 4 if won else -3, did))
            db.db().ex("UPDATE divisions SET morale=MIN(100,MAX(5,morale+?)) WHERE id=?",
                       (4 if won else -3, did))
            pool = 3000 + 400 * int(d.get("level") or 1)
            if won:
                div_spend(did, credits=pool)
        results.append(dict(a=a, b=b, sa=round(sa, 1), sb=round(sb, 1), winner=winner, detail=detail))
    w["status"] = "closed"
    w["results"] = results
    db.db().setv("war_state", w)
    return results
