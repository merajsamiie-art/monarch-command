# 🗺 Expedition Engine — کاوش زمان‌دار، ریسک واقعی، غنیمت کمیاب
import random

import balance
import config
import db
import titans as TN
from db import now

ZONES = {
    "pacific": dict(name="🌊 اقیانوس آرام", env="ocean", danger=2, need_rank=1,
                    mins=(9, 20), bonus=("cells", "mats"),
                    desc="خطای صدای زیرآبی؛ بردِ MUTOها اینجاست."),
    "skull": dict(name="🏝 جزیره جمجمه", env="jungle", danger=4, need_rank=3,
                  mins=(14, 30), bonus=("dna", "mats"),
                  desc="Skullcrawlerها عطر انسان را می‌فهمند."),
    "ruins": dict(name="🏙 شهرهای ویران", env="city", danger=3, need_rank=1,
                  mins=(8, 18), bonus=("mats", "credits"),
                  desc="فلز، بتن و چیزهایی که زیر آوار نفس می‌کشند."),
    "antarctic": dict(name="❄️ جنوبگان", env="antarctica", danger=4, need_rank=6,
                      mins=(16, 34), bonus=("cores", "fdata"),
                      desc="پایگاه ۵۴. یخ، هر چیزی را ساکت می‌کند."),
    "volcano": dict(name="🌋 حلقه‌ی آتش", env="volcano", danger=5, need_rank=8,
                    mins=(18, 36), bonus=("cores", "cells"),
                    desc="دمای ۱۱۰۰ درجه. اسکنارهای فعال."),
    "hollow": dict(name="🕳 زمین توخالی", env="hollow", danger=5, need_rank=10,
                   mins=(22, 40), bonus=("cores", "dna"),
                   desc="قاعده‌ی فیزیک اینجا امضا نشده است."),
    "nuclear": dict(name="☢️ ناحیه‌ی هسته‌ای", env="nuclear", danger=5, need_rank=7,
                    mins=(15, 30), bonus=("cores", "fdata"),
                    desc="پرتوزا، پر‌بازده. Geiger از دقیقه‌ی سوم جیغ می‌زند."),
    "orbit": dict(name="🌌 مدار پایین", env="space", danger=5, need_rank=14,
                  mins=(26, 40), bonus=("cores", "fdata"),
                  desc="SpaceGodzilla بلورهایش را اینجا کاشت."),
}


def available(p: dict) -> list:
    rank = int(p.get("rank") or 1)
    return [(k, z) for k, z in ZONES.items() if rank >= z["need_rank"]]


def menu(p: dict) -> list:
    out = []
    for k, z in available(p):
        out.append(dict(cb=f"exp:{k}", text=f"{z['name']} · خطر {z['danger']}/5 · {z['mins'][0]}-{z['mins'][1]} دقیقه"))
    return out


def status(uid: int) -> dict:
    p = db.db().player(uid)
    if not p or not p.get("expedition_until"):
        return dict(active=False)
    left = float(p["expedition_until"]) - now()
    if left > 0:
        return dict(active=True, left=left, zone=p.get("expedition_zone"),
                    tier=int(p.get("expedition_tier") or 1))
    return dict(active=False, ready=True, zone=p.get("expedition_zone"),
                tier=int(p.get("expedition_tier") or 1))


