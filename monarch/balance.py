# ⚖️ Balance Engine — تنها خانه‌ی فرمول‌ها (Auto-Win ممنوع، اسپم‌برد ممنوع)
import hashlib
import json
import os
import random

import config
import titans as TN
from abilities import ABILITIES, PASSIVES

NORMALIZE = 34.0          # مقیاس: آمار تایتان ÷ NORMALIZE ≈ واحد بازیکن
RARITY_FLOOR = {"RECON": 0.55, "RARE": 0.68, "ELITE": 0.80,
                "ALPHA": 0.92, "LEGENDARY": 1.00, "OMEGA": 1.10}
RARITY_IDX = {"RECON": 0, "RARE": 1, "ELITE": 2, "ALPHA": 3, "LEGENDARY": 4, "OMEGA": 5}

TAGS = ("atomic", "brute", "storm", "light", "fire", "tech", "oxygen", "crystal",
        "sonic", "venom", "gravity", "psychic", "burrow", "aquatic", "volcanic",
        "flight", "silk", "ice", "mech", "acid", "void", "dark", "plant", "blade",
        "electric", "energy", "solar", "kinetic")

# جدول حلقه‌ی ضعف — همین جدول است که «مهارت» را بر «شهرت» پیروز می‌کند
COUNTERS = {
    "sonic": ("brute", "crystal", "plant", "tech"),
    "light": ("dark", "void", "acid", "storm"),
    "fire": ("plant", "ice", "silk", "acid"),
    "ice": ("fire", "aquatic", "volcanic", "flight"),
    "electric": ("tech", "mech", "aquatic", "crystal"),
    "gravity": ("flight", "tech", "brute", "atomic"),
    "acid": ("mech", "tech", "brute", "guard"),
    "oxygen": ("atomic", "crystal", "plant", "void"),
    "atomic": ("brute", "void", "storm", "mech"),
    "tech": ("sonic", "acid", "gravity", "plant"),
    "psychic": ("void", "storm", "brute", "mech"),
    "blade": ("silk", "plant", "aquatic", "tech"),
    "burrow": ("flight", "storm", "tech", "crystal"),
    "kinetic": ("crystal", "silk", "burrow", "flight"),
}


def titans_rarity_idx(rar: str) -> int:
    return RARITY_IDX.get(rar, 1)


def norm(v: float) -> float:
    return round(float(v) / NORMALIZE, 2)


# ─────────── وضعیت‌ها ───────────
STATUS_META = {
    "burn": dict(emj="🔥", name="سوختگی", desc="آسیب ادامه‌دار هر نوبت"),
    "acid": dict(emj="🧪", name="فرسودگی", desc="خوردگی + کاهش دفاع"),
    "bleed": dict(emj="🩸", name="خونریزی", desc="آسیب ادامه‌دار"),
    "stun": dict(emj="💫", name="فلج", desc="نوبت از دست رفته"),
    "freeze": dict(emj="🧊", name="انجماد", desc="قفل حرکت"),
    "slow": dict(emj="🐌", name="کندی", desc="−۴۵٪ جاخالی"),
    "blind": dict(emj="🌫", name="کورشدن", desc="−۲۰٪ دقت"),
    "guard": dict(emj="🛡", name="گارد", desc="−۵۵٪ آسیب این نوبت"),
    "rally": dict(emj="📣", name="رالی", desc="+۱۸٪ آسیب"),
    "atkdown": dict(emj="📉", name="فرسایش حمله", desc="−۱۸٪ آسیب"),
    "defup": dict(emj="🧱", name="پیش‌سنگر", desc="+۲۵٪ دفاع مؤثر"),
    "defdown": dict(emj="🏗", name="شرار", desc="−۲۸٪ دفاع"),
    "accup": dict(emj="🎯", name="قفل هدف", desc="+دقت و +کریت"),
    "mark": dict(emj="👁", name="نشان‌شده", desc="+دقت و +کریت برای شکارچی"),
    "drain": dict(emj="🔋", name="تخلیه", desc="کاهش انرژی هر نوبت"),
    "focus": dict(emj="🧿", name="تمرکز", desc="+۳۵٪ آسیب، جاخالی حریف −۴۰٪"),
}


def has(unit: dict, status: str) -> bool:
    for s in unit.get("statuses") or []:
        if s[0] == status:
            return True
    return False


def status_turns(unit: dict, status: str) -> int:
    for s in unit.get("statuses") or []:
        if s[0] == status:
            return s[1]
    return 0


def add_status(unit: dict, sid: str, turns: int, val: float = 0.0) -> bool:
    if turns <= 0 or sid not in STATUS_META:
        return False
    if unit.get("_raw") and immunity(unit, sid):
        return False
    for s in unit.setdefault("statuses", []):
        if s[0] == sid:
            s[1] = max(s[1], turns)
            s[2] = max(s[2], round(val, 2))
            return True
    unit["statuses"].append([sid, turns, round(val, 2)])
    return True


def clear_statuses(unit: dict, n: int = 99) -> int:
    bad = ("burn", "acid", "bleed", "slow", "blind", "stun", "freeze", "atkdown", "mark", "drain", "defdown")
    sts = unit.get("statuses") or []
    keep, removed = [], 0
    for s in sts:
        if s[0] in bad and removed < n:
            removed += 1
            continue
        keep.append(s)
    unit["statuses"] = keep
    return removed


