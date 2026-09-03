# 🪙 Economy Engine — MC، منابع، فروشگاه، بازار، جایزه، بونتی (P2W ممنوع)
import random

import balance
import config
import db
import emoji as EMJ
import player as PL
from db import now

# ── منابع ──
RES = {
    "credits": dict(name="اعتبار مانارچ", emj="coin", icon="🪙", unit="اعتبار", sellable=False),
    "cores": dict(name="هسته تایتان", emj="core", icon="💎", unit="هستۀ تایتان", sellable=False),
    "dna": dict(name="قطعه ژنتیکی", emj="dna", icon="🧬", unit="قطعۀ ژنتیکی", sellable=True, base=90),
    "cells": dict(name="پیل انرژی", emj="cell", icon="🔋", unit="پیل انرژی", sellable=True, base=40),
    "mats": dict(name="ماده تایتان", emj="material", icon="🔩", unit="مادۀ تایتان", sellable=True, base=55),
    "fdata": dict(name="داده محرمانه", emj="data", icon="📡", unit="دادۀ محرمانه", sellable=True, base=120),
}

# ── تجهیزات (فقط با بازی به‌دست می‌آید؛ خرید مستقیم قدرت با پول = ممنوع) ──
ITEMS = {
    # rigs
    "rig_field": dict(name="جهاز صحرایی — ۱", emj="gear", kind="rig", tier=1, slot="rig",
                      mods=dict(hp=26, df=2.4, spd=0.8), cost=3400, need_rank=1,
                      desc="استخوان‌بندی میدانی مانارچ — اولین لایه‌ی بقا."),
    "rig_recon": dict(name="جهاز شناسایی — ۲", emj="radar", kind="rig", tier=2, slot="rig",
                      mods=dict(hp=52, df=4.2, spd=1.6, dodge=0.02, acc=0.02), cost=11000, need_rank=4,
                      desc="استتار راداری + حسگر لرزه‌ای."),
    "rig_heavy": dict(name="جهاز سنگر — ۳", emj="shield_doc", kind="rig", tier=3, slot="rig",
                      mods=dict(hp=110, df=9.0, regen=1.4, spd=-0.6), cost=34000, need_rank=8,
                      desc="زره بتنی؛ کند اما تایتان‌کُش."),
    "rig_alpha": dict(name="جهاز فرماندهی آلفا", emj="crown", kind="rig", tier=4, slot="rig",
                      mods=dict(hp=180, df=13.0, atk=6.0, regen=2.2, acc=0.04), cost=98000, need_rank=14,
                      desc="تنها سه نمونه ساخته شد؛ هرکدام یک پرونده‌ی زنده است."),
    # weapons
    "wp_harpoon": dict(name="نیزه‌انداز تایتان", emj="sword", kind="weapon", tier=1, slot="weapon",
                       mods=dict(atk=3.4, acc=0.015), cost=2600, need_rank=1,
                       desc="هارپون ضدتایتان؛ entry-level مونارش."),
    "wp_ion": dict(name="تکرارکننده یون", emj="spark", kind="weapon", tier=2, slot="weapon",
                    mods=dict(atk=7.2, crit=0.03, tags=["tech"]), cost=13000, need_rank=5,
                    desc="رگبار یونی — عليه تایتان‌های مکانیکی عالی."),
    "wp_seismic": dict(name="توپ لرزه‌ای", emj="heavy", kind="weapon", tier=3, slot="weapon",
                       mods=dict(atk=13.5, crit=0.02, tags=["sonic"], energy=10), cost=46000, need_rank=9,
                       desc="موج لرزه‌ای؛ نقطه‌ی ضعف بلورها و استخوان."),
    "wp_orca": dict(name="فرستنده تشدید اورکا", emj="signal", kind="weapon", tier=4, slot="weapon",
                    mods=dict(atk=21.0, acc=0.05, tags=["sonic", "psychic"], energy=26), cost=132000, need_rank=15,
                    desc="فرکانس آلفا؛ هم سلاح، هم فرمان."),
    # support modules
    "md_scanner": dict(name="اسکنر عمیق", emj="track", kind="module", tier=1, slot="module",
                       mods=dict(), cost=4200, need_rank=2, extra=dict(track=0.35),
                       desc="+۳۵٪ بازدهی ردیابی سیگنال."),
    "md_labkit": dict(name="کیت آزمایشگاه سیار", emj="research", kind="module", tier=2, slot="module",
                      mods=dict(), cost=14000, need_rank=6, extra=dict(lab_speed=0.25, lab_fail=-0.08),
                      desc="تحلیل سریع‌تر، شکست کمتر."),
    "md_medbay": dict(name="بست درمان نانو", emj="medkit", kind="module", tier=3, slot="module",
                      mods=dict(regen=2.2), cost=30000, need_rank=8, extra=dict(heal=0.25),
                      desc="ترمیم میدانی؛ مرده‌ها را زنده نگه می‌دارد."),
    "md_shieldgen": dict(name="تولیدکننده سپر اجیس", emj="guard", kind="module", tier=4, slot="module",
                         mods=dict(df=4.0), cost=72000, need_rank=12, extra=dict(shield=0.30),
                         desc="سپر انرژی: ۳۰٪ از آسیب گارد را می‌گیرد."),
    # consumables
    "cs_stim": dict(name="محرک تایتان", emj="cell", kind="consumable", cost=600,
                    use=dict(energy=45, resolve=6), desc="شارژ سریع عصبی."),
    "cs_medkit": dict(name="کیت کمک اولیه", emj="medkit", kind="consumable", cost=900,
                      use=dict(hp=90), desc="۹۰ جان، فوری."),
    "cs_antitoxin": dict(name="ضدخورندگی", emj="acid", kind="consumable", cost=700,
                         use=dict(clean=3), desc="پاک‌سازی وضعیت‌های منفی."),
    "cs_focus": dict(name="سرم تمرکز آلفا", emj="intel", kind="consumable", cost=2400,
                     use=dict(resolve=26, charge=25), desc="تمرکز و شارژ — برای شکارِ افسانه‌ای."),
    "cs_beacon": dict(name="منبع سیگنال", emj="signal", kind="consumable", cost=1800,
                      use=dict(research=45), desc="+۴۵ امتیاز پژوهش روی آخرین هدف."),
    "cs_core_shard": dict(name="قطعه هسته", emj="core", kind="material", cost=9000,
                          desc="خردهٔ هسته — برای ارتقای تایتان لازم است."),
}

