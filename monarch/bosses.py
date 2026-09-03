# 👑 Boss Engine — فاز، Rage Mode، AI Behavior، حمله‌ی ویژه با پنجره‌ی پاسخ
import random

import balance
import config
import db
import emoji as EMJ
import titans as TN
from db import now

# حلقه‌های «پاسخ» برای حمله‌های ویژه — combat.special از همین‌جا می‌آید
COUNTER_KEYS = ("guard", "dodge", "counter", "retreat", "charge")

BOSSES = {
    # ── NORMAL: عملیات‌های روتین MONARCH ──
    "nest_broodmother": dict(
        name="🕷 Nest Broodmother", emj="queen", base="kumonga", tier="NORMAL", enc=0.75,
        zones=("jungle", "hollow"), mins=30, threat=2,
        lore="لانه‌ی جزیره‌ی جمجمه؛ ۴۰۰ تخم در سه متر مکعب.",
        phases=[dict(at=0.66, name="Hatch — نوزادها بیرون می‌آیند", atk=0.18),
                dict(at=0.33, name="Web Fortress", df=0.18)],
        specials=[dict(name="Silk Dump", counter="dodge", mult=1.7, emj="web"),
                  dict(name="Egg Burst", counter="guard", mult=1.5, emj="acid")],
        reward=dict(credits=1400, dna=2, mats=2)),
    "ash_stalker": dict(
        name="🐗 Ash Stalker", emj="horns", base="baragon", tier="NORMAL", enc=0.8,
        zones=("volcano", "city"), mins=28, threat=2,
        lore="نمونه‌ی زخمی که به سطح آمده؛ هر نفسش گوگرد است.",
        phases=[dict(at=0.5, name="Magma Vein Exposure", atk=0.22)],
        specials=[dict(name="Pyro Spittle", counter="dodge", mult=1.6, emj="flame"),
                  dict(name="Ground Splitter", counter="guard", mult=1.5, emj="heavy")],
        reward=dict(credits=1500, cells=2, mats=2)),
    "tide_reaver": dict(
        name="🦞 Tide Reaver", emj="ocean", base="ebirah", tier="NORMAL", enc=0.82,
        zones=("ocean", "city"), mins=26, threat=2,
        lore="راهبندِ دریایی؛ کشتی‌ها را لانه می‌کند.",
        phases=[dict(at=0.6, name="Rip Current", atk=0.14, df=0.06)],
        specials=[dict(name="Claw Pincer", counter="guard", mult=1.55, emj="claw"),
                  dict(name="Ink Blindness", counter="dodge", mult=1.4, emj="dark")],
        reward=dict(credits=1450, cells=2, fdata=1)),
    # ── ELITE: پرونده‌های باز ──
    "prototype_kiryu": dict(
        name="🤖 Prototype KIRYU", emj="mech", base="mechagodzilla", tier="ELITE", enc=0.95,
        zones=("city", "nuclear"), mins=40, threat=3,
        lore="پیش‌نمونه‌ی کنترل‌شده‌ی MONARCH؛ هسته‌اش هنوز ناپایدار است.",
        phases=[dict(at=0.7, name="Coolant Breach — حرارت بالا", atk=0.2),
                dict(at=0.35, name="Locked Target Protocol", atk=0.16, df=0.14)],
        specials=[dict(name="Proton Sweep", counter="dodge", mult=1.9, emj="spark"),
                  dict(name="Missile Salvo", counter="guard", mult=1.7, emj="heavy"),
                  dict(name="Target Lock", counter="counter", mult=1.3, emj="track")],
        reward=dict(credits=4200, cells=4, mats=4, cores=1)),
    "siren_phase2": dict(
        name="🟢 Siren Phase II", emj="hedorah", base="hedorah", tier="ELITE", enc=0.98,
        zones=("city", "ocean"), mins=42, threat=4,
        lore="فاز پروازی؛ ابر اسیدی روی شهر ایستاده است.",
        phases=[dict(at=0.66, name="Descent — فرود روی دکل", atk=0.18),
                dict(at=0.28, name="Mineral Feast", heal_pct=0.12)],
        specials=[dict(name="Acid Rain", counter="guard", mult=1.75, emj="acid"),
                  dict(name="Corrosive Grip", counter="dodge", mult=1.6, emj="web")],
        reward=dict(credits=4600, mats=5, fdata=2, cores=1)),
    "flying_gigan": dict(
        name="👽 Cyber Enforcer Gigan", emj="gigan", base="gigan", tier="ELITE", enc=1.0,
        zones=("city", "space"), mins=38, threat=4,
        lore="فرستاده‌ی تمدن‌های بیگانه؛ برای اعدام پادشاه ساخته شد.",
        phases=[dict(at=0.5, name="Blade Overdrive", atk=0.26)],
        specials=[dict(name="Cyclops Sweep", counter="dodge", mult=1.85, emj="spark"),
                  dict(name="Saw Descent", counter="guard", mult=1.7, emj="blade")],
        reward=dict(credits=5000, cores=1, mats=5, fdata=2)),
    "deep_coil": dict(
        name="🐍 Deep Coil Manda", emj="manda", base="manda", tier="ELITE", enc=0.94,
        zones=("ocean", "city"), mins=36, threat=3,
        lore="مارِ قاره‌ها؛ when it wakes, tide charts are rewritten.",
        phases=[dict(at=0.6, name="Constriction Protocol", atk=0.18)],
        specials=[dict(name="Coil Crush", counter="retreat", mult=1.8, emj="boss"),
                  dict(name="Whirlpool Drag", counter="dodge", mult=1.6, emj="ocean")],
        reward=dict(credits=4100, dna=4, cells=3)),
    # ── LEGENDARY ──
    "stormlord": dict(
        name="🐉 Stormlord Ghidorah", emj="ghidorah", base="king_ghidorah", tier="LEGENDARY",
        enc=1.15, zones=("city", "space", "ocean"), mins=55, threat=5,
        lore="سه سر، سه تصمیم؛ طوفان فقط اثر جانبی است.",
        phases=[dict(at=0.72, name="Front Alpha — جبهه‌ی طوفان", atk=0.2, env="city"),
                dict(at=0.44, name="Gravity Well", atk=0.16, df=0.1),
                dict(at=0.18, name="Annihilation Chorus", atk=0.32)],
        specials=[dict(name="Gravity Ray Triad", counter="dodge", mult=2.0, emj="storm"),
                  dict(name="Lightning Crown", counter="guard", mult=1.8, emj="bolt"),
                  dict(name="Tail Sweep Chaos", counter="counter", mult=1.5, emj="clash")],
        reward=dict(credits=18000, cores=3, fdata=6, dna=8, cells=6)),
    "floral_nightmare": dict(
        name="🧬 Floral Nightmare", emj="biollante", base="biollante", tier="LEGENDARY",
        enc=1.08, zones=("jungle", "nuclear"), mins=50, threat=4,
        lore="ترکیب گل و DNA گودزیلا؛ ریشه در خاکِ آلوده دارد.",
        phases=[dict(at=0.6, name="Second Bloom", atk=0.22, heal_pct=0.1),
                dict(at=0.3, name="Root Network", df=0.22)],
        specials=[dict(name="Vine Impalement", counter="guard", mult=1.85, emj="dna"),
                  dict(name="Acid Pollen", counter="dodge", mult=1.7, emj="acid")],
        reward=dict(credits=15500, dna=10, cores=2, mats=5)),
    "perfection": dict(
        name="☠️ Destoroyah: Perfection", emj="destoroyah", base="destoroyah", tier="LEGENDARY",
        enc=1.2, zones=("city", "nuclear", "volcano"), mins=58, threat=5,
        lore="پرونده‌ی «مرگ گودزیلا»؛ تکامل در میانه‌ی نبرد.",
        phases=[dict(at=0.75, name="Agonized Swarm", atk=0.2),
                dict(at=0.45, name="Micro-Oxygen Overload", atk=0.26),
                dict(at=0.2, name="Perfection — بال‌ها باز شد", atk=0.3, df=0.14)],
        specials=[dict(name="Oxygen Destroyer Echo", counter="dodge", mult=2.1, emj="atom"),
                  dict(name="Ash Barrage", counter="guard", mult=1.75, emj="flame"),
                  dict(name="Cellular Rebirth", counter="counter", mult=1.2, emj="phase")],
        reward=dict(credits=21000, cores=4, fdata=7, dna=9)),
    # ── ALPHA: تهدیدهای سطحِ آخر ──
    "axe_bearer": dict(
        name="🦍 Kong: Axe Bearer", emj="kong", base="kong", tier="ALPHA", enc=1.12,
        zones=("hollow", "jungle", "city"), mins=48, threat=4,
        lore="وقتی تبر را برمی‌دارد، دیگر مذاکره‌ای در کار نیست.",
        phases=[dict(at=0.62, name="Charge Resonance", atk=0.2),
                dict(at=0.28, name="Axe Overcharge", atk=0.28)],
        specials=[dict(name="Axe Arc", counter="dodge", mult=1.9, emj="heavy"),
                  dict(name="Ground Shock", counter="guard", mult=1.7, emj="clash")],
        reward=dict(credits=12000, cores=2, mats=6, cells=5)),
    "siege_mecha": dict(
        name="🤖 Mechagodzilla: Siege", emj="mecha", base="mechagodzilla", tier="ALPHA", enc=1.2,
        zones=("city", "space"), mins=56, threat=5,
        lore="سه گانگ، سه حالت؛ حالت محاصره یعنی شهر تخلیه شود.",
        phases=[dict(at=0.7, name="Proton Array Online", atk=0.22),
                dict(at=0.35, name="Annihilation Protocol", atk=0.34, heat=30)],
        specials=[dict(name="Proton Scream", counter="guard", mult=2.0, emj="mecha"),
                  dict(name="Barrage Lock", counter="dodge", mult=1.8, emj="heavy"),
                  dict(name="Self-Diagnostic Purge", counter="counter", mult=1.1, emj="binary")],
        reward=dict(credits=24000, cores=4, fdata=8, cells=8)),
    # ── WORLD BOSS (راید جهانی) ──
    "hollow_breach": dict(
        name="🌒 The Hollow Breach", emj="breach", base="skar_king", tier="WORLD", enc=1.7,
        zones=("hollow", "jungle", "ocean"), mins=180, threat=5, world=True,
        lore="شکافی در پوست زمین؛ از آن بیرون، زنجیرها دیده می‌شوند.",
        phases=[dict(at=0.8, name="Beast Tide — موج موجودات", atk=0.18),
                dict(at=0.55, name="Chain Break", atk=0.24),
                dict(at=0.3, name="Monollith Resonance", atk=0.3, df=0.2),
                dict(at=0.1, name="Skar Descends", atk=0.42)],
        specials=[dict(name="Chain Sweep", counter="dodge", mult=2.2, emj="boss"),
                  dict(name="Bone Storm", counter="guard", mult=2.0, emj="heavy"),
                  dict(name="Domination Roar", counter="counter", mult=1.4, emj="crown")],
        reward=dict(credits=60000, cores=10, fdata=12, dna=14, cells=10)),
    "crystal_tree": dict(
        name="💎 The Crystal Tree", emj="spacegod", base="spacegodzilla", tier="WORLD", enc=1.65,
        zones=("space", "antarctica", "city"), mins=170, threat=5, world=True,
        lore="ریشه‌های بلورین در یخ جنوبگان؛ هر شاخه یک پایگاه را بلعیده است.",
        phases=[dict(at=0.78, name="Crystal Bloom", atk=0.2),
                dict(at=0.45, name="Reflective Canopy", df=0.3, atk=0.16),
                dict(at=0.15, name="Corona Convergence", atk=0.38)],
        specials=[dict(name="Corona Cascade", counter="dodge", mult=2.1, emj="gem"),
                  dict(name="Diameter Cage", counter="guard", mult=1.8, emj="lock"),
                  dict(name="Mirror Refraction", counter="counter", mult=1.5, emj="light")],
        reward=dict(credits=55000, cores=9, fdata=14, cells=9)),
    "long_winter": dict(
        name="❄️ Shimo: The Long Winter", emj="shimo", base="shimo", tier="WORLD", enc=1.6,
        zones=("antarctica", "ocean", "city"), mins=165, threat=5, world=True,
        lore="هر جا که پا می‌گذارد، عصر یخبندان می‌آید.",
        phases=[dict(at=0.8, name="Frost Quake", atk=0.18),
                dict(at=0.5, name="Glacial Advance", atk=0.24, df=0.16),
                dict(at=0.2, name="Absolute Zero", atk=0.4)],
        specials=[dict(name="Ice Age Cloud", counter="guard", mult=1.9, emj="ice"),
                  dict(name="Rime Collapse", counter="dodge", mult=2.0, emj="frost"),
                  dict(name="Deep Freeze Pulse", counter="charge", mult=1.4, emj="lock")],
        reward=dict(credits=52000, cores=8, cells=12, mats=10)),
    "resonance_chorus": dict(
        name="🦇 Resonance Chorus", emj="muto", base="muto_prime", tier="WORLD", enc=1.5,
        zones=("city", "hollow"), mins=150, threat=4, world=True,
        lore="دو جفت، چهار صدا؛ فرکانسی که استخوان را می‌شکند.",
        phases=[dict(at=0.7, name="Silence Barrage", atk=0.2),
                dict(at=0.35, name="Nest Call", atk=0.3)],
        specials=[dict(name="Fracture Wave", counter="dodge", mult=1.9, emj="track"),
                  dict(name="Brood Rush", counter="guard", mult=1.7, emj="swarm")],
        reward=dict(credits=44000, cores=6, dna=12, fdata=8)),
    "orca_protocol": dict(
        name="🛰 ORCA Protocol — Rogue", emj="moguera", base="moguera", tier="WORLD", enc=1.42,
        zones=("nuclear", "city", "space"), mins=150, threat=4, world=True,
        lore="دستگاه ORCA از کنترل خارج شده و خودش «فرمان» می‌دهد.",
        phases=[dict(at=0.66, name="Signal Hijack", atk=0.24),
                dict(at=0.33, name="Total Sync", atk=0.32, df=0.2)],
        specials=[dict(name="Frequency Spike", counter="counter", mult=1.8, emj="signal"),
                  dict(name="Drone Swarm", counter="guard", mult=1.6, emj="mecha")],
        reward=dict(credits=40000, cores=5, fdata=12, cells=8)),
}