def tick_statuses(unit: dict) -> list:
    """پایان نوبت: آسیب ادامه‌دار + شمارش معکوس."""
    events = []
    if not unit.get("statuses"):
        return events
    keep = []
    for sid, turns, val in unit["statuses"]:
        if sid in ("burn", "acid", "bleed") and val:
            unit["hp"] = round(float(unit["hp"]) - val, 2)
            events.append(f"{STATUS_META[sid]['emj']} {STATUS_META[sid]['name']} −{val:.1f}")
        elif sid == "drain" and val:
            unit["energy"] = max(0.0, float(unit.get("energy") or 0) - val)
            events.append(f"🔋 تخلیه −{val:.0f}")
        if sid == "defdown" and val:
            unit["df"] = round(max(0.0, float(unit.get("df") or 0) - val), 2)
        turns -= 1
        if turns > 0:
            keep.append([sid, turns, val])
    unit["statuses"] = keep
    return events


def passive_mods(unit: dict) -> dict:
    if not unit or not unit.get("pas"):
        return {}
    pas = PASSIVES.get(unit["pas"])
    return dict(pas.get("mods") or {}) if pas else {}


def immunity(unit: dict, tag: str) -> bool:
    mods = passive_mods(unit)
    return tag in set((mods.get("immune") or "").split("|"))


# ─────────── تطابق عنصری / محیط ───────────
def matchup(atk_tags, target) -> tuple:
    t = TN.get(target) if isinstance(target, str) else target
    if not t:
        return 1.0, ""
    mult, note = 1.0, ""
    weak = set(t.get("weak") or [])
    resist = set(t.get("resist") or [])
    for tag in atk_tags or []:
        if tag in weak:
            mult *= config.WEAK_BONUS
            note = f"⤷ {tag} ← نقطه‌ی ضعف"
        elif tag in resist:
            mult *= 0.72
            note = f"⤷ {tag} بی‌اثر شد"
        elif weak & set(COUNTERS.get(tag, ())):
            mult *= 1.12
            note = f"⤷ {tag} حلقه‌ی ضعف را فعال کرد"
    return round(mult, 3), note


def env_factor(t: dict, env: str) -> tuple:
    if not t or not env:
        return 1.0, ""
    home = (t.get("env") or {}).get(env, 0)
    mods = passive_mods(t) if t.get("pas") else {}
    bonus = mods.get("home_bonus", 0.0) if mods else 0.0
    if home:
        f = home + bonus
        return round(f, 3), f"🌍 {TN.ENVS.get(env, env)} ×{f:.2f}"
    if mods.get("no_env_pen"):
        return 1.0, ""
    if env in ("space", "antarctica", "nuclear", "hollow") and t.get("rar") in ("RECON", "RARE"):
        return config.ENV_AWAY, f"🌍 {TN.ENVS.get(env, env)} نامناسب ×{config.ENV_AWAY}"
    return 1.0, ""


# ─────────── فرمول central ضربه ───────────
def crit_expect(att: dict) -> float:
    return 1 + (config.CRIT_BASE + float(att.get("crit_bonus") or 0)) * (config.CRIT_MULT - 1)


def def_reduce(df: float) -> float:
    df = max(0.0, float(df or 0))
    return 1 - df / (df + config.DEF_K)


reduce_by_def = def_reduce


def resolve_strike(att: dict, dfd: dict, *, mult: float = 1.0, ability: dict = None,
                   is_counter: bool = False, ignore_guard: bool = False,
                   env: str = None, forced_hit: bool = False) -> dict:
    """یک ضربه؛ دقیقاً همان تابعی که در موتور نبرد اجرا می‌شود (تست‌ها همین را می‌زنند)."""
    out = dict(dmg=0.0, crit=False, dodged=False, missed=False, blocked=False, notes=[])
    raw = dfd.get("_raw")

    dodge = float(dfd.get("dodge") or 0)
    if has(dfd, "slow"):
        dodge *= 0.55
    if has(att, "focus"):
        dodge *= 0.6
    if not forced_hit and random.random() < dodge:
        out["dodged"] = True
        return out

    acc = float(att.get("acc") or 0.8)
    if ability:
        acc += 0.05
    if has(att, "blind"):
        acc -= 0.20
    if has(att, "mark") or has(dfd, "mark"):
        acc += 0.14
    if has(att, "accup"):
        acc += 0.08
    if has(dfd, "slow"):
        acc += 0.06
    acc = max(0.25, min(0.97, acc))
    if not forced_hit and random.random() > acc:
        out["missed"] = True
        return out

    dmg = float(att.get("atk") or 1.0) * mult * random.uniform(*config.DMG_VAR)
    tags = set(att.get("tags") or [])
    if ability and ability.get("tag"):
        tags.add(ability["tag"])
    if raw:
        m, note = matchup(tags, raw)
        dmg *= m
        if note:
            out["notes"].append(note)
        ev, evnote = env_factor(raw, env)
        dmg *= ev
        if evnote:
            out["notes"].append(evnote)
    pm = passive_mods(att)
    if pm.get("dmg"):
        dmg *= 1 + pm["dmg"]
    if pm.get("opener") and int(att.get("_turn") or 1) <= 1:
        dmg *= 1 + pm["opener"]
    if pm.get("execution") and float(dfd.get("hp") or 0) > 0.60 * float(dfd.get("max_hp") or 1):
        dmg *= 1 + pm["execution"]
    if pm.get("vs_stun") and (has(dfd, "stun") or has(dfd, "freeze")):
        dmg *= 1 + pm["vs_stun"]
    if pm.get("alternate") and int(att.get("_turn") or 1) % 2 == 1:
        dmg *= 1 + pm["alternate"]
    if pm.get("mob_bonus") and int(att.get("allies") or 0) > 0:
        dmg *= 1 + pm["mob_bonus"]
    if pm.get("per_ally"):
        dmg *= 1 + min(0.24, pm["per_ally"] * int(att.get("allies") or 0))
    if has(att, "rally"):
        dmg *= 1.18
    if has(att, "atkdown"):
        dmg *= 0.82
    if has(att, "focus"):
        dmg *= 1.35
    if is_counter:
        dmg *= config.COUNTER_MULT * (1 + (passive_mods(att).get("counter_bonus") or 0))
    if ability:
        dmg *= 1 + float(ability.get("power", 1.0)) * 0.0

    crit_c = config.CRIT_BASE + float(att.get("crit_bonus") or 0)
    if has(att, "mark"):
        crit_c += 0.12
    if has(att, "accup"):
        crit_c += 0.07
    if (pm.get("first_crit") and int(att.get("_turn") or 1) <= 1) or (att.get("marked_target") and has(dfd, "mark")):
        out["crit"] = True
    elif random.random() < crit_c:
        out["crit"] = True
    if out["crit"]:
        dmg *= config.CRIT_MULT

    if dfd.get("guarded", 0) > 0 or (has(dfd, "guard") and not ignore_guard):
        dmg *= (1 - config.GUARD_REDUCE)
        out["blocked"] = True
    sh = float(dfd.get("shield") or 0.0)
    if sh > 0 and dmg > 0:
        absorbed = min(sh, dmg * 0.75)
        dfd["shield"] = round(sh - absorbed, 2)
        dmg -= absorbed
        out["notes"].append(f"🧱 سپر {absorbed:.1f} را جذب کرد")
    df = float(dfd.get("df") or 0)
    if has(dfd, "defup"):
        df *= 1.25
    if has(dfd, "defdown"):
        df *= 0.72
    if raw:
        pr = passive_mods(dfd)
        if pr.get("berserk_def") and float(dfd.get("hp") or 0) < 0.40 * float(dfd.get("max_hp") or 1):
            df *= 1 + pr["berserk_def"]
    if dfd.get("_pvp"):
        df *= 1.05                                       # مزیت میزبان در نبرد بازیکنان
    dmg = dmg * def_reduce(df)
    out["dmg"] = round(max(1.0, dmg), 2)
    if pm.get("lifesteal"):
        att["hp"] = round(min(float(att.get("max_hp") or 100), float(att["hp"]) + dmg * pm["lifesteal"]), 2)
    return out


