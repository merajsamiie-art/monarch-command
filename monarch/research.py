# 🔬 Research & Discovery Engine — کشف تایتان، سیگنال، نمونه، تحلیل، پیوند
import random

import balance
import config
import db
import titans as TN
from db import now

# stage: 0 ناشناخته · 1 سیگنال · 2 مشاهده · 3 نمونه · 4 تحلیل · 5 پیوند
STAGES = [dict(key="unknown", label="🕳 ناشناخته", need=0),
          dict(key="signal", label="📡 سیگنال", need=60),
          dict(key="sighting", label="👁 مشاهده", need=150),
          dict(key="sampled", label="🧬 نمونه", need=320),
          dict(key="analyzed", label="🔬 تحلیل", need=620),
          dict(key="bonded", label="👑 پیوند", need=1100)]


def row(uid: int, tid: str, create: bool = False) -> dict:
    d = db.db()
    r = d.one("SELECT * FROM bonds WHERE user_id=? AND titan_id=?", (int(uid), tid))
    if r:
        return r
    if create:
        d.ex("INSERT OR IGNORE INTO bonds(user_id,titan_id,stage,points,last) VALUES(?,?,0,0,?)",
             (int(uid), tid, now()))
        r = d.one("SELECT * FROM bonds WHERE user_id=? AND titan_id=?", (int(uid), tid))
    return r or dict(user_id=uid, titan_id=tid, stage=0, points=0, kills=0, bond=0, bond_points=0)


def stage_of(uid: int, tid: str) -> int:
    return int(row(uid, tid).get("stage") or 0)


def is_known(uid: int, tid: str) -> bool:
    """نام تایتان فقط بعد از اولین سیگنال لو می‌رود (RECON/RARE استثنای «شایعه» دارند)."""
    t = TN.get(tid)
    if not t:
        return False
    return stage_of(uid, tid) >= 1 or t["rar"] in ("RECON",)


def codename(uid: int, t: dict) -> tuple:
    """نمایش محرمانه: هرچه کشف نکرده‌ای، فقط یک کد است."""
    if is_known(uid, t["id"]):
        return t["name"], t["emj"]
    idx = (hash(t["id"]) % 90) + 10
    return f"UNKNOWN TITAN {idx}", "🕳"


def add_points(uid: int, tid: str, pts: float, reason: str = "misc") -> dict:
    """افزودن امتیاز تحقیق + ارتقای خودکار مرحله."""
    t = TN.get(tid)
    if not t:
        return dict(ok=False)
    d = db.db()
    r = row(uid, tid, create=True)
    stage = int(r.get("stage") or 0)
    if stage >= len(STAGES) - 1:
        return dict(ok=True, advanced=0, stage=stage, points=r.get("points", 0))
    pts = float(pts)
    if reason == "bond" and stage < len(STAGES) - 1:
        pts *= balance.gate_of(t["rar"])["xp_mult"]
    new = float(r.get("points") or 0) + pts
    advanced = 0
    while stage < len(STAGES) - 1 and new >= STAGES[stage + 1]["need"]:
        new -= STAGES[stage + 1]["need"]
        stage += 1
        advanced += 1
        if stage == len(STAGES) - 1:
            break
    d.ex("UPDATE bonds SET stage=?, points=?, last=? WHERE user_id=? AND titan_id=?",
         (stage, round(new, 1), now(), int(uid), tid))
    d.setv(f"lasttarget:{uid}", tid)
    d.apply(uid, last_target=tid)
    return dict(ok=True, advanced=advanced, stage=stage, points=round(new, 1),
                first=(advanced and stage >= 3), name=t["name"])


def bar(row_: dict) -> str:
    stage = int(row_.get("stage") or 0)
    if stage >= len(STAGES) - 1:
        return "👑 پیوند فعال"
    nxt = STAGES[stage + 1]
    cur = float(row_.get("points") or 0)
    return f"{STAGES[stage]['label']} · {cur:.0f}/{nxt['need']} → {nxt['label']}"


