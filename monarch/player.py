# 👤 Player Engine — پرونده‌ی عامل، تیک، مرگ/احیا، منابع، تجهیزات، رتبه
import math
import random

import balance
import config
import db
import emoji as E
from db import now

_RES_KEYS = ("credits", "cores", "dna", "cells", "mats", "fdata", "vault")


def ensure_player(uid: int, name: str = None, username: str = None) -> dict:
    uid = int(uid)
    d = db.db()
    row = d.player(uid)
    if row and row.get("max_hp"):
        if name and row.get("name") != name:
            d.apply(uid, name=name[:48])
            d.cache_flush(uid)
        return get(uid)
    hp = config.START_HP
    d.ex("""INSERT INTO players(user_id,name,username,created_at,last_seen,last_tick,rank,xp,
            hp,max_hp,energy,max_energy,resolve,max_resolve,credits)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(user_id) DO NOTHING""",
         (uid, (name or f"AGENT{uid}")[:48], username, now(), now(), now(), 1, 0,
          hp, hp, config.START_ENERGY, config.START_ENERGY, config.START_RESOLVE,
          config.START_RESOLVE, config.START_CREDITS))
    d.cache_flush(uid)
    db.db().feed("join", f"{uid}:{name}")
    return get(uid)


def get(uid: int) -> dict:
    row = db.db().player(int(uid))
    if not row or "user_id" not in row:
        return {}
    return dict(row)


def name_of(uid: int) -> str:
    p = get(uid)
    return p.get("name") or f"AGENT{uid}"


def set_row(uid: int, **fields):
    db.db().apply(int(uid), **fields)


def add_res(uid: int, **deltas):
    uid = int(uid)
    p = get(uid)
    if not p:
        return
    out = {}
    for k, v in deltas.items():
        if k not in _RES_KEYS or not v:
            continue
        out[k] = round(max(0.0, float(p.get(k) or 0) + float(v)), 3)
    if out:
        db.db().apply(uid, **out)


def spend(uid: int, **deltas) -> bool:
    """بررسی موجودی + کسر، اتمیک. اگر کم بیاورد False."""
    uid = int(uid)
    p = get(uid)
    if not p:
        return False
    for k, v in deltas.items():
        if k in _RES_KEYS and float(p.get(k) or 0) + float(v) < -0.001:
            return False
    add_res(uid, **deltas)
    return True


def can_afford(p: dict, **cost) -> bool:
    return all(float(p.get(k) or 0) >= float(v or 0) for k, v in cost.items())


# ─────────── تیک تنبل (lazy) ───────────
def tick(uid: int) -> dict:
    uid = int(uid)
    p = get(uid)
    if not p:
        return {}
    t = now()
    today = db.local_day()
    if p.get("day") != today or p.get("last_seen_day") != today:
        # چرخه‌ی شبانه: سهمیه‌های روزانه (آرنا/چک‌این/مأموریت) اینجا صفر می‌شوند
        db.db().apply(uid, day=today, last_seen_day=today, last_tick=t, last_seen=t)
        p = get(uid) or p
    dt = max(0.0, t - float(p.get("last_tick") or t))
    if dt < 5 and not p.get("dead_until"):
        db.db().apply(uid, last_seen=t)
        return p
    hours = min(config.TICK_CAP_H, dt / 3600.0)
    fields = dict(last_tick=t, last_seen=t)
    if is_dead(p):
        if t >= float(p["dead_until"]):
            respawn(uid, silent=True)
            p = get(uid)
        else:
            db.db().apply(uid, last_seen=t)
            return p
    else:
        mx_hp = float(p["max_hp"]) + balance.rank_stats(p["rank"])["hp"]
        fields["hp"] = round(min(mx_hp, float(p["hp"]) + config.HP_REGEN_H * hours), 2)
        fields["energy"] = round(min(float(p["max_energy"]),
                                    float(p["energy"]) + config.ENERGY_REGEN_H * hours), 2)
        fields["resolve"] = round(min(100.0, float(p.get("resolve") or 0) + config.RESOLVE_REGEN_H * hours), 2)
    db.db().apply(uid, **fields)
    return get(uid)