def expected_strike(att: dict, dfd: dict, mult: float = 1.0) -> float:
    """آسیب مورد انتظار در هر ضربه (تحلیلی) — مبنای برآوردهای UI."""
    acc = max(0.2, min(0.97, float(att.get("acc") or 0.8)))
    return (float(att.get("atk") or 1) * mult * crit_expect(att) * acc
            * (1 - float(dfd.get("dodge") or 0)) * def_reduce(dfd.get("df")))


# ─────────── آمار بازیکن ───────────
def rank_stats(rank: int) -> dict:
    c = config.RANK_BONDS
    r = max(1, int(rank or 1))
    return dict(hp=c["hp"] * (r - 1), energy=c["energy"] * (r - 1),
                atk=c["atk"] * (r - 1), df=c["df"] * (r - 1))


def player_block(p: dict, gear: dict = None, bonds: list = None) -> dict:
    """آمار رزمی از رنک + تجهیزات + پیوند تایتان‌ها (هیچ‌چیز با پول خریدنی نیست)."""
    gear = gear or {}
    bonds = bonds or []
    rank = int(p.get("rank") or 1)
    r = rank_stats(rank)
    max_hp = float(p.get("max_hp") or config.START_HP) + r["hp"] + gear.get("hp", 0)
    hp = float(p.get("hp") or max_hp)
    resolve = float(p.get("resolve") or 40)
    b = dict(uid=p.get("user_id"), name=p.get("name") or "AGENT", emj="agent", kind="agent",
             max_hp=round(max_hp, 1), hp=round(max(1.0, min(hp, max_hp)), 1),
             max_energy=round(float(p.get("max_energy") or config.START_ENERGY) + gear.get("energy", 0), 1),
             energy=round(float(p.get("energy") or config.START_ENERGY), 1),
             resolve=resolve, rank=rank,
             atk=5.0 + r["atk"] + gear.get("atk", 0) + rank * 0.55,
             df=3.6 + r["df"] + gear.get("df", 0),
             spd=3.4 + gear.get("spd", 0) + min(5.0, resolve / 26),
             acc=min(0.93, 0.70 + resolve / 330 + gear.get("acc", 0)),
             dodge=min(config.DODGE_CAP, 0.05 + gear.get("dodge", 0) + resolve / 1500),
             regen=0.35 + gear.get("regen", 0) + resolve / 420,
             crit_bonus=gear.get("crit", 0.0),
             tags=["kinetic"] + list(gear.get("tags") or []),
             abilities=list(gear.get("abilities") or []), echoes=[],
             statuses=[], charge=0.0, guarded=0, counter_window=0,
             counts={}, uses={}, cd={}, shield=0.0, _pvp=bool(p.get("_pvp")))
    for bt in bonds:
        b["atk"] += bt.get("atk", 0)
        b["df"] += bt.get("df", 0)
        b["spd"] += bt.get("spd", 0)
        b["max_hp"] += bt.get("hp", 0)
        b["hp"] = min(b["hp"] + bt.get("hp", 0) * 0.35, b["max_hp"])
        b["regen"] += bt.get("regen", 0)
        b["acc"] = min(0.95, b["acc"] + bt.get("acc", 0))
        b["dodge"] = min(config.DODGE_CAP, b["dodge"] + bt.get("dodge", 0))
        b["tags"] = sorted(set(b["tags"]) | set(bt.get("tags") or []))
        if bt.get("echo"):
            b["echo"].append(bt["echo"]) if isinstance(b.get("echo"), list) else b["echoes"].append(bt["echo"])
    b["hp"] = round(min(b["hp"], b["max_hp"]), 1)
    for k in ("atk", "df", "regen"):
        b[k] = round(b[k], 2)
    b["power"] = round(b["max_hp"] * 0.42 + b["atk"] * 2.1 + b["df"] * 1.6 + b["spd"] * 0.9
                       + b["max_energy"] * 0.5 + b["acc"] * 60 + b["regen"] * 0.8, 1)
    return b