# ─────────── اکشن‌های میدانی ───────────
def _facility_bonus(uid: int) -> tuple:
    """Radars/Lab سطح Division روی تحقیق اثر دارد (نه پول‌پسند)."""
    import division
    radar = division.facility_of(uid, "radar")
    lab = division.facility_of(uid, "lab")
    return 1 + 0.12 * radar, 1 + 0.15 * lab, lab


def track(uid: int, chat: dict, zone: str = None) -> dict:
    """📡 ردیابی سیگنال — مرحله‌ی اول کشف؛ بی‌هیچ هزینه‌ای جز انرژی و زمان."""
    p = db.db().player(uid)
    if not p:
        return dict(ok=False, msg="🔒 /start اول.")
    if balance.has(p, "stun"):
        return dict(ok=False, msg="💫 فلجی.")
    if player_energy(uid) < 10:
        return dict(ok=False, msg="🔋 انرژی کافی نداری (۱۰ لازم است).")
    if p.get("dead_until") and float(p["dead_until"]) > now():
        return dict(ok=False, msg="☠️ در Recovery Mode ردیابی ممکن نیست.")
    db.db().apply(uid, energy=max(0.0, float(p["energy"]) - 10))
    rad, lab, _ = _facility_bonus(uid)
    zone = zone or (chat or {}).get("zone") or "ocean"
    t = pick_signal(zone)
    if not t:
        return dict(ok=False, msg="📡 هیچ امضای لرزه‌ای در این منطقه ثبت نشد.")
    pts = round(random.uniform(12, 26) * rad * (1.25 if _zone_matches(t, zone) else 0.85), 1)
    res = add_points(uid, t["id"], pts, "track")
    import player as PL
    PL.progress(uid, "track", 1)
    PL.track_stat(uid, "research_done", 0)
    known = is_known(uid, t["id"])
    label, emj = codename(uid, t) if known else (f"UNKNOWN SIGNATURE {t['id'][:4].upper()}", "🕳")
    return dict(ok=True, tid=t["id"], pts=pts, msg=(
        f"📡 <b>SIGNAL INTERCEPT</b>\n"
        f"🌍 {TN.ENVS.get(zone, zone)} · امضا: <code>{t['id'][:6].upper()}</code>\n"
        f"{'🔓 پرونده باز شد: ' + label if res.get('advanced') and res.get('stage', 0) >= 1 else '🗝 هنوز کلاسیفای‌د — ' + str(pts) + ' امتیاز تحقیق'}"),
        advanced=res.get("advanced", 0))


def pick_signal(zone: str):
    """سیگنال‌ها از استخر تایتان‌های سازگار با منطقه (نه همه‌ی دیتابیس)."""
    pool = [t for t in TN.TITANS.values() if t.get("env", {}).get(zone)]
    if not pool:
        pool = list(TN.TITANS.values())
    w = [1.0 / (1 + balance.titans_rarity_idx(t["rar"])) for t in pool]
    return random.choices(pool, weights=w, k=1)[0]


def _zone_matches(t: dict, zone: str) -> bool:
    return zone in (t.get("env") or {})


def player_energy(uid: int) -> float:
    p = db.db().player(uid)
    return float(p.get("energy") or 0) if p else 0.0