# ─────────── XP / رتبه ───────────
def add_xp(uid: int, amount: float) -> dict:
    uid = int(uid)
    p = get(uid) or {}
    xp = float(p.get("xp") or 0) + float(amount)
    rank = int(p.get("rank") or 1)
    gained = 0
    while xp >= balance.xp_need(rank) and rank < 40:
        xp -= balance.xp_need(rank)
        rank += 1
        gained += 1
    db.db().apply(uid, xp=round(xp, 2), rank=rank)
    out = dict(rank=rank, gained=gained, xp=round(xp, 2), need=balance.xp_need(rank))
    if gained:
        add_res(uid, credits=120 * gained * rank)
        db.db().feed("rankup", f"{uid}->{rank}")
    return out


def rank_label(p: dict) -> str:
    return balance.rank_title(int(p.get("rank") or 1))


# ─────────── مرگ / Recovery Mode ───────────
def is_dead(p: dict) -> bool:
    return bool(p and float(p.get("dead_until") or 0) > now())


def dead_left(p: dict) -> float:
    return max(0.0, float(p.get("dead_until") or 0) - now())


def die(uid: int, reason: str = "COMBAT", protect_legendary: bool = True) -> dict:
    """☠️ AGENT DOWN — ۱۰ دقیقه بازیابی + Drop بخشی از منابعِ محافظت‌نشده."""
    uid = int(uid)
    p = get(uid)
    if not p:
        return dict(drop={}, until=0)
    drop = {}
    for k, pct in (("credits", config.DROP_CREDIT), ("dna", config.DROP_RESOURCE),
                   ("cells", config.DROP_RESOURCE), ("mats", config.DROP_RESOURCE),
                   ("fdata", config.DROP_RESOURCE * 0.6)):
        if k in config.DROP_PROTECTED:
            continue
        amt = round(float(p.get(k) or 0) * pct, 2)
        if amt > 0:
            drop[k] = amt
    # 🏦 هرچه در خزنه‌ی Division است از Drop در امان است: اول از اعتبار خزنه کم می‌شود
    if drop.get("credits") and float(p.get("credits") or 0) > drop["credits"]:
        pass
    drop = {k: v for k, v in drop.items() if v > 0}
    if drop:
        add_res(uid, **{k: -v for k, v in drop.items()})
    db.db().apply(uid, dead_until=now() + config.RECOVERY_MINUTES * 60,
                  deaths=int(p.get("deaths") or 0) + 1, hp=1.0, energy=0.0)
    db.db().feed("death", f"{uid}:{reason}")
    return dict(ok=True, drop=drop, until=now() + config.RECOVERY_MINUTES * 60, reason=reason)


def respawn(uid: int, silent: bool = False) -> dict:
    uid = int(uid)
    p = get(uid) or {}
    mx = float(p.get("max_hp") or config.START_HP) + balance.rank_stats(p.get("rank"))["hp"]
    db.db().apply(uid, dead_until=0, hp=round(mx * config.INJURY_HP, 1),
                  energy=round(float(p.get("max_energy") or config.START_ENERGY) * 0.5, 1),
                  resolve=round(max(20.0, float(p.get("resolve") or 40) * 0.8), 1))
    if not silent:
        db.db().feed("respawn", str(uid))
    return get(uid)


# ─────────── خزنه ───────────
def vault_capacity(p: dict) -> float:
    import division
    lvl = division.facility_of(p["user_id"], "storage")
    return config.VAULT_BASE + config.VAULT_PER_DIV_LEVEL * lvl