TIERS = ("NORMAL", "ELITE", "LEGENDARY", "ALPHA", "WORLD")
TIER_EMOJI = dict(NORMAL="💀", ELITE="🕹", LEGENDARY="☠️", ALPHA="👑", WORLD="🌒")


for _b in BOSSES.values():
    _b["emj"] = EMJ.of(_b.get("emj"), "🕹")


def by_id(bid: str) -> dict:
    return BOSSES.get(bid) or {}


def eligible(zone: str, tier: str = None) -> list:
    out = []
    for bid, b in BOSSES.items():
        if tier and b["tier"] != tier:
            continue
        if b.get("world"):
            continue
        if not b.get("zones") or zone in b["zones"]:
            out.append(bid)
    if not out:
        out = [bid for bid, b in BOSSES.items() if not b.get("world")]
    return out


def pick(zone: str, danger: int = 1, hour: int = None) -> str:
    """انتخاب باس بر اساس خطر منطقه و ساعت شب (شب‌ها خطرناک‌تر)."""
    night = 22 <= (hour if hour is not None else db.local_hour()) or (hour or 0) <= 4
    pool = eligible(zone)
    weights = []
    for bid in pool:
        b = BOSSES[bid]
        w = {1: 4.0, 2: 2.4, 3: 1.2, 4: 0.6, 5: 0.25}.get(danger, 1.0)
        if night:
            w *= 1.25 if b["tier"] in ("ELITE", "LEGENDARY") else 0.9
        if b["tier"] == "NORMAL":
            w *= 1.6 - 0.16 * danger
        elif b["tier"] == "ELITE":
            w *= 0.7 + 0.24 * danger
        elif b["tier"] == "LEGENDARY":
            w *= 0.12 + 0.22 * danger
        else:
            w *= 0.05 + 0.16 * danger
        weights.append(max(0.02, w))
    return random.choices(pool, weights=weights, k=1)[0]