def start(uid: int, zone: str, chat: dict = None) -> dict:
    import player as PL
    p = PL.get(uid)
    if not p:
        return dict(ok=False, msg="🔒 /start")
    if PL.is_dead(p):
        return dict(ok=False, msg="☠️ در حالت بازیابی هیچ تیمی اعزام نمی‌شود.")
    st = status(uid)
    if st.get("active"):
        return dict(ok=False, msg=f"⏳ کاوش فعال داری ({ZONES.get(st['zone'], {}).get('name', '')}) — "
                                 f"{st['left']/60:.0f} دقیقه.")
    z = ZONES.get(zone)
    if not z:
        return dict(ok=False, msg="🗺 این منطقه در نقشه‌ی مانارچ نیست. «/explore» برای لیست.")
    if int(p.get("rank") or 1) < z["need_rank"]:
        return dict(ok=False, msg=f"🔒 دسترسی سطح {z['need_rank']} لازم است.")
    if PL.on_cd(uid, "exped"):
        return dict(ok=False, msg=f"⏳ {PL.cd_left(uid, 'exped'):.0f} ثانیه.")
    if float(p.get("energy") or 0) < 25:
        return dict(ok=False, msg="🔋 ۲۵ انرژی برای اعزام لازم است.")
    PL.spend(uid, energy=-25)
    mins = random.randint(*z["mins"])
    tier = 1 + max(0, (int(p.get("rank") or 1) - z["need_rank"]) // 3)
    PL.set_row(uid, expedition_zone=zone, expedition_until=now() + mins * 60, expedition_tier=tier)
    PL.set_cd(uid, "exped", config.CD_EXPED)
    import division
    eng = division.facility_of(uid, "engineering")
    if eng:
        PL.set_row(uid, expedition_until=float(p["expedition_until"]) - mins * 60 * 0.06 * eng)
    return dict(ok=True, msg=(f"🗺 <b>کاوش اعزام شد</b>\n{z['name']} · تیم سطح {tier}\n"
                              f"⏱ {mins} دقیقه · 📻 «/explore report» برای وضعیت\n"
                              f"<i>{z['desc']}</i>"), minutes=mins)


def abort(uid: int) -> dict:
    p = db.db().player(uid)
    if not p or not p.get("expedition_until"):
        return dict(ok=False, msg="🗺 کاوش فعالی نداری.")
    left = float(p["expedition_until"]) - now()
    if left <= 0:
        return dict(ok=False, msg="✅ تیم در مسیر بازگشت است — «/explore claim».")
    PL = __import__("player")
    PL.set_row(uid, expedition_until=0, expedition_zone=None, expedition_tier=0)
    PL.spend(uid, credits=-200)
    return dict(ok=True, msg="💨 <b>فراخوان</b> — تیم زودتر فراخوانده شد؛ ۲۰۰ اعتبار هزینه‌ی عملیات.")


def loot_table(z: dict, tier: int, fail: bool) -> dict:
    out = dict(credits=0, cells=0, mats=0, dna=0, fdata=0, cores=0)
    if fail:
        out["credits"] = random.randint(60, 200)
        return out
    k = 1 + 0.45 * tier
    out["credits"] = round(random.randint(400, 1300) * k * (1 + 0.15 * z["danger"]), 0)
    for res in z["bonus"]:
        out[res] = round(random.uniform(1.0, 2.6) * k, 1)
    other = random.choice([x for x in ("mats", "cells", "fdata", "dna") if x not in z["bonus"]])
    out[other] = round(random.uniform(0.6, 2.0) * k, 1)
    if random.random() < config.EXPED_RARE * (1 + 0.15 * tier):
        out["cores"] = 1
    return out


def claim(uid: int, chat: dict = None) -> dict:
    """پایان کاوش: غنیمت + احتمال برخورد با تایتان."""
    import player as PL
    p = PL.get(uid)
    st = status(uid)
    if not st.get("ready"):
        return dict(ok=False, msg="🗺 کاوش فعالی برای تسویه نیست." if not st.get("active")
                    else f"⏳ {st['left']/60:.0f} دقیقه مانده.")
    zone = st["zone"] or "ruins"
    z = ZONES.get(zone) or list(ZONES.values())[0]
    tier = st["tier"] or 1
    PL.set_row(uid, expedition_until=0, expedition_zone=None, expedition_tier=0)
    PL.track_stat(uid, "expeditions", 1)
    PL.progress(uid, "exped", 1)
    fail = random.random() < config.EXPED_FAIL + 0.05 * z["danger"] - 0.04 * tier
    loot = loot_table(z, tier, fail)
    import division
    store = division.facility_of(uid, "storage")
    if store:
        loot["credits"] = round(loot["credits"] * (1 + 0.06 * store), 0)
    PL.add_res(uid, **loot)
    xp = round(random.uniform(10, 22) * (0.6 if fail else 1.0) * (1 + 0.25 * tier), 1)
    PL.add_xp(uid, xp)
    lines = ["🗺 <b>گزارش کاوش</b>", f"{z['name']} · سطح {tier}",
             "❌ <b>شکست</b> — تیم با آسیب بازگشت؛ غنیمت ناچیز." if fail
             else "✅ <b>بهبود</b>"]
    icon = dict(credits="🪙", cells="🔋", mats="🔩", dna="🧬", fdata="📡", cores="💎")
    lines.append(" · ".join(f"{icon[k]} {v:g}" for k, v in loot.items() if v))
    lines.append(f"✨ +{xp} XP")
    encounter = None
    chance = (0.14 if fail else 0.26) + 0.05 * z["danger"]
    if random.random() < chance:
        pool = [t for t in TN.TITANS.values() if zone_env(zone) in (t.get("env") or {})] or list(TN.TITANS.values())
        w = [1 / (1 + balance.titans_rarity_idx(t["rar"])) for t in pool]
        t = random.choices(pool, weights=w, k=1)[0]
        encounter = t["id"]
        lines += ["", f"🚨 <b>تماس با تایتان</b> — {t['emj']} {t['name']} روی خط کاوش تو قرار گرفته!"]
    return dict(ok=True, msg="\n".join(lines), fail=fail, loot=loot, encounter=encounter,
                auto_combat=bool(encounter))


def zone_env(zone: str) -> str:
    return (ZONES.get(zone) or {}).get("env", "ocean")


def resolve_due(uid: int) -> dict:
    """تیک بی‌صدا: اگر کاوش تمام شده باشد، نتیجه را آماده می‌کند (بدون پیام)."""
    st = status(uid)
    return dict(ready=bool(st.get("ready")), zone=st.get("zone"))