# ═══════════ کالیبراسیون عددی (با خودِ شبیه‌ساز، نه با عدد دستی) ═══════════
CYCLE = [dict(mult=1.0, guard=0), dict(mult=1.0, guard=0), dict(mult=1.85, guard=0),
         dict(mult=0.0, guard=1), dict(mult=1.0, guard=0), dict(mult=1.85, guard=0),
         dict(mult=1.0, guard=0), dict(mult=1.28, guard=0), dict(mult=1.0, guard=0),
         dict(mult=1.85, guard=0), dict(mult=1.0, guard=0), dict(mult=0.0, guard=1)]
SMART_CYCLE = round(sum(c["mult"] for c in CYCLE) / len(CYCLE), 4)   # ≈۱٫۰۷
SPAM_CYCLE = 0.76
BLOCK_CYCLE = round((len(CYCLE) - sum(c["guard"] for c in CYCLE) * config.GUARD_REDUCE) / len(CYCLE), 4)

TARGET = {"RECON": 0.86, "RARE": 0.76, "ELITE": 0.68, "ALPHA": 0.62,
          "LEGENDARY": 0.55, "OMEGA": 0.50}
SPAM_MAX = 0.34
SKILL_GAP = 0.22            # حداقل فاصله‌ی بردِ ماهرانه از بردِ اسپم

CAL: dict = {}
CAL_FILE = os.path.join(os.path.dirname(__file__), "data", "balance.json")


def ttk_of(t: dict, encounter: float = 1.0) -> float:
    idx = titans_rarity_idx(t["rar"])
    return round((7.0 + 2.6 * idx) * max(0.35, min(2.4, encounter)), 2)


def pace_of(t: dict, encounter: float = 1.0) -> float:
    """نسبتِ زمانِ کشتنِ حریف به زمانِ کشته‌شدنِ بازیکن (۱ = لبه‌ی تیغ).

    کفِ ۱٫۱ عمداً گذاشته شده: بدون حاشیه، نتیجه فقط با RNG تعیین می‌شود و
    کالیبراسیون بی‌معنی است. سختیِ واقعیِ رتبه‌های بالا از encounter، فازهای
    باس، وضعیت‌ها و AI زنده می‌آید — نه از سکه‌اندازیِ مرگ.
    """
    idx = titans_rarity_idx(t["rar"])
    return round(max(1.10, 1.20 - 0.022 * idx) * max(0.75, min(1.6, encounter)), 3)


def titan_stats(t: dict, encounter: float = 1.0) -> dict:
    """آمار پایه‌ی تایتان در واحد بازیکن (بدون کالیبراسیون)."""
    idx = titans_rarity_idx(t["rar"])
    e = max(0.3, min(2.6, encounter))
    df_eff = min(0.80, 0.46 + 0.055 * idx)
    return dict(
        idx=idx, e=e, df=round(config.DEF_K * (1 / (1 - df_eff) - 1), 2),
        dodge=min(config.DODGE_CAP, 0.03 + t["dodge"] / 1100),
        acc=min(0.94, 0.70 + 0.035 * idx), crit_bonus=0.02 + 0.012 * idx,
        spd=round(t["spd"] / NORMALIZE, 2),
        eng=round(t["eng"] / NORMALIZE * 2.0, 1),
        base_atk=round(max(3.0, (t["atk"] / NORMALIZE) * (0.46 + 0.09 * idx) * e), 2),
        base_hp=round(max(25.0, (t["hp"] / NORMALIZE) * (0.26 + 0.15 * idx) * e), 1),
        reg_pct=0.004 + 0.003 * (t["reg"] / 400),
    )


def absolute_block(t: dict, encounter: float = 1.0, hp_k: float = 1.0, atk_k: float = 1.0) -> dict:
    """بلوک کامل حریف؛ hp_k/atk_k اهرم‌های کالیبراسیون‌اند."""
    st = titan_stats(t, encounter)
    hp = round(st["base_hp"] * hp_k, 1)
    b = dict(
        name=t["name"], emj=t["emj"], tid=t["id"], rar=t["rar"], kind="titan",
        hp=hp, max_hp=hp, atk=round(st["base_atk"] * atk_k, 2),
        df=st["df"], spd=st["spd"], acc=st["acc"], dodge=st["dodge"],
        crit_bonus=st["crit_bonus"], regen=round(hp * st["reg_pct"], 2),
        intel=t["int"], threat=t.get("threat", 1),
        energy=st["eng"], max_energy=st["eng"],
        tags=list(t.get("tags", [])), weak=list(t.get("weak", [])), resist=list(t.get("resist", [])),
        pas=t.get("pas"), abilities=list(t.get("ab", [])), ult=t.get("ult"),
        phase=1, ttk=ttk_of(t, encounter), pace=pace_of(t, encounter),
        pressure=st["idx"], encounter=st["e"], aura=0,
    )
    b["_raw"] = t
    b["power"] = t.get("power", 0)
    b["statuses"], b["shield"], b["guarded"] = [], 0.0, 0
    b["charge"], b["counts"], b["uses"], b["cd"] = 0.0, {}, {}, {}
    return b