def block_for(bid: str, chat: dict = None, hp: float = None) -> dict:
    """ساختن بلاک باس از روی تایتانِ پایه + متادیتای فاز/ویژه."""
    b = by_id(bid)
    t = TN.get(b.get("base")) or TN.get("godzilla")
    danger = int((chat or {}).get("danger") or 1)
    enc = float(b.get("enc", 1.0)) * (0.92 + 0.09 * danger)
    blk = balance.titan_block(t, encounter=enc, rank=int((chat or {}).get("min_rank") or 8))
    blk["name"] = b["name"]
    blk["emj"] = b["emj"]
    blk["boss_id"] = bid
    blk["is_boss"] = True
    blk["tier"] = b["tier"]
    blk["max_hp"] = round(blk["max_hp"] * (1.25 + 0.2 * TIERS.index(b["tier"])), 1)
    if hp is not None:
        blk["hp"] = round(float(hp), 1)
    else:
        blk["hp"] = blk["max_hp"]
    blk["boss"] = dict(id=bid, name=b["name"], phases=b.get("phases") or [],
                       specials=b.get("specials") or [], tier=b["tier"],
                       rage_at=now() + config.BOSS_RAGE_AFTER, lore=b.get("lore", ""))
    blk["boss"]["base_titan"] = t["id"]
    return blk


