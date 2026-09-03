#!/usr/bin/env python3
"""🖼 کارت تصویری تایتان‌ها — واردکردن/سازگارکردن تصویر (تمیز، یک‌دست، سبک).

    # از فایلِ دانلودشده (مثلاً چیزی که از Pinterest ذخیره کرده‌ای):
    python3 tools/pin_import.py godzilla --file ~/Downloads/godzilla.jpg
    # یا مستقیم از URLِ تصویر (i.pinimg.com و مشابه آن):
    python3 tools/pin_import.py kong --url https://i.pinimg.com/originals/xx/yy.jpg
    # دسته‌ای: هر خط = «tid url» (خط‌های # رد می‌شوند)
    python3 tools/pin_import.py --from-manifest monarch/data/titan_photos.txt
    # چه‌کسی تصویر ندارد؟
    python3 tools/pin_import.py --list-missing
    # فقط بررسی/گزارش
    python3 tools/pin_import.py --report

خروجی: monarch/assets/titans/<tid>.jpg  (JPEG، پهنای ≤۹۰۰، نسبت ۴:۳ برش‌خورده، q=82)
قوانین: نام فایل = idِ تایتان در titans.py (بزرگ/کوچک مهم نیست)؛ اگر تایتان در دیتابیس
نباشد هشدار می‌دهد و ذخیره نمی‌کند — تا «نام ساختگی» وارد بازی نشود.
"""
import argparse
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: F401

import titans as TN  # noqa: E402

OUT = os.path.join(_path.ROOT, "monarch", "assets", "titans")
MANIFEST = os.path.join(_path.ROOT, "monarch", "data", "titan_photos.json")
MAX_W, QUALITY = 900, 82


def normalize(raw: bytes, tid: str) -> tuple:
    """برش ۴:۳ مرکزی + کوچک‌سازی + JPEG — تا کارت‌ها هم‌اندازه و سبک بمانند."""
    from PIL import Image, ImageOps
    try:
        im = Image.open(io.BytesIO(raw))
        im = ImageOps.exif_transpose(im).convert("RGB")
    except Exception as e:
        return 0, f"تصویر خوانده نشد ({str(e)[:60]})"
    w, h = im.size
    if w < 380 or h < 285:
        return 0, f"رزولوشن کم است ({w}×{h}) — تصویر تمیزِ بزرگ‌تر لازم است"
    tw, th = (w, int(round(w * 3 / 4)))
    if h > th:      # برشِ ارتفاع از مرکزِ کمی بالاتر (صورت/تنِ تایتان معمولاً آنجاست)
        top = int((h - th) * 0.42)
        im = im.crop((0, top, w, top + th))
    elif h < th:    # کم‌آوری پهنا
        left = int((w - int(h * 4 / 3)) / 2)
        im = im.crop((left, 0, left + int(h * 4 / 3), h))
    if im.width > MAX_W:
        im = im.resize((MAX_W, int(MAX_W * 3 / 4)), Image.LANCZOS)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{tid}.jpg")
    im.save(path, "JPEG", quality=QUALITY, optimize=True, progressive=True)
    return os.path.getsize(path), path


def fetch(url: str) -> bytes:
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)",
                                               "Referer": "https://.pinterest.com/"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read()


def _tid(arg: str) -> str:
    t = TN.get(str(arg).strip().lower())
    return (t or {}).get("id") or ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("titan", nargs="?")
    ap.add_argument("--file")
    ap.add_argument("--url")
    ap.add_argument("--from-manifest")
    ap.add_argument("--list-missing", action="store_true")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()

    have = {os.path.splitext(f)[0] for f in os.listdir(OUT)} if os.path.isdir(OUT) else set()
    if a.report or a.list_missing:
        missing = [t["id"] for t in TN.TITANS.values() if t["id"] not in have]
        print(f"🖼 {len(have)}/{len(TN.TITANS)} تایتان تصویر دارد.")
        if missing:
            print("بی‌تصویر (" + str(len(missing)) + "): " + " ".join(missing))
        return 0

    if a.from_manifest:
        done = fail = 0
        for line in open(a.from_manifest, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or len(line.split()) < 2:
                continue
            tid, url = line.split()[:2]
            tid = _tid(tid)
            if not tid:
                print(f"  ⚠️ نام شناخته‌شده نیست: {line.split()[0]}"); fail += 1; continue
            try:
                size, path = normalize(fetch(url), tid)
            except Exception as e:
                print(f"  ⚠️ {tid}: {str(e)[:90]}"); fail += 1; continue
            if size:
                print(f"  ✔ {tid}: {size // 1024} KB → {os.path.relpath(path, _path.ROOT)}"); done += 1
            else:
                print(f"  ⚠️ {tid}: {path}"); fail += 1
        print(f"✅ {done} کارت ساخته شد · ⚠️ {fail} خطا")
        return 0 if done else 1

    if not (a.titan and (a.file or a.url)):
        ap.print_help()
        return 2
    tid = _tid(a.titan)
    if not tid:
        print(f"❌ «{a.titan}» در titans.py نیست — فقط نام‌های canon مجاز است.")
        return 1
    raw = open(a.file, "rb").read() if a.file else fetch(a.url)
    size, path = normalize(raw, tid)
    if not size:
        print(f"❌ {path}")
        return 1
    print(f"✔ {path} ({size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