def sample(uid: int, tid: str, chat: dict = None) -> dict:
    """🧬 نمونه‌برداری میدانی — ریسک دارد؛ گاهی با خون تمام می‌شود."""
    import player as PL
    p = PL.get(uid)
    t = TN.get(tid)
    if not t:
        return dict(ok=False, msg="🗄 چنين تایتانی در دیتابیس نیست.")
    if p.get("dead_until") and float(p["dead_until"]) > now():
        return dict(ok=False, msg=f"☠️ Recovery Mode — {PL.cd_left(uid, 'recovery')} ثانیه.")
    if PL.on_cd(uid, "sample"):
        return dict(ok=False, msg=f"⏳ نمونه‌برداری در آماده‌سازی: {PL.cd_left(uid, 'sample'):.0f} ثانیه")
    r = row(uid, tid)
    if int(r.get("stage") or 0) < 2:
        return dict(ok=False, msg=f"🔒 برای نمونه‌برداری به «{STAGES[1]['label']}» نیاز است. "
                                  f"ابتدا با /track سیگنال را محکم کن (امضا/بازدید).")
    if player_energy(uid) < 22:
        return dict(ok=False, msg="🔋 ۲۲ انرژی لازم است.")
    PL.set_cd(uid, "sample", config.CD_SAMPLE)
    db.db().apply(uid, energy=max(0.0, player_energy(uid) - 22))
    zone = (chat or {}).get("zone") or "ocean"
    risk = 0.10 + 0.05 * balance.titans_rarity_idx(t["rar"]) - (0.0 if _zone_matches(t, zone) else 0.03)
    rig = 1 + 0.1 * (chat or {}).get("danger", 1)
    PL.track_stat(uid, "samples", 1)
    PL.progress(uid, "sample", 1)
    if random.random() < risk:
        hurt = round(random.uniform(24, 60) * rig, 1)
        newhp = float(p["hp"]) - hurt
        if newhp <= 0:
            PL.die(uid, "SAMPLING_ACCIDENT")
            return dict(ok=True, msg=(f"🩸 <b>SAMPLING FAILURE</b> — {t['name']}\n"
                                      f"نمونه‌ی ناخوش‌ایند… واحد واکنش سریع تو را برداشت.\n"
                                      f"☠️ <b>AGENT DOWN</b> · Recovery {config.RECOVERY_MINUTES} دقیقه"))
        db.db().apply(uid, hp=max(1.0, newhp), resolve=max(0.0, float(p.get("resolve") or 0) - 6))
        return dict(ok=True, msg=(f"⚠️ <b>SPECIMEN SECURED / INJURY</b>\n"
                                  f"🧬 {hurt:.0f} آسیب · 🎯 +۴۰ امتیاز تحقیق {t['name']}"))
    pts = random.uniform(34, 62)
    res = add_points(uid, tid, pts, "sample")
    return dict(ok=True, msg=(f"🧬 <b>SAMPLE SECURED</b> — {t['name']}\n"
                              f"🔬 +{pts:.0f} امتیاز تحقیق"
                              + (f"\n🚨 <b>STAGE UP</b> → {STAGES[res['stage']]['label']}" if res.get("advanced") else "")))


def analyze(uid: int, tid: str) -> dict:
    """🔬 شروع سیکل آزمایشگاه (صف واقع‌زمان)."""
    import player as PL
    t = TN.get(tid)
    if not t:
        return dict(ok=False, msg="🗄 تایتان نامعتبر.")
    p = PL.get(uid)
    r = row(uid, tid)
    if int(r.get("stage") or 0) < 3:
        return dict(ok=False, msg=f"🔒 تحلیل نیازمند «{STAGES[3]['label']}» است.")
    if float(p.get("lab_until") or 0) > now():
        left = float(p["lab_until"]) - now()
        return dict(ok=False, msg=f"⏳ آزمایشگاه درگیر {p.get('lab_titan')} است — {left/60:.0f} دقیقه.")
    g = balance.gate_of(t["rar"])
    cost = dict(dna=2 + g["idx"], fdata=1 + g["idx"], credits=600 + 260 * g["idx"])
    if not PL.can_afford(p, **cost):
        return dict(ok=False, msg="📦 کمبود منبع برای سیکل تحلیل: "
                                  + " · ".join(f"{k} ×{v}" for k, v in cost.items()))
    _, lab_mult, lab_lvl = _facility_bonus(uid)
    dur = config.LAB_MINUTES * 60 * (0.72 + 0.28 * (1 + g["idx"]) / 2) / lab_mult
    PL.spend(uid, **cost)
    PL.track_stat(uid, "research_done", 0)
    db.db().apply(uid, lab_titan=tid, lab_stage="analyze", lab_until=now() + dur,
                  lab_points=float(r.get("points") or 0))
    PL.set_cd(uid, "analyze", config.CD_ANALYZE)
    return dict(ok=True, msg=(f"🔬 <b>ANALYSIS QUEUE</b> — {t['name']}\n"
                              f"⏱ {dur/60:.0f} دقیقه · هزینه: "
                              + " · ".join(f"{k} {v}" for k, v in cost.items())
                              + "\n<i>با /lab نتیجه را بگیر.</i>"),
                minutes=round(dur / 60, 1))


