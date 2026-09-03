#!/usr/bin/env python3
"""🖼 ساختِ تصویرِ زندهٔ رابط — `preview/rebuilt-ui.html`.

اسکریپت، موتورِ واقعیِ بازی را با harness تست بالا می‌آورد (بدون شبکه)، چند
سطح را اجرا می‌کند و همان متن‌ها را در یک HTML تیرهٔ RTL می‌چیند. بعد از هر
تغییرِ ظاهری فقط این را اجرا کن:

    python3 preview/build.py
"""
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "monarch"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import test_game as T                                                  # noqa: E402
import access as GATE                                                  # noqa: E402
import combat                                                          # noqa: E402
import kb                                                              # noqa: E402
import player as PL                                                    # noqa: E402
import post_channel as PC                                              # noqa: E402
import raid as RA                                                      # noqa: E402
import research                                                        # noqa: E402
import titans as TN                                                    # noqa: E402
import ui                                                              # noqa: E402


def kb_lines(markup) -> str:
    rows = []
    for r in markup.inline_keyboard:
        rows.append("  ".join(f"[{b.text}]" + ("↗" if b.url else "") for b in r))
    return "\n".join(rows)


def build() -> list:
    out = []
    uid, chat_id, chat = T.new_player(rank=14)
    T.fund(uid, credits=4200, cores=9, dna=14, cells=22, mats=17, fdata=11)
    PL.set_row(uid, xp=5200)

    # ۱) کارتِ عامل (گامِ بعد + کارنامه + جریانِ عملیات)
    out.append(("کارتِ عامل — /me", PL.card(PL.get(uid))))

    # ۲) پروندۀ تایتان
    kong = TN.get("kong")
    out.append(("پروندۀ تایتان — /dossier کونگ", research.dossier(uid, kong)))

    # ۳) فید نبرد
    res = combat.start(uid, "hunt", chat=chat, titan_id="hedorah")
    cid = res.get("cid") or res.get("id") or (res.get("row") or {}).get("id")
    feed = [res.get("feed") or res.get("msg") or ""]
    for act in ("heavy", "guard", "charge", "ability", "overdrive", "attack"):
        r = combat.act(int(cid), uid, act) if cid else {}
        feed.append(r.get("feed") or r.get("msg") or "")
    _row, st = combat._load(int(cid))
    out.append(("فیدِ فشردهٔ نبرد — شش کردار، یک پیام (گروه شلوغ نمی‌شود)",
                ("\n".join(x for x in feed if x)) + "\n\n" + combat._quick_view(st)))

    # ۴) تابلوی یورش + دکمه‌های فارسیِ تازه
    RA.start("hollow_breach")
    for other, _c, _ch in (T.new_player(rank=9),):
        RA.join(other)
    for act in ("strike", "focus", "shield", "analyze", "regroup", "strike"):
        RA.act(uid, act)
    out.append(("یورشِ جهانی — تابلو و دکمه‌ها (نام و هزینه از خودِ موتور)",
                RA.board() + "\n\n" + kb_lines(RA_HACK())))

    # ۵) منوی خلوت در برابر منوی کامل
    out.append(("منوی اصلی — ۴ ردیف، ۸ دکمه",
                "🛰 تابلوی فرماندهی\n\n" + kb_lines(kb.main_menu(PL.get(uid), has_combat=True))
                + "\n\n▸ «همۀ دستورها»:\n" + kb_lines(kb.full_menu(PL.get(uid)))))

    # ۶) دروازۀ پیوی
    out.append(("پیوی — فقط دروازہ (هیچ بازی اینجا اجرا نمی‌شود)",
                GATE.pv_text("سرِ‌کارِ تازه‌وارث") + "\n\n" + kb_lines(GATE.kb_for("pv"))))

    # ۷) دروازۀ گروه خلوت
    out.append(("گروهِ ۴ نفره — قفل است، و فقط یک بار در ۱۵ دقیقه هشدار می‌دهد",
                GATE.small_text(4) + "\n\n" + kb_lines(GATE.kb_for("small"))))

    # ۸) کانال
    out.append(("کانال · پروندۀ ۰۰۰ — شروعِ سریع", PC.start_card()))
    out.append(("کانال · درس ۰۳", PC.lesson_card(3, len(T.texts.LESSONS),
                                                 T.texts.LESSONS[2]["title"],
                                                 T.texts.LESSONS[2]["body"])))
    out.append(("کانال · پرسش‌های مکرر", PC.faq_card()))
    return out