ABILITY_ITEMS = {
    "emp_charge": dict(item="wp_ion", ability="emp_charge"),
    "concussion_grenade": dict(item="wp_harpoon", ability="concussion_grenade"),
    "orbital_laser": dict(item="rig_alpha", ability="orbital_laser"),
    "nanite_repair": dict(item="md_medbay", ability="nanite_repair"),
}

SLOTS = ("rig", "weapon", "module")

# برچسبِ فارسیِ مودها — کارتِ فروشگاه هیچ‌وقت `atk+7.2` چاپ نمی‌کند
MOD_FA = dict(hp="جان", df="سپر", atk="آسیب", spd="سرعت", acc="دقت", dodge="جاخالی",
              regen="بازیابی", crit="بحرانی", energy="انرژی", resolve="عزم")
TAG_FA = dict(tech="فناوری", sonic="صوتی", psychic="ذهنی", atomic="هسته‌ای", beast="وحشی",
              energy="انرژی", ancient="باستان", cryo="یخی", fire="آتشین", pollution="آلاینده",
              gravity="گرانشی", light="نوری")


def _num(v) -> str:
    f = float(v)
    return f"{abs(f):g}"


def mod_text(it: dict) -> str:
    """«آسیب +۷٫۲ · بحرانی +۰٫۰۳ · برچسب: فناوری»"""
    out = []
    for k, v in (it.get("mods") or {}).items():
        lab = MOD_FA.get(k)
        if k == "tags":
            if v:
                out.append("برچسب: " + "، ".join(TAG_FA.get(str(x), str(x)) for x in v))
            continue
        if lab is None or not isinstance(v, (int, float)):
            continue
        sign = "+" if float(v) >= 0 else "−"
        out.append(f"{lab} {sign}{_num(v)}")
    for k, v in (it.get("extra") or {}).items():
        lab = dict(track="ردیابی", lab_speed="سرعتِ آزمایشگاه", lab_fail="ریسکِ آزمایشگاه",
                   heal="ترمیم", shield="سپر").get(k)
        if lab and isinstance(v, (int, float)):
            out.append(f"{lab} {int(round(abs(float(v)) * 100))}٪")
    return " · ".join(out)