def alert_text(bid: str, chat: dict) -> str:
    b = by_id(bid)
    t = TN.get(b.get("base")) or {}
    zone = (chat or {}).get("zone") or "ocean"
    return (f"🚨 <b>MONARCH ALERT</b>\n\n"
            f"SEISMIC ACTIVITY DETECTED.\n\n"
            f"👑 <b>TITAN:</b> {b['name']}\n"
            f"📍 <b>LOCATION:</b> {TN.ENVS.get(zone, zone)}\n"
            f"☢️ <b>THREAT:</b> {'CRITICAL' if b['tier'] in ('LEGENDARY','ALPHA','WORLD') else 'SEVERE'}\n"
            f"🕐 <b>WINDOW:</b> {b.get('mins', 35)} دقیقه\n\n"
            f"<i>{b.get('lore','')}</i>\n\n"
            f"▸ <code>/boss</code> — آغاز عملیات (حداکثر ۵ عامل در هر نبرد)\n"
            f"<i>پایه‌ی زیستی: {t.get('name','UNKNOWN')} · ضعف ثبت‌شده: {', '.join((t.get('weak') or [])[:2]) or '—'}</i>")


def spawn(chat_id: int, bid: str = None, force: bool = False) -> dict:
    """ثبت باس فعال در چت (پیام را handlers می‌فرستد تا ضداسپم نشکند)."""
    d = db.db()
    chat = d.one("SELECT * FROM chats WHERE chat_id=?", (int(chat_id),))
    if not chat:
        return dict(ok=False)
    if active(chat_id) and not force:
        return dict(ok=False, msg="🕹 همین حالا یک باس فعال است.")
    bid = bid or pick(chat.get("zone") or "ocean", int(chat.get("danger") or 1))
    b = by_id(bid)
    blk = block_for(bid, chat)
    state = dict(bid=bid, hp=blk["hp"], max_hp=blk["max_hp"], turn=0, phase=1,
                 participants={}, created=now(), combat_id=0, killed=0)
    d.ex("UPDATE chats SET boss_id=?, boss_state=?, boss_until=? WHERE chat_id=?",
         (bid, db.jdump(state), now() + b.get("mins", 35) * 60, int(chat_id)))
    return dict(ok=True, bid=bid, chat_id=int(chat_id), state=state,
                text=alert_text(bid, chat))


