# 🛰 UI Kit — سامانۀ بصری «پروندۀ محرمانه» (بدون وابستگی به aiogram)
"""همه‌ی ظاهرِ بازی از همین‌جا ساخته می‌شود؛ هیچ ماژول دیگری خط‌چین/نوار/برچسب
دستی نمی‌سازد. قراردادها:

· متنِ کاربر کامل فارسی (لاتین فقط شناسه/کد/دستورِ اسلش)
· یک چارچوبِ واحد: سربرگ ← خطِضخیم ← بدنه ← خطنازک ← پانوشت
· فیدِ نبرد فشرده است (ضداسپم): همیشه یک پیام، همیشه کوتاه
"""
import json
import os
import re

import emoji as E
from db import now

RULE = "━" * 20        # خطِ بیرونیِ پرونده
HAIR = "▬" * 12        # جداکننده‌ی بخش‌ها
DOT = "·"


# ───────────────────────── عدد و اندازه ─────────────────────────
def bar(cur: float, mx: float, width: int = 9, full="▰", empty="▱") -> str:
    mx = max(0.0001, float(mx))
    f = max(0.0, min(1.0, float(cur) / mx))
    n_ = int(round(f * width))
    return full * n_ + empty * (width - n_)


def pct(cur: float, mx: float) -> int:
    return int(round(100 * max(0.0, float(cur)) / max(0.0001, float(mx))))


def n(x, dec: int = 0) -> str:
    """عدد تمیز: ۱۲٫۴k / ۳٫۱M"""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "0"
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:.1f}M"
    if abs(v) >= 10_000:
        return f"{v / 1000:.1f}k"
    if dec:
        return f"{v:,.{dec}f}"
    return f"{v:,.0f}"


def dur(secs: float) -> str:
    """مدت‌زمانی فارسی — بدون حرف لاتین."""
    s = max(0, int(secs))
    h, m, s2 = s // 3600, (s % 3600) // 60, s % 60
    if h:
        return f"{h} ساعت و {m:02d} دقیقه"
    if m:
        return f"{m} دقیقه و {s2:02d} ثانیه"
    return f"{s2} ثانیه"


def eta(ts: float) -> str:
    left = max(0.0, float(ts) - now())
    return dur(left) if left > 0 else "اکنون"


# ───────────────────────── چارچوبِ پرونده ─────────────────────────
def head(title: str, sub: str = "", stamp: str = "", code: str = "") -> list:
    """سربرگ: عنوان + مُهرِ طبقه‌بندی + شمارۀ پرونده."""
    out = [f"{E.get('satellite')} {RULE}"]
    t = f"<b>{title}</b>"
    if code:
        t += f" <code>#{code}</code>"
    out.append(t)
    if sub:
        out.append(f"<i>{sub}</i>")
    if stamp:
        out.append(f"<i>◈ {E.get('lock')} {stamp}</i>")
    out.append(RULE)
    return out


def foot(note: str = "") -> list:
    return [HAIR, f"<i>🛰 {note}</i>"] if note else [HAIR]


def card(title: str, rows: list, sub: str = "", status: str = "", cls: str = None,
         stamp: str = "", code: str = "", note: str = "") -> str:
    """یک «پروندۀ» کامل: سربرگ ← بدنه ← پانوشت. وضع = خطِ وضعیتِ سبز/خاکستری."""
    st = stamp or cls or ""
    out = head(title, sub or status, st, code)
    out += [x for x in rows if x not in (None, "")]
    out += foot(note or "تایتان‌ها از قبل اینجا بودند.")
    return "\n".join(out)


def sect(label: str, icon: str = "◆") -> str:
    return f"\n<i>{icon} {label}</i>"


def kv(label: str, value, icon: str = "", tail: str = "") -> str:
    v = value if isinstance(value, str) else n(value)
    label = str(label)
    return f"{icon} {label}: <b>{v}</b>{(' ' + tail) if tail else ''}"


def meter(label: str, cur, mx, icon: str = "", width: int = 10, show: str = "val") -> str:
    c, m = max(0.0, float(cur or 0)), max(0.0001, float(mx or 1))
    p = pct(c, m)
    val = f"<b>{n(c)}</b>/{n(m)}" if show == "val" else f"<b>{p}%</b>"
    return re.sub(r"\s{2,}", " ", f"{icon} {label} {bar(c, m, width, '▰', '▱')} {val}").strip()


