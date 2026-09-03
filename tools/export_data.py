#!/usr/bin/env python3
"""📦 خروجی‌گرفتن دیتای بازی برای ویرایشِ بی‌کد: data/titans/*.json و data/kits.json.

این فایل‌ها **منبعِ واقعیت نیستند** (منبع، کد پایتون است)؛ فقط پیش‌نمایشِ قابل‌ویرایش‌اند
تا با `titans.load_overlays()` روی دیتابیس سوار شوند (افزودن تایتان تازه / بالانس دستی).

    python3 tools/export_data.py --force      # بازنویسی کامل
    python3 tools/export_data.py --changed     # فقط فایل‌هایی که با کد فرق دارند
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: F401

import abilities as AB  # noqa: E402
import titans as TN  # noqa: E402

# ⚠️ پیش‌فرض در `dist/titans` نوشته می‌شود، نه در monarch/data/titans —
# چون آن پوشه توسط titans.load_overlays() به‌عنوان «پوششِ واقعی» خوانده می‌شود و
# فایلِ کهنه می‌تواند کد تازه را بپوشاند. برای اعمالِ عمدی: --live
TD = os.path.join(_path.ROOT, "dist", "titans")
KD = os.path.join(_path.ROOT, "monarch", "data")


def _dump(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--changed", action="store_true")
    ap.add_argument("--live", action="store_true",
                    help="نوشتن در monarch/data/titans/ (پوششِ واقعیِ دیتابیس)")
    ap.add_argument("--kit-overlay", action="store_true",
                    help="ساخت monarch/data/kits.example.json (نمونه‌ی پوششِ دستی)")
    a = ap.parse_args()
    global TD
    if a.live:
        TD = os.path.join(_path.ROOT, "monarch", "data", "titans")
    if a.kit_overlay:
        sample = {"atomic_breath": {"desc": "نسخه‌ی ویرایش‌شده‌ی دستی — همین‌جا بالانس کن.",
                                    "power": 2.05, "cost": 62.0, "cd": 4,
                                    "req": {"charge": 100}}}
        _dump(sample, os.path.join(KD, "kits.example.json"))
        print("monarch/data/kits.example.json نوشته شد")
        return 0
    os.makedirs(TD, exist_ok=True)
    n = 0
    for tid, t in sorted(TN.TITANS.items()):
        path = os.path.join(TD, f"{tid}.json")
        if os.path.exists(path) and not (a.force or a.changed):
            continue
        row = {k: v for k, v in t.items() if not k.startswith("_")}
        row["_abilities"] = {aid: {k: v for k, v in (AB.ABILITIES.get(aid) or {}).items()}
                             for aid in list(row.get("ab") or []) + [row.get("ult")] if aid}
        row["_passive"] = AB.PASSIVES.get(row.get("pas"))
        if a.changed and os.path.exists(path):
            old = json.load(open(path, encoding="utf-8"))
            if old == row:
                continue
        _dump(row, path)
        n += 1
    print(f"{n} فایل در {os.path.relpath(TD, _path.ROOT)}/ · منبع اصلی: monarch/titans.py")
    if not a.live:
        print("برای اعمال روی بازی: --live (سپس ری‌استارت ربات)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