def catalog(kind: str = None) -> list:
    return [(k, v) for k, v in ITEMS.items() if not kind or v.get("kind") == kind]


def shop_page(p: dict, kind: str = None) -> list:
    out = []
    for iid, it in catalog(kind):
        if it.get("kind") == "material":
            continue
        locked = int(p.get("rank") or 1) < it.get("need_rank", 1)
        mark = "🔒" if locked else ""
        out.append((iid, f"{mark}{it['name']} · 🪙{int(it['cost'])}"))
    return out


def price_of(iid: str) -> float:
    return float(ITEMS.get(iid, {}).get("cost", 0))


def buy(uid: int, iid: str) -> dict:
    it = ITEMS.get(iid)
    if not it:
        return dict(ok=False, msg="❌ SYSTEM: کد آیتم نامعتبر است.")
    p = PL.get(uid)
    if not p:
        return dict(ok=False, msg="🔒 ابتدا /start.")
    if PL.is_dead(p):
        return dict(ok=False, msg="☠️ در حالت بازیابی خرید ممکن نیست.")
    if int(p.get("rank") or 1) < it.get("need_rank", 1):
        return dict(ok=False, msg=f"🔒 نیازمند رتبه‌ی {it['need_rank']} — سطحِ دسترسی مانارچ لازم است.")
    if PL.on_cd(uid, "shop"):
        return dict(ok=False, msg=f"⏳ {PL.cd_left(uid, 'shop')} ثانیه صبر.")
    cost = price_of(iid)
    if float(p.get("credits") or 0) < cost:
        return dict(ok=False, msg=f"🪙 کمبود اعتبار: {cost - float(p['credits']):,.0f} اعتبار لازم است.")
    if PL.on_cd(uid, "shop") is False:
        PL.set_cd(uid, "shop", config.CD_SHOP)
    PL.spend(uid, credits=-cost)
    PL.add_item(uid, iid, 1)
    db.db().feed("buy", f"{uid}:{iid}")
    return dict(ok=True, msg=(f"{E('coin')} <b>دریافت شد</b> — {it['name']}\n"
                              f"🪙 −{int(cost):,} اعتبار · «/equip {it.get('name') or iid}» برای مجهزکردن"))


def E(key):
    import emoji
    return emoji.get(key)


def sell(uid: int, res: str, qty: float) -> dict:
    meta = RES.get(res)
    if not meta or not meta.get("sellable"):
        return dict(ok=False, msg="🔒 این منبع در بازار مانارچ قابل‌فروش نیست (Core/اعتبار).")
    p = PL.get(uid)
    if not p or float(p.get(res) or 0) < qty or qty <= 0:
        return dict(ok=False, msg="📦 مقدار نامعتبر.")
    unit = market_price(res)
    total = unit * qty
    PL.spend(uid, **{res: -qty})
    PL.add_res(uid, credits=total)
    return dict(ok=True, msg=(f"🏷 <b>فروش ثبت شد</b>\n{meta['icon']} {qty:g} × {meta['name']} "
                              f"→ 🪙 <b>{total:,.0f} اعتبار</b> @ {unit:,.0f}"))


def market_seed() -> int:
    """نوسان بازار از تاریخ روز + شمارۀ روز → همه بازیکنان یک قیمت می‌بینند."""
    d = db.local_now().strftime("%Y%m%d")
    h = sum(ord(c) for c in d)
    return h