def tune_block(t: dict, player: dict, encounter: float = 1.0) -> dict:
    """کالیبراسیون قطعی: طول نبرد = ttk هدف، حاشیه‌ی بقا = pace.
    (هیچ عددی دستی نیست؛ هر دو از آمار واقعیِ مهاجم استخراج می‌شوند.)"""
    st = titan_stats(t, encounter)
    ttk, pace = ttk_of(t, encounter), pace_of(t, encounter)
    stub_p = dict(df=st["df"], dodge=st["dodge"])
    per_turn = max(0.6, expected_strike(player, stub_p, mult=SMART_CYCLE))
    hp = round(max(30.0, per_turn * ttk), 1)
    a_stub = dict(atk=100.0, acc=st["acc"], crit_bonus=st["crit_bonus"], df=0.0, dodge=0.0)
    rate = max(0.02, expected_strike(a_stub, dict(df=player.get("df"), dodge=player.get("dodge"),
                                                   cycle_guard=1), mult=1.0) / 100.0)
    atk = round(max(3.0, float(player["max_hp"]) / (ttk * pace * rate)), 2)
    return dict(hp=hp, atk=atk, ttk=ttk, pace=pace, per_turn=round(per_turn, 2),
                rate=round(rate, 3))


_GEAR_AT = None


def register_gear_provider(fn):
    """economy کاتالوگ واقعی آیتم‌ها را می‌دهد تا «بازیکن مرجع» افسانه‌ای نباشد."""
    global _GEAR_AT
    _GEAR_AT = fn


def _gear_at(rank: int) -> dict:
    if _GEAR_AT is not None:
        try:
            g = _GEAR_AT(int(rank))
            if g:
                return dict(g)
        except Exception:
            pass
    r = max(1, int(rank))
    return dict(atk=0.72 * r, df=0.62 * r, hp=3.2 * r, acc=min(0.06, 0.007 * r),
                dodge=min(0.05, 0.005 * r), regen=0.14 * r, energy=1.4 * r, spd=0.22 * r)