def vault_store(uid: int, amount: float) -> dict:
    p = get(uid)
    cap = vault_capacity(p)
    room = cap - float(p.get("vault") or 0)
    amt = max(0.0, min(float(amount), room, float(p.get("credits") or 0)))
    if amt <= 0:
        return dict(ok=False, msg="🏦 خزنه پر است یا اعتباری نیست.")
    add_res(uid, credits=-amt, vault=amt)
    return dict(ok=True, msg=f"🏦 <b>{amt:,.0f} اعتبار</b> به خزنه‌ی سازمان منتقل شد — از Drop در امان.")


def vault_withdraw(uid: int, amount: float) -> dict:
    p = get(uid)
    amt = max(0.0, min(float(amount), float(p.get("vault") or 0)))
    if amt <= 0:
        return dict(ok=False, msg="🏦 خزنه خالی است.")
    add_res(uid, vault=-amt, credits=amt)
    return dict(ok=True, msg=f"🏦 <b>{amt:,.0f} اعتبار</b> از خزنه بیرون آمد.")


# ─────────── کول‌داون ───────────
def set_cd(uid: int, kind: str, secs: float):
    db.db().ex("INSERT INTO cooldowns(user_id,kind,until) VALUES(?,?,?) "
               "ON CONFLICT(user_id,kind) DO UPDATE SET until=excluded.until",
               (int(uid), kind, now() + float(secs)))


def cd_left(uid: int, kind: str) -> float:
    r = db.db().one("SELECT until FROM cooldowns WHERE user_id=? AND kind=?", (int(uid), kind))
    return max(0.0, float(r["until"]) - now()) if r else 0.0


def on_cd(uid: int, kind: str) -> bool:
    return cd_left(uid, kind) > 0


def clear_cd(uid: int, kind: str = None):
    if kind:
        db.db().ex("DELETE FROM cooldowns WHERE user_id=? AND kind=?", (int(uid), kind))
    else:
        db.db().ex("DELETE FROM cooldowns WHERE user_id=?", (int(uid),))


# ─────────── آیتم‌ها ───────────
def inv(uid: int) -> dict:
    rows = db.db().q("SELECT item_id, qty, equipped FROM items WHERE user_id=? AND qty>0", (int(uid),))
    return {r["item_id"]: dict(qty=r["qty"], equipped=bool(r["equipped"])) for r in rows}


def add_item(uid: int, iid: str, qty: int = 1):
    db.db().ex("INSERT INTO items(user_id,item_id,qty) VALUES(?,?,?) "
               "ON CONFLICT(user_id,item_id) DO UPDATE SET qty=qty+excluded.qty", (int(uid), iid, qty))


def take_item(uid: int, iid: str, qty: int = 1) -> bool:
    row = db.db().one("SELECT qty FROM items WHERE user_id=? AND item_id=?", (int(uid), iid))
    if not row or row["qty"] < qty:
        return False
    left = row["qty"] - qty
    if left <= 0:
        db.db().ex("DELETE FROM items WHERE user_id=? AND item_id=?", (int(uid), iid))
    else:
        db.db().ex("UPDATE items SET qty=? WHERE user_id=? AND item_id=?", (left, int(uid), iid))
    return True


def use_item(uid: int, iid: str) -> dict:
    from economy import ITEMS
    it = ITEMS.get(iid)
    if not it or it.get("kind") != "consumable":
        return dict(ok=False, msg="🎒 این آیتم مصرفی نیست.")
    if not take_item(uid, iid, 1):
        return dict(ok=False, msg="🎒 چیزی از این نوع نداری.")
    p = get(uid)
    u = it.get("use") or {}
    msg = []
    if u.get("hp"):
        mx = float(p["max_hp"])
        add_res(uid)
        db.db().apply(uid, hp=min(mx, float(p["hp"]) + u["hp"]))
        msg.append(f"❤️ +{u['hp']} HP")
    if u.get("energy"):
        db.db().apply(uid, energy=min(float(p["max_energy"]), float(p["energy"]) + u["energy"]))
        msg.append(f"🔋 +{u['energy']}")
    if u.get("resolve"):
        db.db().apply(uid, resolve=min(100.0, float(p.get("resolve") or 0) + u["resolve"]))
        msg.append(f"🧠 +{u['resolve']} تمرکز")
    if u.get("charge"):
        msg.append(f"☢️ شارژ نبرد بعدی +{u['charge']}%")
        add_res(uid, cells=0)
        db.db().apply(uid, energy=min(float(p["max_energy"]), float(p["energy"]) + u["charge"]))
    if u.get("clean"):
        msg.append(f"🧼 {u['clean']} وضعیت منفی پاک شد")
    if u.get("research"):
        import research
        last = db.db().getv(f"lasttarget:{uid}", None)
        if last:
            research.add_points(uid, last, u["research"], "beacon")
            msg.append(f"🔬 +{u['research']} تحقیق روی {last}")
        else:
            msg.append("🔬 هدف فعالی ثبت نشده")
    return dict(ok=True, msg=f"🎒 {it['name']} مصرف شد — " + " · ".join(msg))


