# 🛰 UI Kit — فرمت «پرونده‌ی محرمانه MONARCH» (بدون وابستگی به aiogram)
import math

import emoji as E
from db import now


def bar(cur: float, mx: float, width: int = 9, full="▰", empty="▱") -> str:
    mx = max(0.0001, float(mx))
    f = max(0.0, min(1.0, float(cur) / mx))
    n = int(round(f * width))
    return full * n + empty * (width - n)


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
    s = max(0, int(secs))
    h, m, s2 = s // 3600, (s % 3600) // 60, s % 60
    if h:
        return f"{h}h {m:02d}m"
    if m:
        return f"{m}m {s2:02d}s"
    return f"{s2}s"


def header(title: str = "COMMAND", status: str = "ACCESS GRANTED", cls: str = None) -> str:
    e = E.get
    top = f"{e('satellite')} <b>MONARCH {title}</b>"
    line = f"<i>{e('check')} {status}</i>"
    if cls:
        line += f" · <code>{cls}</code>"
    return f"{top}\n▬▬▬▬▬▬▬▬▬▬▬▬\n{line}"


def footer(note: str = "THE TITANS ARE ALREADY HERE.") -> str:
    return f"▬▬▬▬▬▬▬▬▬▬▬▬\n<i>🛰 {note}</i>"


def block(label: str, value: str, icon: str = None) -> str:
    e = E.get
    ic = E.get(icon, "file") if icon else "▪️"
    return f"{ic} {label}: <b>{value}</b>"


def stat_line(label: str, cur, mx, icon: str, extra: str = "") -> str:
    return (f"{E.get(icon)} {label:<7}{bar(cur, mx)} "
            f"<b>{n(cur)}</b>/{n(mx)}{extra}")


def classified(rows: list, title: str = "TITAN FILE", cls: str = "CLASSIFIED") -> str:
    e = E.get
    out = [f"{e('file')} <b>MONARCH DATABASE</b> — {title}", f"<i>◈ {e('lock')} {cls}</i>", ""]
    out += rows
    return "\n".join(out)


def threat_stars(level: int) -> str:
    level = max(1, min(5, int(level or 1)))
    return "☢️" * level + "・" * (5 - level)


def combat_feed(state: dict, lines: list, title: str = "ENGAGEMENT LOG") -> str:
    """کمپکت‌فید: همیشه یک پیام، ویرایش می‌شود (ضداسپم)."""
    e = E.get
    a, d = state["a"], state["d"]
    env = state.get("env") or "ocean"
    from titans import ENVS
    out = [f"{e('sword')} <b>MONARCH — {title}</b>",
           f"<i>🌍 {ENVS.get(env, env)} · نوبت {state.get('turn', 1)}</i>", ""]
    out.append(f"🛰 <b>{a.get('name', 'AGENT')}</b> {stat_line('', a['hp'], a['max_hp'], 'vitals')}"
               f"\n   🔋 {bar(a.get('energy', 0), a.get('max_energy', 100), 6)} "
               f"⚡ {n(a.get('energy', 0))} · ☢️ {n(a.get('charge', 0))}%")
    out.append(f"{'  '.join(status_tags(a))}")
    out.append("")
    out.append(f"{e('boss')} <b>{d.get('name', 'UNKNOWN')}</b> "
               f"{stat_line('', d['hp'], d['max_hp'], 'vitals')} "
               f"<i>{pct(d['hp'], d['max_hp'])}%</i>")
    out.append(f"{'  '.join(status_tags(d))}")
    out.append("")
    out.append("\n".join(lines[-6:]))
    return "\n".join(x for x in out if x is not None)


def status_tags(unit: dict) -> list:
    from balance import STATUS_META
    out = []
    for sid, turns, val in unit.get("statuses") or []:
        m = STATUS_META.get(sid, {})
        out.append(f"<i>{m.get('emj', '•')}{turns}</i>")
    if float(unit.get("shield") or 0) > 0:
        out.append(f"<i>🧱{n(unit['shield'], 1)}</i>")
    return out or ["<i>—</i>"]


def hp_color(p: float) -> str:
    if p > 0.66:
        return "🟢"
    if p > 0.33:
        return "🟡"
    return "🔴"


def rarity_badge(rar: str) -> str:
    from titans import RARITY
    r = RARITY.get(rar) or {}
    return f"<code>{r.get('cls', 'UNKNOWN')}</code> · {r.get('name', rar)}"


def rank_bar(rank: int, xp: float, need: float) -> str:
    return f"{bar(xp, need, 12)} <i>{n(xp)}/{n(need)} XP</i>"


def divider() -> str:
    return "▬" * 12


def mono(text: str) -> str:
    return f"<code>{text}</code>"


def eta(ts: float) -> str:
    left = max(0.0, float(ts) - now())
    return dur(left) if left > 0 else "اکنون"


def circle(p: float) -> str:
    p = max(0, min(4, int(round(p * 4))))
    return "◴◶◵●"[p % 4]


def grid(items: list, per_row: int = 2) -> list:
    return [items[i:i + per_row] for i in range(0, len(items), per_row)]
