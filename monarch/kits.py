# 🧬 Kit Synthesizer — ساخت خودکار کیت‌های تعریف‌نشده از روی الگوی رفتاری
"""titans.py هر تایتان را با نام canon و شناسه‌ی Ability/Ultimate/Passive تعریف
می‌کند. قرار داد طراحی: **۱ Passive + ۲ تا ۴ Ability + ۱ Ultimate**.

این ماژول هر شناسه‌ای را که تایتان‌ها ارجاع داده‌اند اما در abilities.py تعریف
نشده، از روی «معنای نامش» می‌سازد؛ پس افزودن تایتانِ تازه فقط یک خط در
titans.py است، نه شش تعریف دستی.

سقف‌های تعادل (تضمین «Auto-Win ممنوع»):
  • Ability: انرژی ۱۶–۳۸ · Cooldown ۲–۵ · توان ≤ ۱٫۴۵
  • Ultimate: انرژی ≥ ۴۴ · Cooldown ≥ ۳ · شرط فعال‌سازی (شارژ ≥ ۷۸ یا HP کم)
  • وضعیت‌ها همگی موقتی‌اند؛ هیچ الگویی قفلِ دائمی یا آسیبِ یک‌باره‌ی کشنده نمی‌سازد.

پوششِ دستی (بدون دست‌زدن به کد): monarch/data/kits.json
    {"ability_id": {"power": 1.2, "eff": {"stun": 2}, "desc": "..."}}
"""
import json
import os
import re

OVERLAY = os.path.join(os.path.dirname(__file__), "data", "kits.json")

ULT_COST_MIN, ULT_CD_MIN, ULT_CHARGE = 44, 3, 78
AB_COST = {0: 16, 1: 20, 2: 24, 3: 28, 4: 32, 5: 38}