def item_level(uid: int, iid: str, set_to=None):
    """سطح ارتقای تجهیز (۰ تا ۳)."""
    if set_to is not None:
        db.db().ex("UPDATE items SET level=? WHERE user_id=? AND item_id=?", (int(set_to), int(uid), iid))
        return int(set_to)
    row = db.db().one("SELECT level FROM items WHERE user_id=? AND item_id=?", (int(uid), iid))
    return int(row["level"] or 0) if row else 0


def equip(uid: int, iid: str) -> dict:
    """تجهیز در اسلاتِ خودش؛ هر اسلات یک آیتم (rig/weapon/module)."""
    from economy import ITEMS, SLOTS
    it = ITEMS.get(iid)
    if not it:
        return dict(ok=False, msg="⚙️ کد آیتم نامعتبر.")
    if it.get("kind") not in SLOTS:
        return dict(ok=False, msg="⚙️ فقط Rig/سلاح/ماژول مجهز می‌شود.")
    if not inv(uid).get(iid):
        return dict(ok=False, msg="🎒 این تجهیز را نداری.")
    slot = it.get("slot") or it.get("kind")
    rivals = [k for k, v in ITEMS.items() if (v.get("slot") or v.get("kind")) == slot]
    ph = ",".join("?" * len(rivals))
    db.db().ex(f"UPDATE items SET equipped=0 WHERE user_id=? AND item_id IN ({ph})",
               (int(uid), *rivals))
    db.db().ex("UPDATE items SET equipped=1 WHERE user_id=? AND item_id=?", (int(uid), iid))
    return dict(ok=True, msg=f"⚙️ <b>مجهز شد</b> — {it['name']}")


def unequip(uid: int, iid: str) -> dict:
    db.db().ex("UPDATE items SET equipped=0 WHERE user_id=? AND item_id=?", (int(uid), iid))
    return dict(ok=True, msg=f"⚙️ {iid} از حالت تجهیز خارج شد.")


# ─────────── ثبت فعالیت در چت ───────────
def note_chat(uid: int, chat_id: int):
    db.db().ex("INSERT INTO chat_users(chat_id,user_id,last_active) VALUES(?,?,?) "
               "ON CONFLICT(chat_id,user_id) DO UPDATE SET last_active=excluded.last_active",
               (int(chat_id), int(uid), now()))


def track_stat(uid: int, field: str, amount: int = 1):
    p = get(uid)
    if not p:
        return
    db.db().apply(uid, **{field: int(p.get(field) or 0) + amount})


# ─────────── نمای کلی ───────────
def power_rating(p: dict) -> int:
    try:
        b = __import__("economy").stats_of(p)
    except Exception:
        b = balance.player_block(p, {}, [])
    bonds = 0
    try:
        import research
        bonds = sum(bt.get("bond", 0) * 40 for bt in research.bond_rows(p["user_id"]))
    except Exception:
        pass
    return int(b["power"] * 2.4 + int(p.get("kills") or 0) * 12 + bonds +
               int(p.get("boss_kills") or 0) * 160 + int(p.get("arena_rating") or 1000) * 0.18)