def active(chat_id: int) -> dict:
    chat = db.db().one("SELECT * FROM chats WHERE chat_id=?", (int(chat_id),))
    if not chat or not chat.get("boss_id"):
        return {}
    st = db.jload(chat.get("boss_state"), {}) or {}
    if float(chat.get("boss_until") or 0) <= now() or float(st.get("hp", 0)) <= 0:
        return {}
    return dict(bid=chat["boss_id"], state=st, chat=chat,
                left=max(0.0, float(chat["boss_until"]) - now()))


def sync_hp(chat_id: int, hp: float):
    d = db.db()
    chat = d.one("SELECT boss_state FROM chats WHERE chat_id=?", (int(chat_id),))
    if not chat:
        return
    st = db.jload(chat["boss_state"], {}) or {}
    st["hp"] = round(max(0.0, float(hp)), 1)
    d.ex("UPDATE chats SET boss_state=? WHERE chat_id=?", (db.jdump(st), int(chat_id)))


def add_participant(chat_id: int, uid: int, role: str = "assault"):
    d = db.db()
    chat = d.one("SELECT boss_state FROM chats WHERE chat_id=?", (int(chat_id),))
    if not chat:
        return
    st = db.jload(chat["boss_state"], {}) or {}
    p = st.setdefault("participants", {})
    row = p.setdefault(str(uid), dict(dmg=0.0, guard=0.0, support=0.0, analyze=0.0, joined=now()))
    st["participants"] = p
    d.ex("UPDATE chats SET boss_state=? WHERE chat_id=?", (db.jdump(st), int(chat_id)))