# ── الگوها: (regexِ نام، برچسب، توان، افکت، توضیح) — نخستین انطباقِ نزدیک‌تر برنده ──
PATTERNS = [
    (r"atomic|nuclear|radiat|fission|radio", "atomic", 1.26, dict(dmg=1.0, burn=2, mark=1),
     "فشار هسته‌ای: آسیب سنگین + نشانه‌گذاری برای ضربات بعدی."),
    (r"cryo|frost|ice|freeze|glacier|winter|cold|shatter_ice", "ice", 1.10,
     dict(dmg=0.9, freeze=2, slow=2), "انجماد موضعی؛ جاخالی و سرعت حریف را می‌بندد."),
    (r"emp|jam|scramble|static|interfer|sensor|disrupt|tesla|volt|electric|spark|thunder|storm",
     "electric", 1.12, dict(dmg=0.95, stun=1, blind=1),
     "تخلیه‌ی بار الکتریکی؛ یک نوبت فلج و کوری سنسور."),
    (r"acid|corros|venom|toxic|poison|spit|slime|regurgit|dissolv", "acid", 1.06,
     dict(dmg=0.85, acid=3, dfdown=0.10), "خورندگی: دفاع حریف را در چند نوبت می‌خورد."),
    (r"fire|flame|ember|magma|lava|pyro|burn|scorch|inferno|burn_", "fire", 1.16,
     dict(dmg=0.98, burn=3), "آتشِ ادامه‌دار؛ منطقه را داغ و نفس‌کش می‌کند."),
    (r"breath|beam|ray|laser|pulse|burst|detonat|cannon|blast|discharge|project",
     "energy", 1.20, dict(dmg=1.0, burn=2), "آسیب مستقیمِ متمرکز؛ هسته‌ی انرژی را داغ می‌کند."),
    (r"claw|rake|slash|rend|snag|fang|bite|jaw|tear|maul|scratch|shred", "brute", 1.05,
     dict(dmg=1.0, bleed=2), "پارگی فیزیکی + خونریزی."),
    (r"tail|whip|swing|sweep|flail|lash|cyclone|tornado|gale|vortex|whirlwind",
     "wind", 1.06, dict(dmg=0.95, knock=14, spd_down=0.10),
     "جاروی چرخشی؛ حریف را از تعادل می‌اندازد."),
    (r"kick|stomp|slam|punch|fist|elbow|hoof|trample|boot|hammer|ax|axe|mace",
     "brute", 1.14, dict(dmg=1.05, stun=1, knock=14), "ضربه‌ی سنگینِ فرود؛ یک نوبت تعلیق."),
    (r"ram|charge_up|dash|rush|gore|tusk|horn|spike|lance|bolter|thrust", "kinetic", 1.08,
     dict(dmg=1.0, knock=12), "حمله‌ی ورودی با سرعت؛ فاصله را با آسیب می‌بندد."),
    (r"burrow|dig|tunnel|subterranean|underground|sink|trip|quake|tremor|seismic",
     "ground", 0.98, dict(dmg=0.9, stun=1, spd_down=0.10),
     "از زیرِ زمین بیرون می‌زند و تعادل را می‌گیرد."),
    (r"constrict|strangle|squeeze|press|wrestle|crush_hold|coil", "brute", 1.12,
     dict(dmg=1.02, bleed=2, spd_down=0.16), "گیرِ تن‌به‌تن؛ فرار و جاخالی را سخت می‌کند."),
    (r"web|net|wrap|snare|trap|cord|chain|anchor|pull|tow|grab|hold|tow_", "control", 0.86,
     dict(dmg=0.55, stun=2, acc_down=0.10), "گیر انداختن: قفل حرکت + کاهش دقت."),
    (r"roar|scream|shriek|cry_|howl|bellow|chant|chorus|song|resonan|shroud|silence|gaze|stare|hypno|mind|sonic|siren",
     "psychic", 0.90, dict(dmg=0.42, fear=2, acc_down=0.14, blind=1),
     "فشار صوتی/روانی: دقت و تمرکز حریف را می‌شکند."),
    (r"swarm|brood|eggs|larvae|colony|nest|horde|locust|flurry", "swarm", 1.0,
     dict(dmg=0.72, hits=3, bleed=1), "سه برخورد کوتاه؛ هر ضربه جدا حساب می‌شود."),
    (r"camouf|invis|phantom|shadow|vanish|ghost|blur|evasion|stealth", "trick", 0.6,
     dict(dmg=0.2, dodge_up=0.12, stealth=1), "ناپدید شدن کوتاه؛ جاخالی را بالا می‌برد."),
    (r"shield|aegis|barrier|ward|guard|plate|carapace|shell|armor|armour|bulwark|wall|defense|defend",
     "defense", 0.0, dict(dmg=0.0, shield=0.5, df_up=0.18), "سپرِ فعال: جذب آسیب + افزایش دفاع."),
    (r"reflect|mirror|prism|crystal|refract", "crystal", 0.28,
     dict(dmg=0.3, shield=0.35, reflect=0.3), "بازتاب بخشی از آسیب + پوسته‌ی بلوری."),
    (r"regen|regenerat|mend|heal|repair|recover|bloom|molt| moult|molting|growth|restor|vital",
     "vital", 0.0, dict(dmg=0.0, heal=0.09, regen_up=1.4), "بافت‌سازی؛ بازیابی تدریجی HP."),
    (r"siphon|drain|devour|consume|feed|leech|parasit", "drain", 1.02,
     dict(dmg=0.95, heal=0.35), "آسیب و بازیابی هم‌زمان از بدن حریف."),
    (r"speed|accel|overclock|agility|swift|flight|aerial|dive|glide|soar|wing|sky", "wind", 1.06,
     dict(dmg=0.9, spd_up=0.9, dodge_up=0.06), "افزایش سرعت حرکت و جاخالی برای چند نوبت."),
    (r"rage|fury|berserk|adrenal|rampag|wrath|fero|instinct|blood", "brute", 1.18,
     dict(dmg=1.06, atk_up=0.16, bleed_self=0.02), "خشم: آسیب بیشتر به بهای ثبات."),
    (r"power|amp|boost|surge|focus|concentrat|aim|target|lock|mark", "tech", 0.74,
     dict(dmg=0.5, atk_up=0.14, acc_up=0.10), "آماده‌سازی هدف: دقت و آسیب ضربات بعدی بالا می‌رود."),
    (r"meteor|asteroid|orbit|space|cosmic|gravity|black_hole|void|star|planet", "cosmic", 1.30,
     dict(dmg=1.15, stun=1, env_lock=1), "فشارِ آسمانی؛ آسیب بزرگ با ریسک محیطی."),
    (r"tidal|wave|ocean|whirl|rip|current|tsunami|depth|abyss|marc|sea", "water", 1.09,
     dict(dmg=1.0, slow=2, knock=8), "موجِ فشاری؛ تعادل حریف را در هم می‌شکند."),
]

FALLBACK = ("kinetic", 1.0, dict(dmg=0.92), "ضربه‌ی ثبت‌شده در پرونده‌ی مانارچ.")