def lab_check(uid: int) -> dict:
    """اتمام سیکل آزمایشگاه (از تیک/دستور صدا زده می‌شود)."""
    import player as PL
    p = PL.get(uid)
    if not p or not p.get("lab_titan") or float(p.get("lab_until") or 0) > now():
        return dict(ok=False)
    tid, stage = p["lab_titan"], p.get("lab_stage")
    t = TN.get(tid) or {}
    _, lab_mult, lab_lvl = _facility_bonus(uid)
    fail = max(0.04, config.LAB_FAIL - 0.03 * lab_lvl)
    db.db().apply(uid, lab_titan=None, lab_stage=None, lab_until=0, lab_points=0)
    PL.progress(uid, "lab", 1)
    if random.random() < fail:
        return dict(ok=True, msg=(f"🧪 <b>LAB FAILURE</b> — {t.get('name', '—')}\n"
                                  f"نمونه آلوده شد؛ ۴۰٪ پیشرفت از دست رفت.\n"
                                  f"🏢 ارتقای Laboratory در Division ریسک را کم می‌کند."),
                    fail=True)
    pts = random.uniform(90, 150) * lab_mult
    res = add_points(uid, tid, pts, "analyze")
    import player as _P
    _P.add_res(uid, fdata=1)
    _P.add_xp(uid, 12 + 4 * balance.titans_rarity_idx(t.get("rar", "RARE")))
    return dict(ok=True, msg=(f"🔬 <b>ANALYSIS COMPLETE</b> — {t.get('name')}\n"
                              f"📊 +{pts:.0f} امتیاز تحقیق · 📡 +۱ Classified Data\n"
                              + (f"🚨 <b>STAGE UP</b> → {STAGES[res['stage']]['label']}" if res.get("advanced") else "")),
                advanced=res.get("advanced", 0))


def gates_ok(p: dict, t: dict) -> dict:
    """دروازه‌ی نهایی: پیوند با تایتان (بسیار سخت)."""
    g = balance.gate_of(t["rar"])
    r = row(p["user_id"], t["id"])
    miss = []
    if int(r.get("stage") or 0) < 4:
        miss.append(f"مرحله‌ی تحلیل (الزام: {STAGES[4]['label']})")
    if float(p.get("dna") or 0) < g["dna"]:
        miss.append(f"🧬 {g['dna']} DNA Fragment")
    if float(p.get("cores") or 0) < g["cores"]:
        miss.append(f"💎 {g['cores']} Titan Core")
    if float(p.get("fdata") or 0) < g["fdata"]:
        miss.append(f"📡 {g['fdata']} Classified Data")
    if int(r.get("kills") or 0) < g["kills"]:
        miss.append(f"⚔️ {g['kills']} پیروزی در شکار این تایتان")
    if int(p.get("rank") or 1) < g["rank"]:
        miss.append(f"🎖 رتبه‌ی {g['rank']}")
    return dict(ok=not miss, missing=miss, gate=g)


def bond(uid: int, tid: str) -> dict:
    """👑 پیوند: بازکردن اکسِ تایتان در نبرد."""
    import player as PL
    p = PL.get(uid)
    t = TN.get(tid)
    if not t:
        return dict(ok=False, msg="🗄 تایتان نامعتبر.")
    if PL.on_cd(uid, "bond"):
        return dict(ok=False, msg=f"⏳ پروتکل پیوند خنک است — {PL.cd_left(uid, 'bond'):.0f}s")
    chk = gates_ok(p, t)
    if not chk["ok"]:
        return dict(ok=False, msg=f"🔒 <b>BOND DENIED</b> — {t['name']}\n"
                                  + "\n".join(f"▪️ {m}" for m in chk["missing"]))
    g = chk["gate"]
    PL.spend(uid, dna=-g["dna"], fdata=-g["fdata"], cores=-g["cores"])
    PL.set_cd(uid, "bond", config.CD_BOND)
    r = row(uid, tid, create=True)
    stage = max(int(r.get("stage") or 0), 5)
    db.db().ex("UPDATE bonds SET stage=?, bond=?, points=0, bond_points=? WHERE user_id=? AND titan_id=?",
               (stage, max(1, int(r.get("bond") or 0)), 0, int(uid), tid))
    db.db().feed("bond", f"{uid}:{tid}")
    return dict(ok=True, msg=(f"👑 <b>TITAN BOND ESTABLISHED</b>\n"
                              f"{t['emj']} <b>{t['name']}</b> · تراز ۱\n"
                              f"▸ اکسِ «{t['name']}» در نبرد باز شد (دکمه‌ی ☄️)\n"
                              f"▸ با /bond up تراز را بالا ببر\n"
                              f"<i>{t.get('lore', '')}</i>"))


