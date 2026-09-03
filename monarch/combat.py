# ⚔️ Combat Engine — نبرد نوبتیِ تاکتیکی، کم‌پیام، پایدار (دیتابیس‌محور)
# درک آسان (۸ دکمه)، پشت‌پرده: Stats + Environment + Energy + Ability + Counter + Status + AI
import json
import random

import abilities as AB
import balance
import config
import db
import emoji as EMJ
import titans as TN
from db import now

ACTIONS = {
    "atk": dict(name="حمله", emj="sword", cost=3.0, desc="ضربه‌ی استاندارد — ارزان و قابل‌اتکا"),
    "heavy": dict(name="حمله سنگین", emj="heavy", cost=9.0, cd=2, desc="×۱٫۸۵ آسیب، دقت کمتر، Cooldown"),
    "guard": dict(name="سپر", emj="guard", cost=2.0, desc="−۵۵٪ آسیب این نوبت + پنجره‌ی کانتر + شارژ"),
    "dodge": dict(name="جاخالی", emj="dodge", cost=3.0, desc="+جاخالی این نوبت + شارژ کم"),
    "counter": dict(name="Counter", emj="counter", cost=4.0, desc="کانتر پس از گارد موفق / ریسک‌خواندن"),
    "charge": dict(name="شارژ", emj="charge", cost=0.0, desc="+۳۴ شارژ هسته‌ای، رفع خستگی"),
    "overdrive": dict(name="Overdrive", emj="atom", cost=6.0, desc="مصرف ۱۰۰ شارژ → تمرکز ۲ نوبت"),
    "retreat": dict(name="عقب‌نشینی", emj="retreat", cost=0.0, desc="فرار؛ ریسک ضربه‌ی آخر"),
}
for _a in ACTIONS.values():
    _a["emj"] = EMJ.of(_a.get("emj"), "⚔️")


# ─────────── persistence ───────────
def _save(cid: int, st: dict):
    st["updated"] = now()
    db.db().ex("UPDATE combats SET state=?, updated_at=?, status=? WHERE id=?",
               (db.jdump(st), now(), st.get("status", "live"), cid))
    _sync_boss_hp(cid, st)


def _sync_boss_hp(cid: int, st: dict):
    """باسِ گروهی یک استخر HP دارد: هر ضربه به پرونده‌ی چت نوشته می‌شود."""
    chat_id = (st.get("meta") or {}).get("chat_boss")
    if not chat_id or st.get("kind") != "boss":
        return
    try:
        import bosses
        bosses.sync_hp(int(chat_id), float(st["d"].get("hp") or 0))
    except Exception:
        pass


def _load(cid: int) -> tuple:
    r = db.db().one("SELECT * FROM combats WHERE id=?", (int(cid),))
    if not r:
        return None, None
    return r, (db.jload(r["state"], {}) or {})


def active_of(uid: int) -> dict:
    r = db.db().one("SELECT * FROM combats WHERE status='live' AND (a_id=? OR state LIKE ?) "
                    "ORDER BY id DESC LIMIT 1", (int(uid), f'%"{int(uid)}"%'))
    if not r:
        return {}
    st = db.jload(r["state"], {}) or {}
    if r["status"] != "live":
        return {}
    if int(uid) != int(r["a_id"]) and int(uid) not in [int(x) for x in (st.get("al") or {}).keys()]:
        return {}
    return dict(row=r, st=st, cid=int(r["id"]), kind=r["kind"], msg_id=int(r["msg_id"] or 0))


def close(cid: int, status: str = "closed"):
    db.db().ex("UPDATE combats SET status=?, updated_at=? WHERE id=?", (status, now(), int(cid)))


def gc():
    """جمع‌آوری نبردهای رهاشده (ضدترکم‌شده‌ی دیتابیس)."""
    rows = db.db().q("SELECT id, state FROM combats WHERE status='live' AND updated_at < ?",
                     (now() - config.COMBAT_TIMEOUT,))
    for r in rows:
        st = db.jload(r["state"], {}) or {}
        for u in [st.get("a")] + list((st.get("al") or {}).values()):
            if u:
                _writeback(u)
        close(r["id"], "timeout")
    return len(rows)


def _writeback(u: dict):
    """بازگرداندن HP/انرژی به پرونده‌ی بازیکن (ماندگار در ری‌استارت)."""
    if not u or u.get("kind") != "agent":
        return
    uid = int(u.get("uid") or 0)
    if not uid:
        return
    db.db().apply(uid, hp=round(max(0.0, float(u.get("hp") or 0)), 2),
                  energy=round(max(0.0, float(u.get("energy") or 0)), 2),
                  resolve=round(max(0.0, min(100.0, float(u.get("resolve") or 0))), 2))