def chip(text: str, icon: str = "") -> str:
    return f"<code>{icon}{text}</code>"


def elem(x: str) -> str:
    """نامِ عنصر/نقطه‌ضعف → فارسی (`fa.TOK` تنها منبعِ واژه‌نامه است)."""
    import fa
    k = re.sub(r"[^a-z]", "", str(x or "").lower())
    return fa.TOK.get(k) or str(x or "")


def tags(items: list, sep: str = f" {DOT} ") -> str:
    return sep.join(str(x) for x in items if x not in (None, "", "—")) or "—"


def pair_rows(items: list, per: int = 2, fmt=lambda x: x) -> list:
    out = []
    for i in range(0, len(items), per):
        out.append(f" {DOT} ".join(fmt(x) for x in items[i:i + per]))
    return out


# ───────────────────────── سازگار با نام‌های قبلی ─────────────────────────
def header(title: str = "فرماندهی", status: str = "دسترسی تأیید شد", cls: str = None) -> str:
    e = E.get
    top = f"{e('satellite')} <b>مانارچ {title}</b>"
    line = f"<i>{e('check')} {status}</i>"
    if cls:
        line += f" · <code>{cls}</code>"
    return f"{top}\n{HAIR}\n{line}"


def footer(note: str = "تایتان‌ها از قبل اینجا بودند.") -> str:
    return f"{HAIR}\n<i>🛰 {note}</i>"


def divider() -> str:
    return HAIR


def mono(text: str) -> str:
    return f"<code>{text}</code>"


def block(label: str, value: str, icon: str = None) -> str:
    ic = E.get(icon, "file") if icon else "▪️"
    return f"{ic} {label}: <b>{value}</b>"


def stat_line(label: str, cur, mx, icon: str, extra: str = "") -> str:
    return (f"{E.get(icon)} {label:<7}{bar(cur, mx)} "
            f"<b>{n(cur)}</b>/{n(mx)}{extra}")


def classified(rows: list, title: str = "پروندۀ تایتان", cls: str = "محرمانه") -> str:
    return "\n".join(head(title, stamp=cls) + list(rows) + [HAIR])


def threat_stars(level: int) -> str:
    level = max(1, min(5, int(level or 1)))
    return "☢️" * level + "・" * (5 - level)


def hp_color(p: float) -> str:
    p = float(p or 0)
    return "🟢" if p > 0.66 else ("🟡" if p > 0.33 else "🔴")


def rarity_badge(rar: str) -> str:
    from titans import RARITY
    r = RARITY.get(rar) or {}
    return f"<code>{r.get('cls', 'ناشناخته')}</code> {DOT} {r.get('name', rar)}"


def rank_bar(rank: int, xp: float, need: float) -> str:
    return f"{bar(xp, need, 12)} <i>{n(xp)}/{n(need)} تجربه</i>"


def circle(p: float) -> str:
    p = max(0, min(4, int(round(p * 4))))
    return "◴◶◵●"[p % 4]


def grid(items: list, per_row: int = 2) -> list:
    return [items[i:i + per_row] for i in range(0, len(items), per_row)]