def engage(uid: int, chat: dict) -> dict:
    """آغاز/ادامه‌ی نبرد باس با استفاده از موتور نبرد (HP مشترک)."""
    import combat
    a = active(chat["chat_id"])
    if not a:
        return dict(ok=False, msg="🕹 هیچ تهدید فعالی در این منطقه نیست — «/scan».")
    bid = a["bid"]
    blk = block_for(bid, chat, hp=a["state"].get("hp"))
    res = combat.start(uid, "boss", chat=chat, boss=dict(block=blk, id=bid))
    if res.get("ok"):
        add_participant(chat["chat_id"], uid)
        st = res["state"]
        st["meta"]["chat_boss"] = int(chat["chat_id"])
        st["meta"]["boss_id"] = bid
        combat._save(res["cid"], st)
        combat._sync_boss_hp(res["cid"], st)
    return res


def settle(chat_id: int, won: bool) -> dict:
    """توزیع جوایز با پنج شاخه: Damage / Defense / Support / Last Hit / Research."""
    import player as PL
    a = active(chat_id)
    chat = db.db().one("SELECT * FROM chats WHERE chat_id=?", (int(chat_id),)) or {}
    bid = a.get("bid") or chat.get("boss_id")
    b = by_id(bid)
    st = a.get("state") or {}
    parts = st.get("participants") or {}
    if won:
        import json
        db.db().ex("UPDATE chats SET boss_id=NULL, boss_state=NULL, boss_until=0 WHERE chat_id=?",
                   (int(chat_id),))
    if not b or not parts:
        return dict(ok=True, winners={}, msg="")
    rw = b.get("reward", {})
    scored = sorted(parts.items(), key=lambda kv: -float(kv[1].get("dmg") or 0))
    awards = {}
    if scored:
        awards["damage"] = scored[0][0]
    def best(key):
        c = sorted(((u, float(v.get(key) or 0)) for u, v in parts.items()), key=lambda x: -x[1])
        return c[0][0] if c and c[0][1] > 0 else None
    awards["defense"] = best("guard")
    awards["support"] = best("support")
    awards["research"] = best("analyze")
    awards["last_hit"] = scored[0][0] if scored else None
    labels = dict(damage="🥇 Most Damage", defense="🛡 Best Defense", support="❤️ Best Support",
                  last_hit="🎯 Last Hit", research="🔬 Best Research")
    share = 1.0 / max(1, len(parts))
    lines = []
    if won:
        for uid_s, rowp in parts.items():
            uid = int(uid_s)
            amt = {k: round(v * (0.45 + 0.55 * share), 0) if isinstance(v, (int, float)) else v
                   for k, v in rw.items()}
            PL.add_res(uid, **{k: v for k, v in amt.items() if k in
                               ("credits", "cores", "dna", "cells", "mats", "fdata")})
            PL.add_xp(uid, 34 * (1 + TIERS.index(b["tier"]) * 0.35))
            PL.track_stat(uid, "boss_kills", 1)
            PL.progress(uid, "boss_join", 1)
            import division
            division.credit_activity(uid, "boss", 1)
        for key, uid_s in awards.items():
            if not uid_s:
                continue
            bonus = dict(credits=round(float(rw.get("credits", 500)) * 0.30, 0), cores=1)
            PL.add_res(int(uid_s), **bonus)
            lines.append(f"{labels[key]} → <b>{PL.name_of(int(uid_s))}</b>")
    else:
        for uid_s in parts:
            PL.add_xp(int(uid_s), 8)
        lines.append("⌛ پنجره‌ی عملیات بسته شد — تهدید عقب‌نشینی کرد (XP مشارکت ثبت شد).")
    return dict(ok=True, winners=awards, msg="\n".join(lines), tier=b["tier"], name=b["name"])


def decay() -> list:
    """پایان/پاک‌سازی باس‌های منقضی — بی‌صدا."""
    rows = db.db().q("SELECT chat_id, boss_id, boss_state FROM chats "
                     "WHERE boss_until>0 AND boss_until<?", (now(),))
    out = []
    for r in rows:
        st = db.jload(r["boss_state"], {}) or {}
        if float(st.get("hp", 0)) > 0 and st.get("participants"):
            out.append(dict(chat_id=r["chat_id"], bid=r["boss_id"], settled=settle(r["chat_id"], False)))
        db.db().ex("UPDATE chats SET boss_id=NULL, boss_state=NULL, boss_until=0 WHERE chat_id=?",
                   (r["chat_id"],))
    return out