def market_price(res: str) -> float:
    meta = RES.get(res) or {}
    base = float(meta.get("base") or 0)
    if not base:
        return 0.0
    rnd = random.Random(market_seed() + hash(res) % 9973)
    wave = rnd.uniform(-1, 1) * config.SELL_SPREAD
    slot = int(now() // 600)                    # هر ۱۰ دقیقه یک قدم
    drift = random.Random(slot * 31 + int(base)).uniform(-0.05, 0.05)
    return round(base * (1 + wave + drift), 1)


def market_board() -> str:
    rows = []
    for k, m in RES.items():
        if not m.get("sellable"):
            continue
        pr = market_price(k)
        base = m["base"]
        arrow = "▲" if pr > base else "▼" if pr < base else "•"
        rows.append(f"{m['icon']} {m['name']} — <b>{pr:,.0f}</b> اعتبار {arrow}")
    return "\n".join(rows)


# ─────────── ارتقای تجهیزات (Salvage) ───────────
UPGRADE_BASE = dict(mats=4, cells=3, credits=1200)


def upgrade_cost(uid: int, iid: str) -> dict:
    it = ITEMS.get(iid) or {}
    lvl = PL.item_level(uid, iid)
    k = 1 + lvl
    return dict(mats=UPGRADE_BASE["mats"] * k, cells=UPGRADE_BASE["cells"] * k,
                credits=UPGRADE_BASE["credits"] * (k ** 1.6) * (1 + 0.3 * (it.get("tier", 1) - 1)),
                lvl=lvl, max=3)


def upgrade(uid: int, iid: str) -> dict:
    it = ITEMS.get(iid)
    if not it or it.get("kind") not in SLOTS:
        return dict(ok=False, msg="⚙️ فقط Rig/Sلاح/ماژول قابل ارتقاست.")
    p = PL.get(uid)
    c = upgrade_cost(uid, iid)
    if c["lvl"] >= c["max"]:
        return dict(ok=False, msg="⚙️ این تجهیز در بالاترین سطح مهندسی مانارچ است.")
    have = {k: float(p.get(k) or 0) for k in ("mats", "cells", "credits")}
    miss = [k for k, v in (("mats", c["mats"]), ("cells", c["cells"]), ("credits", c["credits"])) if have[k] < v]
    if miss:
        return dict(ok=False, msg="📦 کمبود: " + "، ".join(f"{RES[k]['name']}" for k in miss))
    PL.spend(uid, mats=-c["mats"], cells=-c["cells"], credits=-int(c["credits"]))
    PL.item_level(uid, iid, c["lvl"] + 1)
    return dict(ok=True, msg=f"⚙️ <b>ارتقا انجام شد</b> — {it['name']} MK+{c['lvl'] + 1}")


def gear_mods(uid: int) -> tuple:
    """جمع مودهای تجهیزات مجهز + سطح ارتقا (×۱۲٪ هر سطح)."""
    mods, extra, abilities = dict(), dict(), []
    rows = db.db().q("SELECT item_id, equipped FROM items WHERE user_id=? AND qty>0", (uid,))
    for r in rows:
        if not r["equipped"]:
            continue
        it = ITEMS.get(r["item_id"])
        if not it:
            continue
        lvl = 1 + 0.12 * PL.item_level(uid, r["item_id"])
        for k, v in (it.get("mods") or {}).items():
            if isinstance(v, bool):
                continue
            if isinstance(v, (int, float)):
                mods[k] = mods.get(k, 0) + v * lvl
            elif isinstance(v, (list, tuple)):
                cur = mods.setdefault(k, [])
                cur.extend(x for x in v if x not in cur)
        for k, v in (it.get("extra") or {}).items():
            extra[k] = extra.get(k, 0) + v
        for aid, meta in ABILITY_ITEMS.items():
            if meta["item"] == r["item_id"] and aid not in abilities:
                abilities.append(aid)
    return mods, extra, abilities


# ─────────── پروفیل تجهیزاتِ مرجع (برای کالیبراسیون تعادل) ───────────
def loadout_mods(rank: int) -> dict:
    """بهترین آیتمِ هر اسلات که در این رنک قابل‌دسترس است — مدها جمع می‌شوند.

    این تابع فقط برای «بازیکن مرجع»ِ balance استفاده می‌شود؛ پس واقع‌بینانه است:
    ماژول‌ها و آیتم‌های اکس را نمی‌شمارد و آیتم بعد از رنکِ لازم را هم نمی‌دهد.
    """
    rank = max(1, int(rank))
    out, best = {}, {}
    for it in ITEMS.values():
        if int(it.get("need_rank") or 1) > rank:
            continue
        kind = it.get("kind")
        if kind not in ("rig", "weapon", "module"):
            continue
        score = (int(it.get("tier") or 1), float(it.get("cost") or 0))
        slot = kind if kind != "module" else "module"
        if kind == "module":
            key = f"module{len([1 for k in best if k.startswith('module')]) % 2}"
        else:
            key = kind
        if key not in best or score > best[key][0]:
            best[key] = (score, it)
    for _k, (_s, it) in best.items():
        for m, v in (it.get("mods") or {}).items():
            if isinstance(v, (int, float)):
                out[m] = out.get(m, 0) + v
    return out


balance.register_gear_provider(loadout_mods)


def stats_of(p: dict) -> dict:
    """بلاک نهایی بازیکن برای موتور نبرد."""
    mods, extra, abilities = gear_mods(p["user_id"])
    bonds = __import__("research").bond_bonuses(p["user_id"])
    mods = dict(mods)
    mods["abilities"] = abilities
    b = balance.player_block(p, mods, bonds)
    b["extra"] = extra
    b["gear_abilities"] = abilities
    return b


def bounty_place(uid: int, target: int, amount: float) -> dict:
    if uid == target:
        return dict(ok=False, msg="🎯 جایزه روی سر خودت؟ مانارچ این را ثبت می‌کند.")
    if amount < config.BOUNTY_MIN:
        return dict(ok=False, msg=f"🎯 کمینۀ جایزه {config.BOUNTY_MIN} اعتبار.")
    p = PL.get(uid)
    if not p or float(p.get("credits") or 0) < amount:
        return dict(ok=False, msg="🪙 اعتبار کافی نیست.")
    if not PL.get(target):
        return dict(ok=False, msg="📁 آن بازیکن در پرونده‌ی مانارچ نیست.")
    PL.spend(uid, credits=-amount)
    b = db.db().getv("bounties", {}) or {}
    b[str(target)] = round(float(b.get(str(target), 0)) + amount, 0)
    db.db().setv("bounties", b)
    return dict(ok=True, msg=f"🎯 <b>جایزه ثبت شد</b> — {amount:,.0f} اعتبار روی سر {PL.name_of(target)}")


def bounty_of(uid: int) -> float:
    return float((db.db().getv("bounties", {}) or {}).get(str(uid), 0))


def bounty_collect(killer: int, victim: int) -> float:
    b = db.db().getv("bounties", {}) or {}
    amt = float(b.pop(str(victim), 0) or 0)
    if amt:
        db.db().setv("bounties", b)
        PL.add_res(killer, credits=amt)
    return amt


# ─────────── مأموریت روزانه ───────────
MISSIONS = {
    "track": dict(name="ردیابی ۳ سیگنال", emj="track", key="track", need=3,
                  rw=dict(credits=700, xp=18, fdata=1)),
    "sample": dict(name="۲ نمونه‌برداری میدانی", emj="dna", key="sample", need=2,
                    rw=dict(credits=800, xp=22, dna=2)),
    "hunt": dict(name="شکار ۱ تایتان", emj="sword", key="hunt_win", need=1,
                 rw=dict(credits=1400, xp=30, cells=2)),
    "boss": dict(name="شرکت در ۱ نبرد باس", emj="boss", key="boss_join", need=1,
                 rw=dict(credits=1000, xp=24, mats=3)),
    "guard": dict(name="۸ گارد موفق در نبرد", emj="guard", key="guard", need=8,
                  rw=dict(credits=600, xp=14, cells=1)),
    "research": dict(name="۱ سیکل آزمایشگاه", emj="research", key="lab", need=1,
                     rw=dict(credits=1200, xp=26, fdata=2)),
    "raid": dict(name="۱۰ ضربه در رید جهانی", emj="breach", key="raid_strike", need=10,
                 rw=dict(credits=1500, xp=34, cores=1)),
    "expedition": dict(name="تکمیل ۱ کاوش", emj="mission", key="exped", need=1,
                       rw=dict(credits=900, xp=20, mats=2)),
    "puzzle": dict(name="حل ۱ رمزنگاری مانارچ", emj="binary", key="puzzle", need=1,
                   rw=dict(credits=650, xp=16, dna=1)),
}


def roll_missions(uid: int) -> list:
    today = db.local_day()
    p = PL.get(uid) or {}
    cur = p.get("day")
    if cur == today and (p.get("missions") or "{}") != "{}":
        return list((db.jload(p.get("missions"), {}) or {}).keys())
    rnd = random.Random(int(uid) * 7919 + int(today.replace("-", "")))
    pool = list(MISSIONS.keys())
    rnd.shuffle(pool)
    picks = pool[:config.DAILY_MISSIONS]
    st = {k: dict(prog=0, done=False, got=False) for k in picks}
    PL.set_row(uid, day=today, missions=db.jdump(st))
    return picks


def progress(uid: int, key: str, amount: float = 1) -> list:
    """پیشرفت مأموریت‌ها؛ لیست جوایز تکمیل‌شده را برمی‌گرداند."""
    roll_missions(uid)
    p = PL.get(uid) or {}
    st = db.jload(p.get("missions"), {}) or {}
    done = []
    for mid, row in st.items():
        m = MISSIONS.get(mid)
        if not m or row.get("done") or m["key"] != key:
            continue
        row["prog"] = min(m["need"], float(row.get("prog", 0)) + amount)
        if row["prog"] >= m["need"]:
            row["done"] = True
            done.append(mid)
    PL.set_row(uid, missions=db.jdump(st))
    return done


def claim_mission(uid: int, mid: str) -> dict:
    p = PL.get(uid) or {}
    st = db.jload(p.get("missions"), {}) or {}
    row = st.get(mid)
    if not row or not row.get("done") or row.get("got"):
        return dict(ok=False, msg="🗒 این مأموریت هنوز آماده‌ی تحویل نیست.")
    row["got"] = True
    PL.set_row(uid, missions=db.jdump(st))
    rw = dict(MISSIONS[mid]["rw"])
    PL.add_res(uid, credits=rw.get("credits", 0), dna=rw.get("dna", 0), cells=rw.get("cells", 0),
               mats=rw.get("mats", 0), fdata=rw.get("fdata", 0), cores=rw.get("cores", 0))
    if rw.get("xp"):
        PL.add_xp(uid, rw["xp"])
    txt = " · ".join(f"{'🪙' if k == 'credits' else '✨' if k == 'xp' else RES.get(k, {}).get('icon', '📦')}{v:g}"
                     for k, v in rw.items())
    return dict(ok=True, msg=f"🎁 <b>مأموریت انجام شد</b> — {MISSIONS[mid]['name']}\n{txt}")


def mission_board(uid: int) -> str:
    roll_missions(uid)
    p = PL.get(uid) or {}
    st = db.jload(p.get("missions"), {}) or {}
    if not st:
        return "🗒 هیچ مأموریتی فعال نیست."
    lines = []
    for mid, row in st.items():
        m = MISSIONS.get(mid) or {}
        flag = "✅" if row.get("got") else ("🎁" if row.get("done") else f"{row.get('prog', 0):g}/{m.get('need')}")
        lines.append(f"{m.get('emj', '🗒')} {m.get('name', mid)} — {flag}")
    return "\n".join(lines)


def checkin(uid: int) -> dict:
    today = db.local_day()
    p = PL.get(uid) or {}
    if p.get("last_seen_day") == today:
        return dict(ok=False, msg=f"⏳ حضور امروز ثبت شد — {config.CHECKIN[min(6, int(p.get('streak') or 1) - 1)]} اعتبار گرفتی.")
    st = int(p.get("streak") or 0)
    yest = (db.local_now() - __import__("datetime").timedelta(days=1)).strftime("%Y-%m-%d")
    st = st + 1 if p.get("last_seen_day") == yest else 1
    st = min(st, 7)
    mc = config.CHECKIN[min(6, st - 1)]
    PL.set_row(uid, streak=st, last_seen_day=today, checkin=int(p.get("checkin") or 0) + 1)
    PL.add_res(uid, credits=mc)
    xp = config.CHECKIN_XP
    PL.add_xp(uid, xp)
    return dict(ok=True, msg=f"📅 <b>ورود روزانه ثبت شد</b> — روز {st}\n🪙 +{mc} اعتبار · ✨ +{xp} تجربه")


def refund(uid: int, what: str, amount: float) -> dict:
    PL.add_res(uid, **{what: amount})
    return dict(ok=True, msg=f"↩️ {RES.get(what, {}).get('icon', '📦')} +{amount:g} جبران شد.")


# ─────────── ایموجی‌ها از Registry (کلید → نماد) ───────────
for _it in ITEMS.values():
    _it["emj"] = EMJ.of(_it.get("emj"), "⚙️")
for _m in MISSIONS.values():
    _m["emj"] = EMJ.of(_m.get("emj"), "🗒")