# ───────────────────────── کارت‌های آمادۀ سطوح ─────────────────────────
def agent_card(d: dict) -> str:
    """کارتِ عامل — d از player.profile_text ساخته می‌شود (بدون وابستگیِ متقابل)."""
    rows = [f"👤 <b>{d.get('name', '—')}</b> {DOT} <i>{d.get('handle', '')}</i>" if d.get("handle")
            else f"👤 <b>{d.get('name', '—')}</b>",
            kv("رتبه", d.get("rank_name", "—"), "🎖", f"<code>سطح {d.get('rank', 1)}</code>"),
            f"✨ {rank_bar(d.get('rank', 1), d.get('xp', 0), d.get('xp_need', 1))}", ""]
    rows += [meter("جان", d.get("hp", 0), d.get("max_hp", 1), "❤️"),
             meter("انرژی", d.get("energy", 0), d.get("max_energy", 1), "🔋"),
             kv("عزم", d.get("resolve", 0), "🧠", f"{DOT} قدرتِ رزمی <b>{n(d.get('power', 0))}</b>"), ""]
    rows += [sect("میدان"),
             f" {DOT} ".join(x for x in (kv("آسیب", d.get("atk", 0), "⚔️"), kv("سپر", d.get("df", 0), "🛡"),
                                         kv("سرعت", d.get("spd", 0), "⚡")) if x),
             f" {DOT} ".join(x for x in (kv("دقت", d.get("acc_txt", "—"), "🎯"),
                                         kv("جاخالی", d.get("dodge_txt", "—"), "🌀"),
                                         kv("بازیابی", d.get("regen", 0), "💚")) if x)]
    if d.get("res_lines"):
        rows += ["", sect("منابع")] + list(d["res_lines"])
    if d.get("gear"):
        rows += ["", sect("تجهیزات فعال"), *d["gear"]]
    if d.get("bonds"):
        rows += ["", sect("پیوندهای تایتان"), *d["bonds"]]
    if d.get("zone"):
        rows += ["", f"🌍 {d['zone']} {DOT} ⏳ {d.get('zone_left', '')}"]
    if d.get("dead"):
        rows += ["", f"☠️ <b>حالتِ بازیابی</b> — {d['dead']}"]
    return card(f"کارتِ عامل · پروندۀ پرسنلی", rows, code=d.get("code", ""),
                stamp=d.get("cls", "تأیید شده"), note="مانارچ هیچ‌کس را جا نمی‌گذارد.")


def titan_file(d: dict, hidden: bool = False) -> str:
    """پروندۀ تایتان — هم نسخۀ «ناشناخته» و هم پروندۀ کامل."""
    if hidden:
        rows = ["🗝 وضعیت: <b>ناشناخته</b>", "",
                "<i>هیچ امضای تأییدشدۀ ثبت نشده است.</i>", "",
                kv("جرمِ تخمینی", d.get("mass", "—"), "⚖️"),
                kv("سطحِ تهدید", threat_stars(d.get("threat", 1)), "☢️"), "",
                "📡 با <code>/track</code> در منطقۀ سازگار سیگنال جمع کن."]
        return card(f"{d.get('emj', '🕳')} {d.get('name', 'تایتانِ ناشناخته')}", rows,
                    code=d.get("code", ""), stamp="محرمانه", note="فایلِ باز نشده — اول ببینش.")
    rows = [d["badge"]] if d.get("badge") else []
    rows += [f"<i>{d.get('origin', '')}</i>",
            f" {DOT} ".join(x for x in (kv("قد", d.get("h", "—"), "📏"), kv("جرم", d.get("w", "—"), "⚖️"),
                                        kv("تهدید", threat_stars(d.get("threat", 1)), "☢️")) if x),
            "", d.get("lore", ""), "", sect("آمار بنیادی")]
    rows += pair_rows(d.get("stats", []), 2,
                      lambda x: f"{x[0]} <code>{f'{float(x[1]):,.0f}' if abs(float(x[1])) >= 10 else f'{float(x[1]):,.1f}'}{''}</code>")
    rows += ["", sect("میدانِ نبرد"),
             f"🌍 {tags(d.get('env', []))}",
             f"❌ نقطۀ ضعف: <b>{tags([elem(x) for x in d.get('weak', [])])}</b>",
             f"🛡 مقاومت: <b>{tags([elem(x) for x in d.get('resist', [])])}</b>"]
    if d.get("passive"):
        rows += ["", sect("ذاتی"), f"🧬 <b>{d['passive'][0]}</b> — {d['passive'][1]}"]
    if d.get("abilities"):
        rows += ["", sect("مهارت‌ها")] + d["abilities"]
    if d.get("ultimate"):
        rows += ["", sect("ضربۀ نهایی", "👑"), d["ultimate"]]
    if d.get("research"):
        rows += ["", sect("پژوهش و پیوند"), d["research"]]
    if d.get("gate_missing"):
        rows += ["", sect("پیش‌نیازهای پیوند", "🔓")] + [f"▪️ {m}" for m in d["gate_missing"]]
    elif d.get("bond_ready"):
        rows += ["", f"✅ <b>آمادۀ پیوند</b> — <code>/bond {d.get('id', '')}</code>"]
    return card(f"{d.get('emj', '🦖')} {d.get('name', '')}", rows, code=d.get("code", ""),
                stamp=d.get("cls", "محرمانه"), note=d.get("note", "بخوان، بعد شکار کن."))