def _pair(items: list, per: int = 3) -> list:
    """چیدنِ برچسب‌ها در ردیف‌های کوتاه (کارتِ فشرده)."""
    return ["  · " + " · ".join(items[i:i + per]) for i in range(0, len(items), per)]


def card(p: dict, full: bool = True) -> str:
    """کارتِ عامل — داده را می‌چیند و چارچوبِ پرونده را به ui می‌سپارد."""
    import ui
    b = __import__("economy").stats_of(p)
    d = db.db()
    gear = []
    for r in d.q("SELECT item_id, level FROM items WHERE user_id=? AND equipped=1 AND qty>0", (p["user_id"],)):
        it = __import__("economy").ITEMS.get(r["item_id"]) or {}
        gear.append(f"{it.get('emj', '⚙️')} {it.get('name', r['item_id'])}"
                    + (f" <code>+{r['level']}</code>" if r.get("level") else ""))
    import research
    bonds = [f"{(__import__('titans').get(bt['titan_id']) or {}).get('emj', '🦖')}"
             f" {(__import__('titans').get(bt['titan_id']) or {}).get('name', '?')}"
             f" <i>پیوندِ {bt['bond']}</i>" for bt in research.bond_rows(p["user_id"])[:6]]
    eco = __import__("economy")
    dead = ""
    if is_dead(p):
        dead = f"{max(0, int(dead_left(p) // 60))} دقیقه"
    dat = dict(
        name=p.get("name") or "عامل", handle=("@" + p["username"]) if p.get("username") else "",
        rank=int(p.get("rank") or 1), rank_name=rank_label(p),
        xp=float(p.get("xp") or 0), xp_need=balance.xp_need(int(p.get("rank") or 1)),
        hp=b["hp"], max_hp=b["max_hp"], energy=b["energy"], max_energy=b["max_energy"],
        resolve=float(p.get("resolve") or 0), power=power_rating(p),
        atk=b["atk"], df=b["df"], spd=b["spd"], regen=b["regen"],
        acc_txt=f"{b['acc'] * 100:.0f}٪", dodge_txt=f"{b['dodge'] * 100:.0f}٪",
        code=abs(hash(("agent", p["user_id"]))) % 90000 + 1000, cls="مجوزِ مانارچ", dead=dead,
        res_lines=(_pair(["{} {}: <b>{}</b>".format(m["icon"], m["name"], ui.n(p.get(k)))
                          for k, m in eco.RES.items()])) if full else None,
        gear=(gear or ["<i>هیچ تجهیزی فعال نیست — /shop</i>"]) if full else None,
        bonds=bonds or None,
        disc=f"{len(research.known_rows(p['user_id']))}/{len(__import__('titans').TITANS)}",
        daily=(f"✅ امروز {ui.DOT} {int(p.get('streak') or 1)} روز پیوسته"
               if p.get("last_seen_day") == db.local_day()
               else "⬜ امروز ثبت نشده"),
        vault=float(p.get("vault") or 0),
        flow=_flow(p), nxt=_next_step(p),
    )
    return ui.agent_card(dat)


def _flow(p: dict) -> list:
    """آنچه همین حالا در زمینِ این عامل می‌چرخد (کاوش/آزمایشگاه/یورش/سازمان)."""
    import division
    import expedition
    import raid as RA
    import titans as TN
    import ui
    uid = p["user_id"]
    out = []
    st = expedition.status(uid)
    if st.get("active"):
        out.append(f"🗺 کاوش در «{st.get('zone') or '—'}» — بازگشت تا {ui.dur(st['left'])}")
    elif st.get("ready"):
        out.append("🗺 کاوش برگشته — <code>/explore claim</code>")
    if p.get("lab_titan") and float(p.get("lab_until") or 0) > now():
        nm = (TN.get(p["lab_titan"]) or {}).get("name", "نمونه")
        out.append(f"🔬 آزمایشگاه مشغولِ «{nm}» — {ui.eta(float(p['lab_until']))}")
    rs = RA.state()
    if rs and not rs.get("over"):
        out.append(f"🌍 یورشِ جهانی «{rs.get('name')}» — پایان {ui.eta(float(rs.get('ends_at') or 0))}")
    dv = division.get_for(uid)
    if dv.get("name"):
        out.append(f"🏢 «{dv['name']}» {ui.DOT} سطح {int(dv.get('level') or 1)} "
                   f"{ui.DOT} {len(dv.get('members') or [])} عضو")
    return out