# ─────────── ساخت نبرد ───────────
def start(uid: int, kind: str, *, chat: dict, titan_id: str = None, opp_uid: int = None,
          boss: dict = None, encounter: float = 1.0, arena: bool = False) -> dict:
    import player as PL
    import economy
    p = PL.get(uid)
    if not p:
        return dict(ok=False, msg="🔒 /start")
    if PL.is_dead(p):
        return dict(ok=False, msg=f"☠️ حالتِ بازیابی — {PL.dead_left(p)/60:.1f} دقیقه تا احیا.")
    if active_of(uid):
        return dict(ok=False, msg="⚔️ درگیری فعالی داری — «/fight» برای ادامه یا عقب‌نشینی.")
    env = (chat or {}).get("zone") or "ocean"
    if kind in ("boss", "world") and boss:
        d = boss.get("block") or boss          # هم wrapper و هم بلاکِ مستقیم
        d["is_boss"] = True
        d["boss"] = boss.get("boss") or (boss.get("block") or {}).get("boss") or {}
        d.setdefault("boss_id", boss.get("id"))
    elif opp_uid:
        q = PL.get(opp_uid)
        if not q:
            return dict(ok=False, msg="🔒 حریف در مانارچ ثبت نشده.")
        if PL.is_dead(q):
            return dict(ok=False, msg="☠️ آن عامل down است — صبر کن احیا شود.")
        d = economy.stats_of(q)
        d["_pvp"] = True
        d["tid"] = None
        d["uid"] = int(opp_uid)
        d["name"] = q["name"]
        d["emj"] = "agent"
        d["_raw"] = None
        d["allies"] = 0
        d["arena"] = arena
    else:
        t = TN.get(titan_id)
        if not t:
            return dict(ok=False, msg="🗄 تایتان نامعتبر — «/hunt <id>»")
        d = balance.titan_block(t, encounter=encounter, rank=int(p.get("rank") or 1))
        if not arena and kind == "hunt":
            chk = _hunt_gate(p, t)
            if not chk["ok"]:
                return dict(ok=False, msg=chk["msg"])
    a = economy.stats_of(p)
    a["name"] = p["name"]
    a["allies"] = 0
    # ⚡ فشارِ کلاس: بازیکنِ پایین‌تر، با ترس وارد می‌شود
    if d.get("aura"):
        balance.add_status(a, "atkdown", 40, 0)
    st = dict(kind=kind, turn=1, env=env, log=[], al={}, meta={}, status="live",
              created=now(), special=None, last=now(),
              arena=arena, chat_id=int((chat or {}).get("chat_id") or 0))
    st["a"] = a
    st["d"] = d
    st["meta"] = dict(titan_id=titan_id, boss_id=(boss or {}).get("id"), opp_uid=opp_uid,
                      encounter=encounter, threats=0)
    cur = db.db().ex("INSERT INTO combats(chat_id,kind,status,a_id,b_id,state,created_at,updated_at) "
                     "VALUES(?,?,?,?,?,?,?,?)",
                     (st["chat_id"], kind, "live", int(uid), int(opp_uid or 0), db.jdump(st), now(), now()))
    cid = cur.lastrowid
    st["id"] = cid
    _save(cid, st)
    label = d.get("name", "ناشناخته")
    txt = (f"⚔️ <b>درگیری آغاز شد</b>\n"
           f"🛰 <code>پروندۀ {cid:05d}</code> · 🌍 {TN.ENVS.get(env, env)}\n"
           f"🆚 <b>{label}</b>"
           + (f" · <code>{TN.RARITY.get(d.get('rar') or '', {}).get('cls', '')}</code>" if d.get("rar") else ""))
    return dict(ok=True, cid=cid, state=st, msg=txt + "\n" + _quick_view(st), keyboard=True)


def _hunt_gate(p: dict, t: dict) -> dict:
    """شکار داوطلبانه: رتبه + پیوندِ لازم — تا Legendary بی‌آمادگی باز نیست."""
    need = balance.GATE.get(t["rar"], balance.GATE["RARE"])["rank"]
    if int(p.get("rank") or 1) < need:
        return dict(ok=False, msg=(f"🔒 <b>دسترسی رد شد</b> — شکار {t['name']}\n"
                                   f"رتبه‌ی لازم: <b>{need}</b> · رتبه‌ی تو: {int(p.get('rank') or 1)}\n"
                                   f"<i>مانارچ اجازه‌ی خودکشی میدانی نمی‌دهد. Research/کاوش را ادامه بده.</i>"))
    return dict(ok=True)


# ─────────── اکشن‌ها ───────────
def usable(a: dict, caster: dict, target: dict) -> tuple:
    if not a:
        return False, "❌"
    if float(caster.get("energy") or 0) < float(a.get("cost") or 0):
        return False, f"🔋 انرژی کم است ({a['cost']:.0f})"
    if int(caster.get("uses", {}).get(a["id"], -1)) == 0:
        return False, "🎒 محدودیت استفاده"
    if int(caster.get("cd", {}).get(a["id"], 0)) > 0:
        return False, f"⏳ Cooldown {caster['cd'][a['id']]} نوبت"
    req = a.get("req") or {}
    if req.get("charge") and float(caster.get("charge") or 0) < req["charge"]:
        return False, f"☢️ شارژ {req['charge']}% لازم است (الان {caster.get('charge', 0):.0f}%)"
    if req.get("needs_mark") and not balance.has(target, "mark"):
        return False, "🎯 هدف قفل نشده (Target Lock لازم است)"
    if req.get("heat") and float(caster.get("heat") or 0) < req["heat"]:
        return False, f"🌡 حرارت هسته {req['heat']} لازم است"
    return True, ""