def bond_profile(rank: int) -> list:
    """پیوندهای یک بازیکنِ منطقی در این رنک (با همان bond_gain سقف‌دار).

    عمداً «مین‌مکس» نیست: میانگین نیمه‌ی بالای استخرِ مجاز و ترازِ پایین، چون
    بازیکنِ معمولی روی تایتانی که شکار کرده پیوند می‌بندد نه قوی‌ترین تایتانِ بازی.
    """
    rank = max(1, int(rank))
    n = 0 if rank < 5 else min(3, 1 + (rank - 5) // 6)
    if n <= 0:
        return []
    pool = [t for t in TN.TITANS.values()
            if GATE.get(t["rar"], GATE["RARE"])["rank"] <= rank]
    if not pool:
        return []
    pool.sort(key=lambda t: -float(t.get("power") or 0))
    top = pool[:max(1, len(pool) // 2)]
    power = sum(float(t.get("power") or 0) for t in top) / len(top)
    lvl = 1 if rank < 15 else 2
    return [bond_gain(power, lvl) for _ in range(n)]


def benchmark(rank: int) -> dict:
    """پروفیل مرجع MONARCH برای همان رنک: فرمولِ واقعیِ بازیکن + کاتالوگ واقعیِ تجهیزات.

    اگر این پروفیل از بازیکن واقعی دور باشد، کل کالیبراسیون به‌سمت «غیرممکن» می‌رود؛
    پس اینجا عمداً محافظه‌کارانه است (بدون آیتم‌های افسانه‌ای، بدون سقف‌شکنی).
    """
    rank = max(1, int(rank))
    p = dict(user_id=-1, name="BENCHMARK", rank=rank, hp=0,
             max_hp=config.START_HP,
             energy=config.START_ENERGY + 4 * (rank - 1),
             max_energy=config.START_ENERGY + 4 * (rank - 1),
             resolve=min(100, 38 + 3.4 * (rank - 1)))
    p["hp"] = p["max_hp"]
    return player_block(p, _gear_at(rank), bond_profile(rank))


def duel(att: dict, dfd: dict, t: dict, smart: bool = True, max_turns: int = 46,
          env: str = None) -> int:
    """شبیه‌سازی نبرد با resolve_strike واقعی. ۱ = برد مهاجم، ۰ = باخت/ناموفق."""
    import copy
    a = copy.deepcopy(att)
    d = copy.deepcopy(dfd)
    a["statuses"], a["shield"], a["guarded"] = list(a.get("statuses") or []), 0.0, 0
    d["statuses"], d["shield"], d["guarded"] = list(d.get("statuses") or []), 0.0, 0
    d["_raw"] = t
    if d.get("aura"):
        add_status(a, "atkdown", 60, 0)
    # فشار Ability حریف: موتور زنده هر ۳–۴ نوبت یک مهارت می‌زند؛ اگر شبیه‌سازی
    # این را نبیند، کالیبراسیون «آسان‌تر از واقعیت» می‌شود.
    ab_mult, ab_every = 0.0, 0
    try:
        import abilities as _AB
        _pw = [float((_AB.get(x) or {}).get("power") or 0) for x in (d.get("abilities") or [])]
        _pw = [v for v in _pw if v > 0.2]
        if _pw:
            ab_mult = round(0.30 * max(_pw) / 2.2, 3)
            ab_every = 3 if len(_pw) >= 3 else 4
    except Exception:
        ab_mult, ab_every = 0.12, 4
    chain = 0
    for turn in range(1, max_turns + 1):
        a["_turn"], d["_turn"] = turn, turn
        if smart:
            c = CYCLE[(turn - 1) % len(CYCLE)]
            mult, guard = c["mult"], c["guard"]
        else:
            chain += 1
            mult, guard = max(0.50, 1 - 0.09 * chain), 0
        if guard:
            a["guarded"] = 1
        elif mult:
            r = resolve_strike(a, d, mult=mult, env=env)
            d["hp"] = float(d["hp"]) - r["dmg"]
        if float(d["hp"]) <= 0:
            return 1
        if has(d, "stun") or has(d, "freeze"):
            d["statuses"] = [s for s in d["statuses"] if s[0] not in ("stun", "freeze")]
            tick_statuses(d)
            a["guarded"] = 0
            continue
        rd = resolve_strike(d, a, mult=1.0 + (0.24 if turn % 5 == 0 else 0.0) + (0.4 if turn % 11 == 0 else 0.0))
        a["hp"] = float(a["hp"]) - rd["dmg"]
        if rd.get("blocked") and smart and random.random() < 0.55:
            rip = resolve_strike(a, d, mult=1.0, is_counter=True, env=env)
            d["hp"] = float(d["hp"]) - rip["dmg"]
            if float(d["hp"]) <= 0:
                return 1
        if ab_every and turn % ab_every == 0 and ab_mult > 0:
            r2 = resolve_strike(d, a, mult=1.0 + ab_mult, env=env)
            a["hp"] = float(a["hp"]) - r2["dmg"]
        a["guarded"] = 0
        if float(a["hp"]) <= 0:
            return 0
        tick_statuses(a)
        tick_statuses(d)
        if float(d.get("regen") or 0):
            d["hp"] = min(float(d["max_hp"]), float(d["hp"]) + float(d["regen"]))
        if float(a.get("regen") or 0):
            a["hp"] = min(float(a["max_hp"]), float(a["hp"]) + float(a["regen"]))
    return 0


def apply_class_gap(b: dict, t: dict, rank: int) -> dict:
    """فشارِ کلاس: بازیکنِ پایین‌تر از حدِ مجاز، شدتِ بیشتری تحمل می‌کند."""
    need = GATE.get(t["rar"], GATE["RARE"])["rank"]
    gap = max(0, need - int(rank or 1))
    if gap:
        b["aura"] = min(3, 1 + gap // 3)
        b["atk"] = round(b["atk"] * (1 + 0.07 * gap), 2)
    b["need_rank"] = need
    return b


def tuned_block(t: dict, player: dict, encounter: float = 1.0,
                adj: tuple = (1.0, 1.0)) -> dict:
    tn = tune_block(t, player, encounter)
    hp_k = tn["hp"] / max(1.0, 1e-6) * adj[0]
    b = absolute_block(t, encounter)
    b["hp"] = b["max_hp"] = round(tn["hp"] * adj[0], 1)
    b["atk"] = round(tn["atk"] * adj[1], 2)
    b["regen"] = round(b["hp"] * titan_stats(t, encounter)["reg_pct"], 2)
    return b


def win_rate(t: dict, play_rank: int, adj=(1.0, 1.0), smart: bool = True, trials: int = 20,
             encounter: float = 1.0, tune_rank: int = None) -> float:
    """نرخ بردِ یک بازیکنِ هم‌سطحِ play_rank در برابر تایتانی که برای tune_rank کالیبره شده."""
    bench = benchmark(play_rank)
    b = tuned_block(t, benchmark(tune_rank if tune_rank is not None else play_rank), encounter, adj)
    b = apply_class_gap(b, t, play_rank)
    # هر نمونه یک جریانِ RNG مستقل و تکرارپذیر دارد. بدون این، نمونه‌ها با هم فاز
    # می‌گیرند (تعداد draw در هر نبرد ثابت است) و نرخِ بردِ یک‌دفعه ۰٫۱۵ یا ۰٫۷۵
    # خوانده می‌شود؛ یعنی ممیزی تعادل بی‌معنی.
    import zlib
    base = zlib.crc32(f"{t['id']}|{play_rank}|{smart}|{encounter}".encode()) & 0x3FFFFFFF
    saved = random.getstate()
    wins = 0
    for i in range(trials):
        random.seed(base + i * 7919)
        if duel(bench, dict(b), t, smart=smart) > 0:
            wins += 1
    random.setstate(saved)
    return wins / trials


def _wr(t: dict, rank: int, adj: tuple, smart: bool, trials: int, encounter: float) -> float:
    return win_rate(t, rank, tuple(adj), smart, trials, encounter)


def solve_scales(t: dict, rank: int, encounter: float = 1.0, trials: int = 16) -> dict:
    """حلِ تعادل با بای‌سکشن روی یک اهرم مقیاس (hp و atk با هم).

    در تایتان‌های رتبه‌بالا مرز برد/باخت بسیار باریک است (pace≈۱٫۱): جست‌وجوی
    پلکیِ دو‌متغیره روی همان لبه می‌لنگد و نرخِ برد بین ۰ و ۱ پرش می‌کند.
    بای‌سکشن روی یک مقیاس، فرودِ دقیق روی TARGET را ممکن می‌کند؛ سپس یک
    اهرمِ مستقلِ HP اضافه می‌شود تا اسپم تنبیه شود (نبرد بلندتر = جریمه‌ی تکرار).
    """
    target = TARGET.get(t["rar"], 0.7)
    n = max(24, trials * 2)
    lo, hi = 0.06, 2.4
    guard = 0
    while _wr(t, rank, (lo, lo * 0.92), True, 8, encounter) < 0.75 and lo > 0.01 and guard < 8:
        lo /= 1.7
        guard += 1
    guard = 0
    while _wr(t, rank, (hi, hi * 0.92), True, 8, encounter) > 0.25 and hi < 40 and guard < 8:
        hi *= 1.6
        guard += 1
    s = (lo + hi) / 2.0
    for _ in range(7):
        s = (lo + hi) / 2.0
        wr = _wr(t, rank, (s, s * 0.92), True, n, encounter)
        if wr > target + 0.035:
            lo = s
        elif wr < target - 0.035:
            hi = s
        else:
            break
    adj = [s, s * 0.92]
    # ── اسپم‌ستیزی: HP بیشتر، بدون تغییرِ آسیبِ حریف ──
    for _ in range(4):
        sp = _wr(t, rank, (adj[0], adj[1]), False, max(16, trials), encounter)
        sm = _wr(t, rank, (adj[0], adj[1]), True, max(16, trials), encounter)
        if sp <= max(SPAM_MAX, min(0.55, sm - SKILL_GAP)):
            break
        adj[0] *= 1.12
    # ── تایید نهایی با نمونه‌ی بزرگ‌تر و تصحیحِ نسبی (ضدِ نویز نمونه) ──
    n2 = max(40, trials * 3)
    for _ in range(3):
        v = _wr(t, rank, (adj[0], adj[1]), True, n2, encounter)
        if abs(v - target) <= 0.11:
            break
        if v > target:
            adj[0] *= 1 + 0.5 * (v - target)
            adj[1] *= 1 + 0.42 * (v - target)
        else:
            adj[0] /= 1 + 0.55 * (target - v)
            adj[1] /= 1 + 0.62 * (target - v)
    wr = _wr(t, rank, (adj[0], adj[1]), True, n, encounter)
    sp = _wr(t, rank, (adj[0], adj[1]), False, n, encounter)
    return dict(hp_k=round(adj[0], 3), atk_k=round(adj[1], 3),
                smart=round(wr, 2), spam=round(sp, 2),
                ttk=ttk_of(t, encounter), pace=pace_of(t, encounter))


def measure_reset(seed: int = 90210):
    """اندازه‌گیری تکرارپذیر: همان seed ⇒ همان عدد، در CI و روی سرور کاربر."""
    random.seed(seed)


def calibrate(force: bool = False, encounter: float = 1.0, quick: int = 16, seed: int = 4242) -> dict:
    global CAL
    try:
        import economy  # noqa: F401  — ثبت gear provider (پروفیل مرجع واقعی)
    except Exception:
        pass
    measure_reset(seed)
    if CAL and not force:
        return CAL
    if not force and load_cache():
        return CAL
    out = {}
    for t in TN.TITANS.values():
        rank = GATE.get(t["rar"], GATE["RARE"])["rank"] + 2
        out[t["id"]] = solve_scales(t, rank, encounter, trials=quick)
    CAL = out
    try:
        os.makedirs(os.path.dirname(CAL_FILE), exist_ok=True)
        with open(CAL_FILE, "w", encoding="utf-8") as f:
            json.dump(dict(sig=_sig(), encounter=encounter, cal=out), f, ensure_ascii=False, indent=1)
    except Exception:
        pass
    return out


def _sig() -> str:
    raw = "|".join(f"{t['id']}:{t['hp']},{t['atk']},{t['df']},{t['dodge']},{t['rar']}"
                   for t in sorted(TN.TITANS.values(), key=lambda x: x["id"]))
    raw += f"#{config.DEF_K}#{config.CRIT_MULT}#{config.GUARD_REDUCE}#{config.DODGE_CAP}"
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def load_cache() -> bool:
    global CAL
    if os.path.exists(CAL_FILE):
        try:
            with open(CAL_FILE, encoding="utf-8") as f:
                blob = json.load(f)
            if blob.get("sig") == _sig():
                CAL = blob["cal"]
                return True
        except Exception:
            pass
    return False


def tune_rank_of(t: dict) -> int:
    """رنکِ مرجعی که تعادل آن تایتان روی آن حل شده (بزرگ‌نمایی حریف اینجا قفل است)."""
    return GATE.get(t["rar"], GATE["RARE"])["rank"] + 2


def titan_block(t: dict, encounter: float = 1.0, rank: int = 1, ref: dict = None) -> dict:
    """بلوک نهایی حریف برای موتور نبرد: کش تعادل + فشارِ کلاس.

    اندازه‌ی حریف **قفلِ رنک مرجع** است (نه رنک بازیکن)؛ در نتیجه装备/پیوند/رنک
    واقعاً نبرد را آسان می‌کنند و بازیکنِ زیرِ رنکِ مجاز جریمه می‌شود (aura).
    """
    if not CAL:
        load_cache()
    cal = (CAL or {}).get(t["id"], {})
    tr = tune_rank_of(t)
    need = int(GATE.get(t["rar"], GATE["RARE"])["rank"])
    ref_rank = max(need, min(int(rank or 1), tr))
    b = tuned_block(t, ref or benchmark(ref_rank), encounter,
                    (float(cal.get("hp_k", 1.0)), float(cal.get("atk_k", 1.0))))
    b = apply_class_gap(b, t, rank)
    b["cal_smart"] = cal.get("smart")
    b["cal_spam"] = cal.get("spam")
    b["tune_rank"] = tr
    b["ref_rank"] = ref_rank
    return b


def estimate_fight(t: dict, player: dict, encounter: float = 1.0) -> dict:
    """برآورد شفاف برای UI («آماده‌ای یا نه» نباید حدس باشد)."""
    b = titan_block(t, encounter=encounter, rank=int(player.get("rank") or 1))
    mine = expected_strike(player, b, mult=SMART_CYCLE)
    theirs = expected_strike(b, player, mult=1.0) * BLOCK_CYCLE
    return dict(player_turns=round(b["hp"] / max(0.6, mine), 1),
                titan_turns=round(float(player["max_hp"]) / max(0.6, theirs), 1),
                need_rank=b["need_rank"], aura=b.get("aura", 0),
                ready=int(player.get("rank") or 1) >= b["need_rank"] and not b.get("aura"),
                hp=b["hp"], atk=b["atk"], ttk=b["ttk"])


# ─────────── جایزه ───────────
RARITY_REWARD = {"RECON": (1.0, 1.0), "RARE": (1.25, 1.3), "ELITE": (1.55, 1.65),
                 "ALPHA": (1.95, 2.1), "LEGENDARY": (2.5, 2.7), "OMEGA": (3.1, 3.4)}


def victory_payout(t: dict, *, rank: int = 1, first_kill: bool = False,
                   perfect: bool = False, encounter: float = 1.0) -> dict:
    mc, mult = RARITY_REWARD.get(t.get("rar", "RECON"), (1.0, 1.0))
    out = dict(credits=round(80 * mc * (0.9 + 0.04 * rank) * random.uniform(0.85, 1.15) * encounter, 0),
               xp=round(26 * mult * random.uniform(0.9, 1.15) * encounter, 1),
               dna=round(1.5 * mult * random.uniform(0.7, 1.3) * encounter, 1),
               cells=round(1.0 * mult, 0), mats=round(0.8 * mult, 0),
               fdata=round(0.6 * mult, 0), cores=0.0)
    if random.random() < 0.09 * mult:
        out["cores"] += 1
    if first_kill:
        out["credits"] += 120 * mult
        out["cores"] += 1
    if perfect:
        out["xp"] = round(out["xp"] * 1.3, 1)
        out["cores"] += 1 if random.random() < 0.4 else 0
    return out


# ─────────── رتبه ───────────
RANKS = {
    "recruit": dict(name="MONARCH Recruit", emj="🛰", idx=1, need=1),
    "researcher": dict(name="Researcher", emj="🔬", idx=3, need=3),
    "field_agent": dict(name="Field Agent", emj="📡", idx=7, need=7),
    "titan_specialist": dict(name="Titan Specialist", emj="⚔️", idx=12, need=12),
    "alpha_commander": dict(name="Alpha Commander", emj="👑", idx=18, need=18),
}


def rank_key(rank: int) -> str:
    r = int(rank or 1)
    for k in ("alpha_commander", "titan_specialist", "field_agent", "researcher", "recruit"):
        if r >= RANKS[k]["need"]:
            return k
    return "recruit"


def rank_title(rank: int) -> str:
    k = rank_key(rank)
    return f"{RANKS[k]['emj']} {RANKS[k]['name']}"


def xp_need(rank: int) -> float:
    r = max(1, int(rank or 1))
    return round(config.XP_BASE * (r ** 1.12) + config.XP_STEP * (r - 1), 1)


# ─────────── دروازه‌های کشف/پیوند (بسیار سخت) ───────────
GATE = {
    "RECON": dict(dna=3, fdata=1, kills=1, rank=1, cores=0, lab=0),
    "RARE": dict(dna=8, fdata=3, kills=2, rank=3, cores=0, lab=1),
    "ELITE": dict(dna=16, fdata=7, kills=3, rank=6, cores=1, lab=1),
    "ALPHA": dict(dna=30, fdata=14, kills=4, rank=9, cores=3, lab=2),
    "LEGENDARY": dict(dna=58, fdata=30, kills=6, rank=13, cores=7, lab=3),
    "OMEGA": dict(dna=90, fdata=48, kills=8, rank=17, cores=12, lab=4),
}


def gate_of(rar: str) -> dict:
    g = dict(GATE.get(rar, GATE["RARE"]))
    g["idx"] = titans_rarity_idx(rar)
    return g


def bond_gain(power: float, bond: int) -> dict:
    """مزیت هر تراز پیوند (سقف‌دار؛ تایتان به‌تنهایی برد قطعی نمی‌آورد)."""
    t = max(0, min(config.BOND_MAX, int(bond)))
    f = t * 0.045
    return dict(hp=round(power * 0.0026 * t, 1), atk=round(power * 0.0034 * t, 2),
                df=round(power * 0.0022 * t, 2), spd=round(f * 5, 2),
                acc=min(0.05, f * 0.10), dodge=min(0.04, f * 0.08),
                regen=round(f * 1.2, 2), tags=[], mult=round(f, 3))


# ─────────── ممیزی تعادل ───────────
def audit(trials: int = 24, recalc: bool = False, seed: int = 90210) -> dict:
    try:
        import economy  # noqa: F401  — بدون آن benchmark با فرمولِ پشتیبانی حساب می‌شود
    except Exception:
        pass
    measure_reset(seed)
    if recalc:
        calibrate(force=True, quick=trials)
    if not CAL:
        load_cache() or calibrate(quick=trials)
    rows, problems = [], []
    for t in TN.TITANS.values():
        rank = GATE.get(t["rar"], GATE["RARE"])["rank"] + 2
        cal = (CAL or {}).get(t["id"], {})
        adj = (float(cal.get("hp_k", 1.0)), float(cal.get("atk_k", 1.0)))
        smart = win_rate(t, rank, adj, True, trials)
        spam = win_rate(t, rank, adj, False, trials)
        low = win_rate(t, max(1, rank - 6), adj, True, trials, tune_rank=rank)
        rows.append(dict(id=t["id"], name=t["name"], rar=t["rar"], power=t["power"],
                         hp_k=adj[0], atk_k=adj[1], ttk=ttk_of(t), smart=round(smart, 2),
                         spam=round(spam, 2), underleveled=round(low, 2)))
        if smart > 0.93 and t["rar"] != "RECON":
            problems.append(f"⚠ {t['name']} Auto-Win است (smart {smart:.2f})")
        if smart < 0.28:
            problems.append(f"⚠ {t['name']} برای هم‌رنک خودش غیرممکن است ({smart:.2f})")
        if spam > max(SPAM_MAX if t["rar"] != "RECON" else 0.5, smart - SKILL_GAP):
            problems.append(f"⚠ {t['name']}: اسپم پاداش دارد (spam {spam:.2f} vs smart {smart:.2f})")
        if t["rar"] in ("ALPHA", "LEGENDARY", "OMEGA") and low > 0.66:
            problems.append(f"⚠ {t['name']} برای رنکِ پایین خیلی آسان است ({low:.2f})")
    span = max(r["power"] for r in rows) / max(1e-6, min(r["power"] for r in rows))
    return dict(rows=sorted(rows, key=lambda r: -r["power"]), problems=problems,
                span=round(span, 2), n=len(rows), calibrated=len(CAL or {}))