def _next_step(p: dict) -> str:
    """یک قدمِ مشخص، بر اساسِ نزدیک‌ترین پرونده — تا تازه‌وارث نداند کجا برود."""
    import research
    import titans as TN
    import ui
    if is_dead(p):
        return f"☠️ حالتِ بازیابی — {ui.dur(max(0.0, dead_left(p)))} تا بازگشت"
    rows = [r for r in research.known_rows(p["user_id"]) if int(r.get("stage") or 0) < 5]
    if not rows:
        return "📡 <code>/track</code> — نخستین سیگنال لرزه‌ای را بگیر"
    best = rows[0]
    nm = (TN.get(best["titan_id"]) or {}).get("name", best["titan_id"])
    stage = int(best.get("stage") or 0)
    hint = {0: f"📡 <code>/track</code> برای سیگنالِ «{nm}»",
            1: f"👁 <code>/sample {nm}</code> — امضا را محکم کن",
            2: f"🧬 <code>/sample {nm}</code> هنوز نمونه کم دارد",
            3: f"🔬 <code>/analyze {nm}</code> — سیکلِ آزمایشگاه را باز کن",
            4: f"👑 <code>/bond {nm}</code> — پرونده آمادهٔ پیوند است"}
    nxt = hint.get(stage) or f"⚔️ <code>/hunt {nm}</code> — پیوند را در نبرد محک بزن"
    return nxt


def top_by(field: str, limit: int = 10) -> list:
    rows = db.db().q(f"""SELECT user_id,name,rank,{field} AS v FROM players
                         WHERE {field} > 0 ORDER BY v DESC LIMIT ?""", (limit,))
    return rows


def leaderboard(mode: str = "power", limit: int = 10) -> list:
    """رنکینگ زنده؛ قدرت از کش اسکجولر خوانده می‌شود (و در صورت خالی بودن، محاسبه)."""
    if mode == "power":
        rows = db.db().q("SELECT user_id,name,rank,power_cache FROM players ORDER BY power_cache DESC LIMIT ?",
                         (limit,))
        if not rows or all(not r.get("power_cache") for r in rows):
            all_p = db.db().q("SELECT * FROM players")
            scored = sorted(all_p, key=lambda p: -power_rating(p))[:limit]
            return [dict(user_id=p["user_id"], name=p["name"], rank=p["rank"],
                         v=power_rating(p)) for p in scored]
        return rows
    field = {"xp": "xp", "boss": "boss_kills", "raid": "raids", "kills": "kills",
             "arena": "arena_rating", "research": "research_done", "deaths": "deaths"}.get(mode, "xp")
    return top_by(field, limit)


def recalc_power_cache():
    """هر دور اسکجولر: کش قدرت برای رنکینگ سریع."""
    rows = db.db().q("SELECT * FROM players")
    for p in rows:
        try:
            v = power_rating(p)
            set_row(p["user_id"], power_cache=v)
        except Exception:
            pass
    return len(rows)


# ───────────نمای اقتصاد (economy → player؛ import معکوس = چرخه، پس lazy) ───────────
def progress(uid: int, key: str, amount: float = 1) -> list:
    """پیشرفت مأموریت روزانه؛ لیست mid های تازه تکمیل‌شده."""
    import economy
    return economy.progress(int(uid), key, amount)


def roll_missions(uid: int) -> list:
    import economy
    return economy.roll_missions(int(uid))


def claim_mission(uid: int, mid: str) -> dict:
    import economy
    return economy.claim_mission(int(uid), mid)