EMJ_BY_TAG = {
    "atomic": "atom", "ice": "ice", "electric": "spark", "acid": "acid", "fire": "flame",
    "energy": "beam", "brute": "fist", "wind": "wind", "kinetic": "sword", "ground": "quake",
    "control": "web", "psychic": "mind", "swarm": "swarm", "trick": "smoke",
    "defense": "shield", "crystal": "gem", "vital": "leaf", "drain": "fang", "tech": "chip",
    "cosmic": "star", "water": "wave",
}

PASSIVE_TEMPLATES = {
    "brute": dict(name="Armoured Hide", mods=dict(df=0.08, hp=0.04), desc="پوست ضخیم: آسیب فیزیکی کم‌تر."),
    "atomic": dict(name="Reactor Core", mods=dict(eng=0.10, atk=0.05), desc="هسته‌ی خودشارژ: شارژ سریع‌تر."),
    "psychic": dict(name="Hyper-Instinct", mods=dict(dodge=0.03, acc=0.03), desc="پیش‌بینی حرکت حریف."),
    "water": dict(name="Deep Pressure", mods=dict(hp=0.06, df=0.04), desc="فشار آب؛ بدن فشرده و مقاوم."),
    "ground": dict(name="Landbound Endurance", mods=dict(hp=0.06, regen=0.6), desc="استقامتِ زمین."),
    "wind": dict(name="Aerodynamic Frame", mods=dict(spd=0.10, dodge=0.02), desc="سبک و سریع در آسمان."),
    "ice": dict(name="Cryo Tolerance", mods=dict(res=0.06, hp=0.03), desc="مقاومت در برودت."),
    "acid": dict(name="Corrosive Blood", mods=dict(atk=0.04, bleed=0.02), desc="خونِ اسیدی؛ مهاجم می‌سوزد."),
    "fire": dict(name="Thermal Core", mods=dict(atk=0.05, res=0.04), desc="گرمای درونی؛ آسیب آتش بیشتر."),
    "tech": dict(name="Sensor Array", mods=dict(acc=0.04, dodge=0.02), desc="قفلِ هدف الکترونیکی."),
    "cosmic": dict(name="Extraterrestrial Physiology", mods=dict(res=0.07, eng=0.06), desc="بدنِ بیگانه با بازیابی سریع."),
    "crystal": dict(name="Lattice Structure", mods=dict(df=0.07, res=0.04), desc="ساختار بلوری ضربه‌گیر."),
    "swarm": dict(name="Pack Memory", mods=dict(spd=0.05, acc=0.03), desc="الگوی شکارِ گروهی."),
    "defense": dict(name="Fortified Carapace", mods=dict(df=0.10), desc="سپر طبیعی؛ کاهش آسیب."),
    "vital": dict(name="Rapid Cell Growth", mods=dict(regen=1.1, hp=0.04), desc="بافت‌سازی پایدار."),
    "drain": dict(name="Parasitic Feeding", mods=dict(regen=0.7, atk=0.03), desc="تغذیه از میزبان."),
    "trick": dict(name="Ambush Pattern", mods=dict(dodge=0.04, crit=0.02), desc="حمله از نقطه‌ی کور."),
    "control": dict(name="Constriction Grip", mods=dict(atk=0.03, df=0.03), desc="گیرنده؛ فرار سخت."),
}


def title_of(aid: str) -> str:
    words = [w for w in re.split(r"[_\-]+", aid or "") if w]
    out = []
    for w in words:
        lw = w.lower()
        if lw in ("mk", "ii", "iii", "iv", "x", "v", "omega", "alpha"):
            out.append(lw.upper())
        else:
            out.append(lw.capitalize())
    return " ".join(out) or "Titan Strike"


def match(aid: str) -> tuple:
    """الگوی مناسبِ یک شناسه: نزدیک‌ترین انطباقِ از ابتدای نام."""
    low = f"_{(aid or '').lower()}_"
    best = None
    for pat, tag, power, eff, desc in PATTERNS:
        m = re.search(pat, low)
        if not m:
            continue
        pos = m.start()
        if best is None or pos < best[0]:
            best = (pos, tag, power, eff, desc)
    if best:
        return best[1], best[2], best[3], best[4]
    return FALLBACK