# ───────────────────────── فیدِ نبرد (ضداسپم) ─────────────────────────
def combat_feed(state: dict, lines: list, title: str = "گزارش درگیری") -> str:
    """یک پیامِ فشرده که ویرایش می‌شود — قلبِ تجربه‌ی MMO."""
    e = E.get
    a, d = state["a"], state["d"]
    from titans import ENVS
    env = state.get("env") or "ocean"
    out = [f"{e('sword')} <b>{title}</b> <i>{DOT} {ENVS.get(env, env)}</i> "
           f"<i>{DOT} نوبت {state.get('turn', 1)}</i>", HAIR]
    a_hp, d_hp = max(0.0, float(a.get("hp", 0))), max(0.0, float(d["hp"]))
    ap = pct(a_hp, a.get("max_hp", 1))
    out.append(f"🛰 <b>{a.get('name', 'عامل')}</b> {hp_color(ap / 100)} {meter('', a_hp, a['max_hp'], '', 9)}")
    out.append(f"   🔋 {bar(a.get('energy', 0), a.get('max_energy', 100), 7)} {n(a.get('energy', 0))} "
               f"{DOT} ☢️ {n(a.get('charge', 0))}٪")
    out.append(f"   {'  '.join(status_tags(a))}")
    dp = pct(d_hp, d["max_hp"])
    foe = (f"{e('boss')} <b>{d.get('name', 'ناشناخته')}</b> {hp_color(dp / 100)} "
           f"{meter('', d_hp, d['max_hp'], '', 9)}")
    extra = []
    if state.get("phase"):
        extra.append(f"فاز {state['phase']}")
    if float(state.get("rage") or 0) >= 1:
        extra.append(f"🔥 خشم {n(float(state.get('rage')) * 100):.0f}٪")
    if state.get("strikes_left") is not None:
        extra.append(f"⏳ حملۀ بعدی: {state['strikes_left']}")
    out.append(foe + (("  <i>" + "  ".join(extra) + "</i>") if extra else ""))
    out.append(f"   {'  '.join(status_tags(d))}")
    out.append(HAIR)
    log = [x for x in (lines or [])[-5:] if x]
    out += [f"▸ {x}" for x in (log or ["<i>میدان آرام است…</i>"])]
    return "\n".join(out)


def status_tags(unit: dict) -> list:
    from balance import STATUS_META
    out = []
    for sid, turns, val in unit.get("statuses") or []:
        m = STATUS_META.get(sid, {})
        out.append(f"<i>{m.get('emj', '•')}{turns}</i>")
    if float(unit.get("shield") or 0) > 0:
        out.append(f"<i>🧱{n(unit['shield'], 1)}</i>")
    return out or ["<i>—</i>"]


# ─────────── کارت تصویری تایتان (Pinterest / assets) ───────────
_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "titans")
_PHOTO_MANIFEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "titan_photos.json")
_photos = None
_ext = (".jpg", ".jpeg", ".png", ".webp")


def _photo_map() -> dict:
    """data/titan_photos.json → {tid: url} (URL مستقیم تصویر؛ تلگرام خودش می‌گیرد)."""
    global _photos
    if _photos is None:
        try:
            with open(_PHOTO_MANIFEST, encoding="utf-8") as f:
                blob = json.load(f)
            _photos = {k: v for k, v in blob.items() if v} if isinstance(blob, dict) else {}
        except Exception:
            _photos = {}
    return _photos


def titan_photo(tid: str):
    """مسیر فایل محلی یا URL تصویرِ کارت — اگر هیچ‌کدام نبود None (کارت متنی می‌ماند)."""
    if not tid:
        return None
    for e in _ext:
        fp = os.path.join(_ASSETS, f"{tid}{e}")
        if os.path.exists(fp):
            return fp
    return _photo_map().get(str(tid))


def photo_count() -> int:
    have = set()
    if os.path.isdir(_ASSETS):
        have |= {os.path.splitext(f)[0] for f in os.listdir(_ASSETS) if f.endswith(_ext)}
    return len(have | set(_photo_map()))