def act(cid: int, uid: int, action: str, arg=None) -> dict:
    """یک نوبت بازیکن → پاسخ فوریِ هوش مصنوعی حریف. خروجی: متن کمپکت + کیبورد."""
    row, st = _load(cid)
    if not row or st.get("status") != "live":
        return dict(ok=False, msg="🗄 این پرونده‌ی نبرد بسته شده است.")
    if now() - float(st.get("last") or 0) > config.COMBAT_TIMEOUT:
        for u in [st["a"]] + list((st.get("al") or {}).values()):
            _writeback(u)
        close(cid, "expired")
        return dict(ok=False, msg="⌛ نبرد به‌دلیل بی‌فعالی بسته شد (تلفات: هیچ). «/hunt» دوباره.")
    cd = config.COMBAT_ACTION_CD
    if now() - float(st.get("acted") or 0) < cd:
        return dict(ok=False, msg=f"⏳ {cd - (now() - st['acted']):.0f} ثانیه — نوبت بعدی همین‌قدر فاصله لازم دارد.")
    st["acted"] = now()
    primary = int(row["a_id"]) == int(uid)
    unit = st["a"] if primary else (st.get("al") or {}).get(str(uid))
    if unit is None:
        if action == "join" or action == "assist":
            return _join(cid, st, uid, row)
        return dict(ok=False, msg="🔒 تو در این نبرد شرکت نداری.")
    if action in ("assist",) :
        return _assist(cid, st, uid, unit, row)
    d = st["d"]
    if balance.has(unit, "stun") or balance.has(unit, "freeze"):
        lines = _tick_enemies(st, unit)
        balance.tick_statuses(unit)
        st["turn"] += 1
        _save(cid, st)
        return dict(ok=False, msg="💫 فلجی — نوبت را از دست دادی.", feed=feed(st, lines), live=True)
    lines = []
    notes = []
    ok, why = True, ""
    if action == "retreat":
        return _retreat(cid, st, unit, d, row, uid)
    meta = ACTIONS.get(action)
    ability = None
    is_echo = False
    if action.startswith("ability:"):
        aid = action.split(":", 1)[1]
        ability = AB.get(aid)
        ok, why = usable(ability, unit, d)
    elif action.startswith("echo:"):
        tid = action.split(":", 1)[1]
        ability = AB.ult_of(tid)
        is_echo = True
        ok, why = usable(ability, unit, d)
        bt = _bond_of(uid, tid)
        if not ability:
            ok, why = False, "🔒 این اکس در دسترس نیست"
        elif int(bt or 0) < 2:
            ok, why = False, "🔒 پیوند تراز ۲ لازم است"
        else:
            left = int(unit.setdefault("echo_uses", {}).get(tid, 1 + int(bt) // 2))
            ok, why = (left > 0), "🎒 استفاده‌ی اکس تمام شد"
    elif meta:
        if float(unit.get("energy") or 0) < meta["cost"]:
            notes.append("🔋 خستگی: ضربه‌ی نصفه")
        if meta.get("cd") and int(unit.setdefault("cd", {}).get(action, 0)) > 0:
            ok, why = False, f"⏳ {action} در Cooldown ({unit['cd'][action]})"
    else:
        ok, why = False, "❔ اکشن نامعتبر"
    if not ok:
        return dict(ok=False, msg=f"🚫 {why}")

    # ── هزینه ──
    cost = (ability["cost"] if ability else meta["cost"]) if (ability or meta) else 0
    fatigue = min(0.45, max(0.0, (int(unit.get("chain", 0)) - 2) * 0.09))
    unit["energy"] = round(max(0.0, float(unit["energy"]) - cost), 2)
    if ability:
        unit.setdefault("cd", {})[ability["id"]] = int(ability.get("cd") or 0)
        if ability.get("cost"):
            unit["uses"][ability["id"]] = int(unit.get("uses", {}).get(ability["id"], 3)) - 1
    if is_echo:
        unit.setdefault("echo_uses", {})[arg or tid] = int(unit["echo_uses"].get(tid, 1)) - 1
        unit["charge"] = max(0.0, float(unit.get("charge") or 0) - config.ULT_CHARGE)
    # ── تعیین ضریب ──
    mult = 1.0
    forced = False
    guard_next = False
    if action == "atk":
        mult = 1.0
        unit["chain"] = int(unit.get("chain", 0)) + 1
    elif action == "heavy":
        mult = config.HEAVY_MULT
        unit["chain"] = 0
        unit.setdefault("cd", {})["heavy"] = int(ACTIONS["heavy"]["cd"])
    elif action == "guard":
        unit["guarded"] = 1
        guard_next = True
        unit["charge"] = min(config.CHARGE_MAX, float(unit.get("charge") or 0) + config.GUARD_BUILD)
        unit["chain"] = 0
    elif action == "dodge":
        balance.add_status(unit, "focus", 0, 0)
        unit["evasion"] = 1
        unit["charge"] = min(config.CHARGE_MAX, float(unit.get("charge") or 0) + config.GUARD_BUILD * 0.6)
        unit["chain"] = 0
    elif action == "counter":
        unit["chain"] = 0
        windowed = int(unit.get("counter_window") or 0) > 0
        if windowed:
            mult = 1.0
            forced = True
            notes.append("🎯 <b> Riposte</b> — پنجره‌ی کانتر")
        else:
            if random.random() < 0.34 + min(0.24, float(unit.get("acc") or 0.7) * 0.22):
                balance.add_status(d, "stun", 1, 0)
                notes.append("🎯 <b>وقفه</b> — حرکت حریف را خواندی")
                mult = 0.55
            else:
                unit["exposed"] = 1
                notes.append("🌀 خواندن شکست خورد — بدنت باز ماند")
                mult = 0.4
    elif action == "charge":
        unit["charge"] = min(config.CHARGE_MAX, float(unit.get("charge") or 0) + config.CHARGE_GAIN)
        unit["energy"] = min(float(unit.get("max_energy") or 100), float(unit["energy"]) + 26)
        unit["chain"] = 0
        unit["over"] = 0
        notes.append(f"🔋 شارژ → <b>{unit['charge']:.0f}%</b>")
        mult = 0.0
    elif action == "overdrive":
        if float(unit.get("charge") or 0) < config.ULT_CHARGE:
            return dict(ok=False, msg=f"☢️ برای Overdrive شارژ ۱۰۰ لازم است ({unit.get('charge',0):.0f}%).")
        unit["charge"] = 0.0
        balance.add_status(unit, "focus", 2, 0)
        balance.add_status(unit, "accup", 2, 0)
        notes.append("☢️ <b>بیش‌ران</b> — تمرکز کامل ۲ نوبت")
        mult = 1.15
    elif ability:
        mult = float(ability.get("power") or 1.0)
        unit["chain"] = 0
        notes.append(f"{ability['emj']} <b>{ability['name']}</b>")
    if fatigue:
        mult *= (1 - fatigue)
        notes.append(f"📉 Overextension −{fatigue*100:.0f}% (اسپم نکن)")
    # ── ضربه ──
    if mult > 0:
        r = balance.resolve_strike(unit, d, mult=mult, ability=ability,
                                   is_counter=(action == "counter" and forced),
                                   env=st.get("env"), forced_hit=guard_next and False)
        if r["dodged"]:
            lines.append(f"⚡ {d.get('name')} جاخالی داد")
        elif r.get("missed"):
            lines.append("🕳 خطای محاسباتی — نخورد")
        else:
            d["hp"] = round(float(d["hp"]) - r["dmg"], 2)
            tag = "❗️" if r["crit"] else ("🧱" if r["blocked"] else "💥")
            lines.append(f"{tag} <b>{r['dmg']:.1f}</b> → {d.get('name')}"
                         + (f" · " + "؛ ".join(r["notes"][:2]) if r["notes"] else ""))
            _apply_effects(unit, d, ability, r, st, lines)
            _credit(st, uid, "dmg", r["dmg"])
    if action == "guard":
        __import__("player").track_stat(uid, "guards", 1)
        __import__("player").progress(uid, "guard", 1)
    # ── پاسخ حریف ──
    endgame = None
    if float(d["hp"]) <= 0:
        endgame = _victory(cid, st, row, uid, lines)
    else:
        lines += _enemy_phase(st, lines)
        if float(d["hp"]) <= 0:
            endgame = _victory(cid, st, row, uid, lines)
        else:
            lines += _enemy_turn(st, unit, notes)
            for u in [st["a"]] + list((st.get("al") or {}).values()):
                balance.tick_statuses(u)
                if float(u["hp"]) <= 0:
                    endgame = _defeat(cid, st, row, u, lines)
                    break
    # ── پایان نوبت ──
    for key in list(unit.get("cd", {}).keys()):
        unit["cd"][key] = max(0, int(unit["cd"][key]) - 1)
    for aid in list(st["d"].setdefault("cd", {}).keys()):
        st["d"]["cd"][aid] = max(0, int(st["d"]["cd"][aid]) - 1)
    for u in [st["a"]] + list((st.get("al") or {}).values()):
        u["guarded"] = 0
        u["evasion"] = 0
        u["exposed"] = 0
        if u.get("counter_window"):
            u["counter_window"] = 0
    if st["a"].get("guarded") or guard_next:
        st["a"]["counter_window"] = config.COUNTER_WINDOW if (unit is st["a"] and guard_next) else st["a"].get("counter_window", 0)
    if guard_next:
        unit["counter_window"] = config.COUNTER_WINDOW
    st["turn"] = int(st.get("turn") or 1) + 1
    for u in [st["a"]] + list((st.get("al") or {}).values()):
        _writeback(u)
    if endgame:
        return endgame
    _save(cid, st)
    return dict(ok=True, feed=feed(st, lines), live=True, state=st, cid=cid)


def _bond_of(uid: int, tid: str) -> int:
    r = db.db().one("SELECT bond FROM bonds WHERE user_id=? AND titan_id=?", (int(uid), tid))
    return int(r["bond"] or 0) if r else 0


def _apply_effects(caster: dict, target: dict, ability: dict, res: dict, st: dict, lines: list):
    """افکت‌های مهارت (وضعیت/شارژ/مکمل) — یک مسیر برای بازیکن و تایتان."""
    eff = (ability or {}).get("eff") or {}
    if not eff:
        return
    def add(unit, sid, turns, val=0.0):
        if balance.add_status(unit, sid, int(turns or 0), val):
            m = balance.STATUS_META.get(sid, {})
            if unit is target:
                lines.append(f"   ↳ {m.get('emj','•')} {target.get('name')} → {m.get('name', sid)} ({turns})")
            else:
                lines.append(f"   ↳ {m.get('emj','•')} خودت → {m.get('name', sid)} ({turns})")
    for sid in ("burn", "acid", "bleed", "stun", "freeze", "slow", "blind", "mark", "atkdown", "defup"):
        if eff.get(sid):
            val = 0.0
            if sid in ("burn", "acid", "bleed"):
                val = round(float(res.get("dmg") or 1) * 0.16, 1)
            add(target, sid, eff[sid], val)
    if eff.get("rally") or eff.get("atkup"):
        add(caster, "rally", eff.get("atkup") or eff.get("rally"))
    if eff.get("accup"):
        add(caster, "accup", eff["accup"])
    if eff.get("dispel"):
        n = balance.clear_statuses(caster, int(eff["dispel"]))
        if n:
            lines.append(f"   ↳ 🧼 {n} وضعیت منفی پاک شد")
    if eff.get("heal"):
        amt = round(float(caster.get("max_hp") or 100) * float(eff["heal"]), 1)
        caster["hp"] = round(min(float(caster["max_hp"]), float(caster["hp"]) + amt), 2)
        lines.append(f"   ↳ 💚 +{amt} HP")
    if eff.get("drain"):
        steal = round(float(target.get("energy") or 0) * float(eff["drain"]), 1)
        target["energy"] = round(max(0.0, float(target.get("energy") or 0) - steal), 2)
        caster["energy"] = round(min(float(caster.get("max_energy") or 100), float(caster.get("energy") or 0) + steal), 2)
        if steal > 0:
            lines.append(f"   ↳ 🔋 −{steal} انرژی حریف")
    if eff.get("shield"):
        v = float(eff["shield"])
        if v > 0:
            caster["shield"] = round(float(caster.get("shield") or 0) + v * float(caster.get("max_hp") or 100) * 0.22, 2)
            lines.append(f"   ↳ 🧱 سپر {caster['shield']:.1f}")
        else:
            target["shield"] = round(max(0.0, float(target.get("shield") or 0) + v * 12), 2)
            lines.append(f"   ↳ 💢 سپر حریف −{abs(v) * 12:.1f}")
    if eff.get("charge"):
        caster["charge"] = min(config.CHARGE_MAX, float(caster.get("charge") or 0) + float(eff["charge"]))
    if eff.get("heat"):
        caster["heat"] = float(caster.get("heat") or 0) + float(eff["heat"])
        if caster["heat"] >= 100:
            caster["heat"] = 20.0
            balance.add_status(caster, "stun", 2, 0)
            lines.append(f"   ↳ 🌡 <b>داغی بیش‌ازحد</b> — هسته قفل شد (۲ نوبت)")
    if eff.get("env"):
        st["env"] = eff["env"]
        lines.append(f"   ↳ 🌍 محیط به {TN.ENVS.get(eff['env'], eff['env'])} تغییر کرد")
    if eff.get("phase"):
        st["d"]["phase"] = int(st["d"].get("phase") or 1) + 1
        lines.append(f"   ↳ 🔄 <b>PHASE {st['d']['phase']}</b>")


def _credit(st: dict, uid: int, key: str, amount: float):
    tr = st.setdefault("track", {})
    row = tr.setdefault(str(uid), dict(dmg=0.0, guard=0.0, support=0.0, analyze=0.0, strikes=0))
    row[key] = round(float(row.get(key, 0)) + float(amount), 2)
    if key == "dmg":
        row["strikes"] = int(row.get("strikes", 0)) + 1


def _join(cid: int, st: dict, uid: int, row) -> dict:
    """پیوستن دیگر اعضا به نبردِ باس (MMO واقعی، نه Damage Race)."""
    import player as PL
    import economy
    if st.get("kind") not in ("boss", "world") or len(st.get("al") or {}) >= 5:
        return dict(ok=False, msg="🔒 این نبرد چندنفره نیست یا ظرفیت پر است.")
    p = PL.get(uid)
    if not p or PL.is_dead(p):
        return dict(ok=False, msg="☠️ نمی‌توانی وارد شوی.")
    u = economy.stats_of(p)
    u["name"] = p["name"]
    u["allies"] = 1
    st.setdefault("al", {})[str(uid)] = u
    _credit(st, uid, "dmg", 0)
    _save(cid, st)
    return dict(ok=True, feed=feed(st, [f"🛰 <b>{p['name']}</b> به عملیات پیوست (واحد پشتیبانی)."]),
                live=True, state=st, cid=cid)


def _assist(cid: int, st: dict, uid: int, unit: dict, row) -> dict:
    """🩹 پشتیبانی: التیام/سپر برای متحد — امتیاز Best Support."""
    import player as PL
    al = st.get("al") or {}
    mates = [st["a"]] + [v for k, v in al.items() if k != str(uid)]
    mates = [m for m in mates if float(m.get("hp") or 0) > 0]
    if not mates:
        return dict(ok=False, msg="🩹 متحدی برای پشتیبانی نیست.")
    target = min(mates, key=lambda m: float(m["hp"]) / max(1.0, float(m["max_hp"])))
    if float(unit.get("energy") or 0) < 14:
        return dict(ok=False, msg="🔋 ۱۴ انرژی برای پشتیبانی لازم است.")
    unit["energy"] = round(float(unit["energy"]) - 14, 2)
    amt = round(float(target["max_hp"]) * 0.14, 1)
    target["hp"] = round(min(float(target["max_hp"]), float(target["hp"]) + amt), 2)
    balance.add_status(target, "defup", 2, 0)
    _credit(st, uid, "support", amt)
    st["turn"] = int(st.get("turn") or 1) + 1
    lines = [f"🩹 <b>{unit['name']}</b> → <b>{target['name']}</b> +{amt} HP · 🧱 پیش‌سنگر ۲ نوبت"]
    lines += _enemy_turn(st, unit, [])
    _save(cid, st)
    PL.progress(uid, "boss", 0)
    return dict(ok=True, feed=feed(st, lines), live=True, state=st, cid=cid)


def _retreat(cid: int, st: dict, unit: dict, d: dict, row, uid: int) -> dict:
    import player as PL
    chance = 0.42 + min(0.3, float(unit.get("spd") or 0) / 40) - 0.08 * int(d.get("threat") or 1)
    if st.get("kind") in ("boss", "world"):
        chance -= 0.18
    if random.random() < chance:
        PL.set_row(uid, flees=int(PL.get(uid).get("flees") or 0) + 1)
        PL.spend(uid, credits=-round(0.05 * float(PL.get(uid).get("credits") or 0), 0))
        close(cid, "fled")
        return dict(ok=True, ended=True, text=(f"💨 <b>عقب‌نشینی تاکتیکی</b>\n"
                                              f"از {d.get('name')} فاصله گرفتی؛ ۵٪ اعتبار در فرار ریخت.\n"
                                              f"🛰 مانارچ قضاوت نمی‌کند — زنده بمان."))
    hit = balance.resolve_strike(d, unit, mult=1.25, env=st.get("env"))
    unit["hp"] = round(float(unit["hp"]) - hit["dmg"], 2)
    lines = [f"🚫 فرار شکست خورد — {d.get('name')} پشتِ تو را باز دید · <b>−{hit['dmg']:.1f}</b>"]
    if float(unit["hp"]) <= 0:
        return _defeat(cid, st, row, unit, lines)
    _save(cid, st)
    return dict(ok=True, feed=feed(st, lines), live=True, state=st, cid=cid)


# ─────────── هوش مصنوعی حریف ───────────
def _enemy_turn(st: dict, unit: dict, notes: list) -> list:
    d = st["d"]
    lines = []
    if balance.has(d, "stun") or balance.has(d, "freeze"):
        nm = balance.STATUS_META.get("stun" if balance.has(d, "stun") else "freeze", {})
        lines.append(f"💫 <b>{d.get('name')}</b> قفل است — نوبت را از دست داد")
        balance.tick_statuses(d)
        st["last"] = now()
        return lines
    # ── انتخاب اکشن توسط AI (متناسب با INT تایتان) ──
    intel = float(d.get("intel") or 200)
    hp_ratio = float(d["hp"]) / max(1.0, float(d["max_hp"]))
    choice = None
    ult = AB.ult_of(d.get("tid") or "")
    ok_ult = ult and usable(ult, d, unit)[0]
    if ok_ult and (hp_ratio < 0.55 or random.random() < 0.5 + intel / 900):
        choice = ("ability", ult)
    elif hp_ratio < 0.32:
        heals = [AB.get(a) for a in (d.get("abilities") or []) if (AB.get(a).get("eff") or {}).get("heal")]
        if heals and usable(heals[0], d, unit)[0]:
            choice = ("ability", heals[0])
        elif random.random() < 0.30:
            choice = ("charge", None)
    if choice is None:
        pool = [AB.get(a) for a in (d.get("abilities") or [])]
        pool = [a for a in pool if usable(a, d, unit)[0]]
        if pool and random.random() < 0.42 + min(0.35, intel / 1200):
            choice = ("ability", random.choice(pool))
        else:
            choice = ("heavy" if random.random() < 0.26 else "atk", None)
    kind_, ability = choice
    # ── کانتر روی کارِ تکراری بازیکن ──
    if ability is None and kind_ == "atk" and int(unit.get("chain", 0)) >= 3 and random.random() < 0.5:
        balance.add_status(unit, "blind", 1, 0)
        lines.append(f"🧠 <b>{d.get('name')}</b> ریتم تکراری‌ات را خواند — الگو را شکست")
        kind_ = "special"
    mult = 1.0
    if kind_ == "heavy":
        mult = 1.55
    elif kind_ == "charge":
        d["charge"] = min(config.CHARGE_MAX, float(d.get("charge") or 0) + config.CHARGE_GAIN)
        d["energy"] = min(float(d.get("max_energy") or 100), float(d.get("energy") or 0) + 24)
        lines.append(f"🔋 <b>{d.get('name')}</b> هسته‌اش را شارژ می‌کند ({d['charge']:.0f}%)")
        st["last"] = now()
        return lines
    elif kind_ == "ability" and ability:
        mult = float(ability.get("power") or 1.0)
        d["energy"] = round(max(0.0, float(d.get("energy") or 0) - ability["cost"]), 2)
        d.setdefault("cd", {})[ability["id"]] = int(ability.get("cd") or 0)
        lines.append(f"{ability['emj']} <b>{d.get('name')}</b> → {ability['name']}")
    elif kind_ == "special":
        mult = 1.42
        lines.append(f"😡 <b>{d.get('name')}</b> بی‌رحم ضربه می‌زند")
    # ── هدف: بازیکن یا متحد (تهدید‌محور) ──
    target = _pick_target(st, d)
    if target is None:
        return lines
    evade = 0.0
    if target.get("evasion"):
        evade += 0.26
    if target.get("exposed"):
        evade -= 0.22
    saved_dodge = float(target.get("dodge") or 0)
    target["dodge"] = min(config.DODGE_CAP, max(0.0, saved_dodge + evade))
    r = balance.resolve_strike(d, target, mult=mult, ability=ability, env=None)
    target["dodge"] = saved_dodge
    if r["dodged"]:
        lines.append(f"⚡ <b>{target['name']}</b> جاخالی داد")
    elif r.get("missed"):
        lines.append(f"🕳 ضربه‌ی {d.get('name')} خطا رفت")
    else:
        target["hp"] = round(float(target["hp"]) - r["dmg"], 2)
        tag = "❗️" if r["crit"] else ("🧱" if r["blocked"] else "💥")
        lines.append(f"{tag} <b>−{r['dmg']:.1f}</b> → {target['name']}"
                     + (f" · " + "؛ ".join(r["notes"][:1]) if r["notes"] else ""))
        _apply_effects(d, target, ability, r, st, lines)
        if r["blocked"] and int(target.get("counter_window") or 0) > 0:
            rp = balance.resolve_strike(target, d, mult=1.0, is_counter=True, env=st.get("env"))
            d["hp"] = round(float(d["hp"]) - rp["dmg"], 2)
            lines.append(f"🎯 <b>ضدحمله</b> — {target['name']} پاسخ داد · <b>{rp['dmg']:.1f}</b>")
            _credit(st, int(target.get("uid") or 0), "dmg", rp["dmg"])
        if target.get("guarded"):
            _credit(st, int(target.get("uid") or 0), "guard", r["dmg"])
    balance.tick_statuses(d)
    if float(d.get("regen") or 0) and float(d["hp"]) > 0:
        d["hp"] = round(min(float(d["max_hp"]), float(d["hp"]) + float(d["regen"])), 2)
    st["last"] = now()
    return lines


def _pick_target(st: dict, d: dict):
    cands = [st["a"]] + list((st.get("al") or {}).values())
    cands = [c for c in cands if float(c.get("hp") or 0) > 0]
    if not cands:
        return None
    tr = st.get("track", {})
    return max(cands, key=lambda c: float(c.get("hp") or 0) * 0.4
               + float(tr.get(str(c.get("uid")), {}).get("dmg", 0)) * 0.9)


def _enemy_phase(st: dict, lines: list) -> list:
    """باس: فازها، Rage Mode و حمله‌ی ویژه‌ی پیش‌گویی‌شده (Counter mechanic)."""
    d = st["d"]
    boss = d.get("boss") or {}
    if not boss:
        return lines
    ratio = float(d["hp"]) / max(1.0, float(d["max_hp"]))
    ph = boss.get("phases") or []
    idx = int(d.get("phase") or 1)
    for i, p in enumerate(ph, start=1):
        if ratio <= p.get("at", 1.0) and idx <= i:
            d["phase"] = i + 1
            d["atk"] = round(float(d["atk"]) * (1 + p.get("atk", 0.12)), 2)
            d["df"] = round(float(d["df"]) * (1 + p.get("df", 0.05)), 2)
            lines.append(f"🔄 <b>PHASE {i+1}</b> — {p.get('name', 'تغییر رفتار')} · "
                         f"⚔️+{int(p.get('atk',12))}%")
    if not d.get("rage") and now() > float(boss.get("rage_at") or 1e18):
        d["rage"] = 1
        d["atk"] = round(float(d["atk"]) * 1.28, 2)
        lines.append(f"😡 <b>حالت خشم</b> — {d.get('name')} دیگر مذاکره نمی‌کند (+۲۸٪ آسیب)")
    # حمله‌ی ویژه: پنجره‌ی پاسخ
    if int(st.get("turn") or 1) % 4 == 0 and not st.get("special"):
        sp = random.choice(boss.get("specials") or [])
        if sp:
            st["special"] = dict(name=sp["name"], counter=sp["counter"], mult=sp.get("mult", 1.8),
                                 emj=sp.get("emj", "warning"), turn=st.get("turn"))
            lines.append(f"{sp.get('emj', '🚨')} <b>⚠️ حملۀ نزدیک — {sp['name']}</b> · "
                         f"پاسخ لازم: <b>{ACTIONS.get(sp['counter'], {}).get('emj', '')} "
                         f"{ACTIONS.get(sp['counter'], {}).get('name', '')}</b>")
    elif st.get("special"):
        sp = st["special"]
        good = (st["a"].get("guarded") and sp["counter"] == "guard") or \
               (st["a"].get("evasion") and sp["counter"] == "dodge") or \
               (st["a"].get("counter_window") and sp["counter"] == "counter") or \
               (sp["counter"] == "retreat" and random.random() < 0.4)
        if good:
            d["hp"] = round(float(d["hp"]) - float(d["max_hp"]) * 0.05, 2)
            st["a"]["charge"] = min(config.CHARGE_MAX, float(st["a"].get("charge") or 0) + 30)
            lines.append(f"✅ <b>منحرف شد</b> — {sp['name']} خنثی شد · ☢️ +۳۰ شارژ · −۵٪ HP باس")
        else:
            r = balance.resolve_strike(d, st["a"], mult=sp["mult"], env=None)
            st["a"]["hp"] = round(float(st["a"]["hp"]) - r["dmg"] * 1.3, 2)
            lines.append(f"💀 <b>{sp['name']}</b> خورد → <b>−{r['dmg']*1.3:.1f}</b> (پاسخ ندادی)")
        st["special"] = None
    return lines


# ─────────── پایان نبرد ───────────
def _victory(cid: int, st: dict, row, uid: int, lines: list) -> dict:
    import player as PL
    import research
    import economy
    d = st["d"]
    close(cid, "won")
    kind = st.get("kind")
    perfect = float(st["a"]["hp"]) / max(1.0, float(st["a"]["max_hp"])) > 0.75
    if d.get("_pvp"):
        return _pvp_settle(cid, st, row, uid, lines)
    t = TN.get(d.get("tid") or "") or {}
    tid = d.get("tid")
    first = False
    if tid:
        old = research.row(uid, tid)
        first = int(old.get("kills") or 0) == 0
    pay = balance.victory_payout(t or dict(rar="RARE"), rank=int(PL.get(uid).get("rank") or 1),
                                first_kill=first, perfect=perfect,
                                encounter=float(d.get("encounter") or 1.0))
    PL.add_res(uid, **pay)
    PL.add_xp(uid, pay.get("xp", 0))
    PL.track_stat(uid, "kills", 1)
    PL.track_stat(uid, "wins", 1)
    PL.progress(uid, "hunt_win", 1)
    if tid:
        research.kill_bump(uid, tid, victory=True)
    for u in [st["a"]] + list((st.get("al") or {}).values()):
        _writeback(u)
    div_txt = ""
    try:
        import division
        for u in [st["a"]] + list((st.get("al") or {}).values()):
            division.credit_activity(int(u["uid"]), "hunt_win", 1)
    except Exception:
        pass
    head = (f"🏆 <b>هدف از بین رفت</b> — {d.get('name')}\n"
            + " · ".join(f"{e} {v:g}" for e, v in _iconize(pay))
            + (f"\n🎖 <b>اولین شکار</b> — پرونده‌ی {t.get('name', '')} باز شد" if first else "")
            + (f"\n🅿️ {div_txt}" if div_txt else ""))
    return dict(ok=True, ended=True, text=head, feed=feed(st, lines + [head]), live=False,
                rewards=pay)


def _iconize(d: dict) -> list:
    m = dict(credits="🪙", dna="🧬", cells="🔋", mats="🔩", fdata="📡", cores="💎", xp="✨")
    return [(m.get(k, "▪️"), v) for k, v in d.items() if v]


def _defeat(cid: int, st: dict, row, unit: dict, lines: list) -> dict:
    import player as PL
    close(cid, "lost")
    _sync_boss_hp(cid, st)
    uid = int(unit.get("uid") or row["a_id"])
    for u in [st["a"]] + list((st.get("al") or {}).values()):
        u["hp"] = max(0.0, float(u.get("hp") or 0))
        _writeback(u)
    res = PL.die(uid, st.get("kind") or "combat")
    drop = " · ".join(f"{k} −{v:g}" for k, v in (res.get("drop") or {}).items())
    txt = (f"☠️ <b>عامل از پا درآمده</b>\n"
           f"Recovery Mode: <b>{config.RECOVERY_MINUTES} دقیقه</b>\n"
           + (f"🩸 Drop: {drop}\n" if drop else "🛡 منابعِ محافظت‌شده باقی ماند\n")
           + f"❤️ <b>بازگشت عامل</b> پس از پایان زمان، HP تا {int(config.INJURY_HP*100)}٪ بازسازی می‌شود.")
    PL.track_stat(uid, "losses", 1)
    return dict(ok=False, ended=True, text=txt, feed=feed(st, lines + [txt]), live=False, dead=True)


def _pvp_settle(cid: int, st: dict, row, uid: int, lines: list) -> dict:
    import arena
    import player as PL
    opp = int(row["b_id"] or 0)
    win = int(uid)
    close(cid, "won")
    PL.track_stat(win, "pvp_wins", 1)
    pool = round(min(1400.0, 0.10 * float(PL.get(opp).get("credits") or 0)), 0)
    PL.add_res(win, credits=180 + pool, dna=1)
    PL.add_xp(win, 22)
    PL.track_stat(win, "wins", 1)
    for u in [st["a"]] + list((st.get("al") or {}).values()):
        _writeback(u)
    if opp:
        # بازنده در دوئل نمی‌میرد؛ با ۱ HP به Medical می‌رود (ضد griefing، بدون Drop)
        left = max(1.0, float(st["d"].get("hp") or 0))
        PL.set_row(opp, hp=left)
        PL.track_stat(opp, "pvp_losses", 1)
        PL.track_stat(opp, "losses", 1)
    arena_txt = ""
    if st.get("meta", {}).get("arena"):
        r = arena.settle(win, opp, win_score=1, lose_score=0)
        arena_txt = "\n" + (r.get("msg") or "").split("\n", 1)[-1] if r.get("ok") else ""
    return dict(ok=True, ended=True,
                text=f"🏆 <b>تهدید حذف شد</b> — {st['d'].get('name')}\n"
                     f"🪙 جایزه‌ی میدان <code>+{180 + pool:,.0f}</code> · 🧬 1 · حریف → Medical"
                     + arena_txt,
                feed=feed(st, lines), live=False, rewards=dict(credits=180 + pool, dna=1))


# ─────────── خروجی UI ───────────
def feed(st: dict, lines: list = None) -> str:
    import ui
    log = (st.get("log") or []) + (lines or [])
    st["log"] = log[-config.MAX_FEED_LINES:]
    return ui.combat_feed(st, st["log"])


def _quick_view(st: dict) -> str:
    """دو خطِ فشرده برای نگاهِ سریع (بدونِ شلوغ‌کردنِ فید)."""
    import ui
    a, d = st["a"], st["d"]
    return (f"🛰 ❤️ {ui.n(a['hp'])}/{ui.n(a['max_hp'])} · 🔋 {ui.n(a['energy'])} · ☢️ {ui.n(a.get('charge', 0))}٪\n"
            f"🆚 {d.get('name')} ❤️ {ui.n(d['hp'])}/{ui.n(d['max_hp'])} "
            f"({ui.pct(d['hp'], d['max_hp'])}٪)")


def options(cid: int, uid: int) -> list:
    """دکمه‌های نبرد (ui فقط همین لیست را رندر می‌کند)."""
    row, st = _load(cid)
    if not st:
        return []
    unit = st["a"] if int(row["a_id"]) == int(uid) else (st.get("al") or {}).get(str(uid))
    if not unit:
        return []
    out = []
    for k, meta in ACTIONS.items():
        if k == "overdrive" and float(unit.get("charge") or 0) < config.ULT_CHARGE:
            continue
        out.append(dict(cb=f"cbt:{cid}:{k}", text=meta["name"], emj=meta["emj"]))
    import abilities as _A
    for aid in (unit.get("gear_abilities") or []):
        a = _A.get(aid)
        ok, why = usable(a, unit, st["d"])
        out.append(dict(cb=f"cbt:{cid}:ability:{aid}", text=a["name"], emj=a["emj"],
                        disabled=not ok, hint=why))
    try:
        import research
        for echo in research.echo_options(uid):
            a = _A.get(echo["ability"])
            left = int(unit.setdefault("echo_uses", {}).get(echo["tid"], 1 + int(echo["bond"]) // 2))
            out.append(dict(cb=f"cbt:{cid}:echo:{echo['tid']}", text=f"Echo · {echo['name']}",
                            emj=a["emj"] if a else "☄️", disabled=left <= 0,
                            hint=f"{left} استفاده"))
    except Exception:
        pass
    if st.get("kind") in ("boss", "world") and unit is not st["a"]:
        pass
    if st.get("kind") in ("boss", "world"):
        out.append(dict(cb=f"cbt:{cid}:assist", text="Support Ally", emj="medkit"))
    return out