def bond_up(uid: int, tid: str) -> dict:
    import player as PL
    p = PL.get(uid)
    t = TN.get(tid)
    r = row(uid, tid)
    b = int(r.get("bond") or 0)
    if b < 1:
        return dict(ok=False, msg="🔒 ابتدا /bond برای ایجاد پیوند.")
    if b >= config.BOND_MAX:
        return dict(ok=False, msg="👑 پیوند در سقف نهایی (تراز ۵) است.")
    g = balance.gate_of(t["rar"])
    cost = dict(cores=g["cores"] * (b + 1), dna=int(g["dna"] * 0.8) * (b + 1),
                credits=4000 * (b + 1) * (1 + g["idx"] * 0.4))
    if not PL.can_afford(p, **cost):
        return dict(ok=False, msg="📦 کمبود منبع: " + " · ".join(f"{k} {v}" for k, v in cost.items()))
    PL.spend(uid, **cost)
    db.db().ex("UPDATE bonds SET bond=? WHERE user_id=? AND titan_id=?", (b + 1, int(uid), tid))
    return dict(ok=True, msg=f"👑 <b>BOND LEVEL {b + 1}</b> — {t['name']}\n"
                             f"⤷ اکس قوی‌تر، مزیت آماری بیشتر، Cooldown کمتر.")


def bond_rows(uid: int) -> list:
    """پیوندهای فعال (stage≥5 = پیوند بسته‌شده) با قدرت تایتان برای balance."""
    rows = db.db().q("SELECT * FROM bonds WHERE user_id=? AND stage>=5 AND bond>0 ORDER BY bond DESC",
                     (int(uid),))
    out = []
    for r in rows:
        t = TN.get(r["titan_id"])
        if not t:
            continue
        out.append(dict(titan_id=r["titan_id"], stage=r["stage"], bond=r["bond"],
                        points=r["points"], kills=r["kills"], t_power=t["power"],
                        name=t["name"], emj=t["emj"], rar=t["rar"]))
    return out


def known_rows(uid: int) -> list:
    return db.db().q("SELECT * FROM bonds WHERE user_id=? ORDER BY stage DESC, points DESC", (int(uid),))


def bond_bonuses(uid: int) -> list:
    """مزیت آماری پیوندها (برای balance.player_block)."""
    out = []
    for bt in bond_rows(uid):
        t = TN.get(bt["titan_id"])
        if not t:
            continue
        g = balance.bond_gain(t["power"], bt["bond"])
        g["echo"] = dict(tid=t["id"], name=t["name"], emj=t["emj"], bond=bt["bond"])
        g["tags"] = list(t.get("tags") or [])[:2]
        out.append(g)
    return out


def echo_options(uid: int) -> list:
    """اکس‌های قابل‌استفاده: هر تایتانِ پیوندخورده با تراز ≥۲."""
    out = []
    for bt in bond_rows(uid):
        if int(bt.get("bond") or 0) < 2:
            continue
        t = TN.get(bt["titan_id"])
        if not t:
            continue
        ult = __import__("abilities").ult_of(t["id"])
        if ult:
            out.append(dict(tid=t["id"], name=t["name"], emj=t["emj"], ability=ult["id"],
                            bond=int(bt["bond"])))
    return out