def RA_HACK():
    """دکمه‌های یورش از خودِ handlers (منبعِ واحدِ حقیقت)."""
    import handlers as H
    return H._raid_kb()


CSS = """:root{--bg:#070b12;--ink:#d6e6ff;--dim:#7f9bc4;--line:#1d2a3d;--acc:#37d6a0}
*{box-sizing:border-box}
body{margin:0;padding:34px 16px 60px;background:radial-gradient(1200px 620px at 82% -12%,#101d2e 0%,var(--bg) 62%);color:var(--ink);font:15px/2 Vazirmatn,IRANSans,Tahoma,sans-serif}
h1{font-size:19px;margin:0 auto 6px;max-width:900px;color:#eef5ff}
p.sub{max-width:900px;margin:0 auto 26px;color:var(--dim);font-size:13px;line-height:1.9}
main{max-width:900px;margin:0 auto;display:grid;gap:18px}
section{background:linear-gradient(180deg,#0c1626,#0a1119);border:1px solid var(--line);border-radius:14px;padding:15px 17px 17px;box-shadow:0 18px 44px rgba(0,0,0,.5)}
h2{margin:0 0 11px;font-size:12px;color:var(--acc);letter-spacing:.7px}
pre{margin:0;white-space:pre-wrap;word-break:break-word;font-family:inherit;font-size:14.5px;line-height:2;text-align:right}
.c{background:#0e1b2b;border:1px solid var(--line);border-radius:5px;padding:0 6px;font-size:13px;color:#a8c6ea}
i{color:var(--dim)} b{color:#f0f6ff}
.tag{display:inline-block;border:1px solid var(--line);border-radius:20px;padding:1px 9px;color:var(--dim);font-size:11.5px;margin-inline-start:6px}"""


def main():
    secs = build()
    body = []
    for title, text in secs:
        t = html.escape(text or "").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
        t = re.sub(r"(<code>.*?</code>)", lambda m: f'<span class="c">{m.group(1)[6:-7]}</span>', t)
        body.append(f'<section><h2>{html.escape(title)}</h2><pre>{t}</pre></section>')
    doc = (f'<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8">\n'
           f'<meta name="viewport" content="width=device-width,initial-scale=1">\n'
           f'<title>فرماندۀ مانارچ — رابطِ بازسازی‌شده</title>\n<style>{CSS}</style>\n'
           f'<h1>🦖☢️ فرماندۀ مانارچ — رابطِ «پروندۀ محرمانه» · دروازۀ گروهی</h1>\n'
           f'<p class="sub">برداشتِ زنده از همان کدِ مخزن: کارتِ عامل با «گامِ بعد»، «جریانِ عملیات» و '
           f'«کارنامه» · پروندۀ تایتان · فیدِ فشردهٔ نبرد · تابلوی یورش با دکمه‌هایِ فارسیِ زنده · '
           f'منویِ خلوتِ چهارردیفی · دو کارتِ دروازہ (پیوی و گروهِ کم‌عضو) · و پرونده‌های آموزشِ کانال. '
           f'همۀ متن‌ها فارسی است و لاتین فقط در دستورهای اسلش و کدِ پرونده‌ها.<span class="tag">'
           f'{len(secs)} سطح</span><span class="tag">{len(TN.TITANS)} تایتان</span>'
           f'<span class="tag">{len(GATE.PV_ALLOW)} کلیدِ مجاز در پیوی</span></p>\n'
           f'<main>{"".join(body)}</main></html>\n')
    p = os.path.join(ROOT, "preview", "rebuilt-ui.html")
    with open(p, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"✓ نوشته شد: preview/rebuilt-ui.html · {len(secs)} سطح · {len(doc)} نویسه")


if __name__ == "__main__":
    main()