def build(aid: str, t: dict = None, is_ult: bool = False) -> dict:
    tag, power, eff, desc = match(aid)
    idx = int((t or {}).get("_ridx") or 0)
    eff = dict(eff)
    req = {}
    if is_ult:
        cost = float(ULT_COST_MIN + 4 * idx)
        cd = int(ULT_CD_MIN + (1 if idx >= 3 else 0))
        power = round(1.55 + 0.13 * idx, 2)
        req = dict(charge=ULT_CHARGE + 4 * idx)
        if "shield" in eff or "heal" in eff:
            req["hp_below"] = 0.55
            desc += " فقط وقتی وضعیت قرمز است."
        eff["dmg"] = round(float(eff.get("dmg") or 0.0) + 0.55, 2)
        desc = "👑 " + desc
    else:
        cost = float(AB_COST.get(idx, 20) + (4 if tag in ("cosmic", "atomic", "energy") else 0))
        cd = int(2 + (1 if idx >= 3 else 0) + (2 if power >= 1.2 else 0))
        power = round(power * (1 + 0.03 * idx), 2)
    return dict(id=aid, name=title_of(aid), emj=EMJ_BY_TAG.get(tag, "ability"), cost=cost,
                cd=cd, power=power, req=req, eff=eff, tag=tag,
                desc=f"{desc} · پرونده‌ی {(t or {}).get('name', 'مانارچ')}")


def build_passive(pid: str, t: dict = None) -> dict:
    tag, _p, _e, _d = match(pid)
    tpl = PASSIVE_TEMPLATES.get(tag) or PASSIVE_TEMPLATES["brute"]
    return dict(id=pid, name=tpl["name"], emj="file", desc=tpl["desc"], mods=dict(tpl["mods"]))


def overlay(path: str = None) -> dict:
    """پوششِ دستی از data/kits.json (قابل‌به‌روزرسانی بدون تغییر کد)."""
    p = path or OVERLAY
    if not os.path.exists(p):
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            blob = json.load(f)
        return blob if isinstance(blob, dict) else {}
    except Exception:
        return {}


def synthesize(ABILITIES: dict, PASSIVES: dict, TITANS: dict) -> dict:
    """ثبت هر Ability/Ultimate/Passive ارجاع‌داده‌شده و تعریف‌نشده.

    ABILITIES/PASSIVES را در جا (in-place) پر می‌کند و شمارش برگردانی
    تا تست‌ها و لاگ استارت بتوانند بررسی کنند.
    """
    rar = None
    try:
        import titans as _T
        rar = getattr(_T, "RARITY", {})
    except Exception:
        pass
    missing_ab, missing_ult, missing_pa = set(), set(), set()
    owner = {}
    for t in TITANS.values():
        t["_ridx"] = int((rar or {}).get(t.get("rar", "RARE"), {}).get("idx", 1))
        for aid in (t.get("ab") or []):
            if aid not in ABILITIES:
                missing_ab.add(aid)
                owner.setdefault(aid, t)
        if t.get("ult") and t["ult"] not in ABILITIES:
            missing_ult.add(t["ult"])
            owner.setdefault(t["ult"], t)
        if t.get("pas") and t["pas"] not in PASSIVES:
            missing_pa.add(t["pas"])
            owner.setdefault(t["pas"], t)
    ov = overlay()
    for aid in sorted(missing_ab):
        ABILITIES[aid] = {**build(aid, owner.get(aid), False), **(ov.get(aid) or {})}
    for aid in sorted(missing_ult):
        ABILITIES[aid] = {**build(aid, owner.get(aid), True), **(ov.get(aid) or {})}
    for pid in sorted(missing_pa):
        PASSIVES[pid] = {**build_passive(pid, owner.get(pid)), **(ov.get(pid) or {})}
    # ── اعمالِ قرارداد اولتیمیت روی تعریف‌های ازپیش‌نوشته‌شده هم (سقف: هیچ «دکمه‌ی جادویی») ──
    for aid in sorted({t["ult"] for t in TITANS.values() if t.get("ult")}):
        a = ABILITIES.get(aid)
        if not a:
            continue
        idx = int((owner.get(aid) or {}).get("_ridx") or 0)
        if float(a.get("cost") or 0) < ULT_COST_MIN:
            a["cost"] = float(ULT_COST_MIN + 4 * idx)
        if int(a.get("cd") or 0) < ULT_CD_MIN:
            a["cd"] = int(ULT_CD_MIN + (1 if idx >= 3 else 0))
        req = a.setdefault("req", {})
        if not req.get("charge"):
            req["charge"] = ULT_CHARGE + 4 * idx
    # پوشش دستی برای تعریف‌های موجود هم کار می‌کند
    for aid, patch in ov.items():
        if aid in ABILITIES and aid not in (missing_ab | missing_ult):
            ABILITIES[aid].update(patch)
    return dict(made_abilities=len(missing_ab), made_ultimates=len(missing_ult),
                made_passives=len(missing_pa), overrides=len(ov))