def kill_bump(uid: int, tid: str, *, victory: bool = True) -> dict:
    """پس از نبرد: ثبت کشتار + امتیاز تحقیق."""
    t = TN.get(tid)
    if not t:
        return dict()
    r = row(uid, tid, create=True)
    kills = int(r.get("kills") or 0) + (1 if victory else 0)
    db.db().ex("UPDATE bonds SET kills=?, last=? WHERE user_id=? AND titan_id=?",
               (kills, now(), int(uid), tid))
    res = add_points(uid, tid, (55 if victory else 14) * (1 + 0.1 * balance.titans_rarity_idx(t["rar"])),
                     "combat")
    return dict(kills=kills, advanced=res.get("advanced", 0), stage=res.get("stage", 0))


def set_stage(uid: int, tid: str, stage: int):
    row(uid, tid, create=True)
    db.db().ex("UPDATE bonds SET stage=? WHERE user_id=? AND titan_id=?", (int(stage), int(uid), tid))


# ─────────── رمزنگاری MONARCH (پازلی) ───────────
PUZZLE_KINDS = ("cipher", "seismic", "sigil")


def puzzle_new(uid: int) -> dict:
    """ساخت پازل: کد امضای لرزه‌ای / رمز سزار / اولویتِ پرونده."""
    import player as PL
    if PL.on_cd(uid, "puzzle"):
        return dict(ok=False, msg=f"⏳ رمز بعدی در {PL.cd_left(uid, 'puzzle'):.0f} ثانیه.")
    pool = [t for t in TN.TITANS.values() if stage_of(uid, t["id"]) >= 1] or list(TN.TITANS.values())
    t = random.choice(pool)
    kind = random.choice(PUZZLE_KINDS)
    shift = random.randint(1, 7)
    if kind == "cipher":
        name = t["name"].upper().replace(" ", "")
        enc = "".join(chr((ord(c) - 65 + shift) % 26 + 65) for c in name if c.isalpha())
        q = f"رمز MONARCH: «{enc}» با شیفت {shift} — کدام تایتان؟"
    elif kind == "seismic":
        mag = round(3.1 + t["threat"] * 1.4 + random.uniform(0, .9), 1)
        q = (f"ثبت لرزه‌نگار: بزرگی {mag}، عمق {random.randint(2, 60)}km، "
             f"امضای {TN.ENVS.get(random.choice(list(t['env'] or {'ocean': 1})), '🌊')} — "
             f"کدام تایتان بیشترین سازگاری را دارد؟")
    else:
        q = (f"پرونده می‌گوید: «{t['lore'][:96]}» · نقطه‌ی ضعف: "
             f"{', '.join(t['weak'][:2]) or '—'} — این کد به کدام تایتان است؟")
    opts = [t] + random.sample([x for x in TN.TITANS.values() if x["id"] != t["id"]], 3)
    random.shuffle(opts)
    PL.set_cd(uid, "puzzle", config.CD_PUZZLE)
    qid = f"pz:{uid}"
    db.db().setv(qid, dict(tid=t["id"], answer=t["id"], opts=[o["id"] for o in opts],
                           kind=kind, shift=shift, ts=now()))
    return dict(ok=True, q=q, opts=[o["name"] for o in opts], ids=[o["id"] for o in opts],
                tid=t["id"], kind=kind)


def puzzle_answer(uid: int, chosen: str) -> dict:
    """پاسخ دکمه‌ای؛ درست → امتیاز تحقیق روی همان تایتان."""
    import player as PL
    data = db.db().getv(f"pz:{uid}", None)
    if not data:
        return dict(ok=False, msg="🧮 پازلی باز نیست — /puzzle")
    right = data["answer"] == chosen
    db.db().setv(f"pz:{uid}", None)
    if not right:
        return dict(ok=False, right=data["answer"],
                    msg="❌ <b>DECODE FAILED</b> — امضا ناخوانا ماند. (بدون جریمه، فقط زمان)")
    PL.track_stat(uid, "puzzles", 1)
    PL.progress(uid, "puzzle", 1)
    res = add_points(uid, data["tid"], config.PUZZLE_POINTS, "puzzle")
    t = TN.get(data["tid"]) or {}
    return dict(ok=True, msg=(f"✅ <b>DECODE SUCCESS</b> — {t.get('name', '')}\n"
                              f"🔬 +{config.PUZZLE_POINTS} امتیاز تحقیق"
                              + (f"\n🚨 <b>STAGE UP</b> → {STAGES[res['stage']]['label']}" if res.get("advanced") else "")))


def dossier(uid: int, t: dict) -> str:
    import ui
    r = row(uid, t["id"])
    known = is_known(uid, t["id"])
    name, emj = codename(uid, t)
    if not known:
        return ("\n".join([
            f"{emj} <b>MONARCH DATABASE</b> — <code>{t['id'][:6].upper()}</code>",
            "🗝 STATUS: <b>UNKNOWN</b>", "",
            "<i>هیچ امضای تایید‌شده‌ای ثبت نشده.</i>",
            f"▪️ توده‌ی تخمینی: {random.Random(hash(t['id'])).randint(2, 9) * 10}kt",
            f"▪️ تهدید: {ui.threat_stars(t.get('threat', 1))}",
            "", "📡 با /track در منطقه‌ی سازگار سیگنال جمع کن."]))
    stats = [(m, t[k]) for m, k in (("❤️ HP", "hp"), ("⚔️ ATK", "atk"), ("🛡 DEF", "df"), ("⚡ SPD", "spd"),
                                    ("🔋 Energy", "eng"), ("🧠 INT", "int"), ("🧬 Regen", "reg"),
                                    ("🎯 ACC", "acc"), ("🏃 Dodge", "dodge"), ("🛡 RES", "res"))]
    ab = []
    import abilities as AB
    for aid in t["ab"]:
        a = AB.get(aid)
        ab.append(f"☄️ {a['name']} <i>({a['cost']}⚡ / cd{a['cd']})</i> — {a['desc']}")
    ult = AB.ult_of(t["id"])
    pas = AB.passive_of(t["id"])
    g = balance.gate_of(t["rar"])
    lines = [f"{emj} <b>{name}</b> · {ui.rarity_badge(t['rar'])}",
             f"<i>{t.get('origin', '')} · {t.get('h', '—')} · {t.get('w', '—')}</i>",
             "", t.get("lore", ""), "", "▬▬▬▬▬▬▬▬▬▬▬", "📊 <b>STATS</b>"]
    for i in range(0, len(stats), 2):
        pair = stats[i:i + 2]
        lines.append(" · ".join(f"{lbl} <code>{v:,}</code>" for lbl, v in pair))
    lines += ["", f"🌍 <b>ENVIRONMENT</b>: " + (" · ".join(f"{TN.ENVS.get(k, k)} ×{v}"
                                                            for k, v in (t.get("env") or {}).items()) or "—"),
              f"❌ <b>WEAKNESS</b>: {', '.join(t['weak']) or '—'}",
              f"🛡 <b>RESISTANCE</b>: {', '.join(t['resist']) or '—'}",
              f"🧬 <b>PASSIVE</b>: {pas['emj']} {pas['name']} — {pas['desc']}", "",
              "☄️ <b>ABILITIES</b>"] + ab
    if ult:
        lines += ["", f"👑 <b>ULTIMATE</b>: {ult['emj']} {ult['name']} <i>({ult['cost']}⚡)</i> — {ult['desc']}"]
    lines += ["", f"🔬 <b>RESEARCH</b>: {bar(r)}", f"⚔️ شکار موفق: <b>{r.get('kills', 0)}</b> · "
                f"👑 تراز پیوند: <b>{r.get('bond', 0)}</b>"]
    chk = gates_ok(db.db().player(uid) or {}, t)
    if int(r.get("stage") or 0) >= 4 and not int(r.get("bond") or 0):
        if chk["missing"]:
            lines += ["", "🔓 <b>BOND REQUIREMENTS</b>"] + [f"▪️ {m}" for m in chk["missing"]]
        else:
            lines += ["", f"✅ آماده‌ی پیوند — /bond {t['id']}"]
    return "\n".join(lines)


def discovery_ranking(limit: int = 8) -> list:
    rows = db.db().q("""SELECT b.user_id, COUNT(*) c, SUM(b.stage) s FROM bonds b
                        WHERE b.stage>=3 GROUP BY b.user_id ORDER BY s DESC LIMIT ?""", (limit,))
    return rows
