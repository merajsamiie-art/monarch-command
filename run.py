#!/usr/bin/env python3
"""🦖☢️ MONARCH COMMAND — نقطه‌ی ورود ربات.

اجرای محلی:   python3 run.py
اجرای ۲۴/۷:  GitHub Actions (workflow bot.yml) — همان کاری که ریپوهای قبلی می‌کنند.
دیتابیس در `MC_DB_PATH` (پیش‌فرض: monarch.db کنار همین فایل) نگه داشته می‌شود
و ورک‌فلو هر ۶۰ ثانیه آن را به گیت کامیت می‌کند.
"""
import asyncio
import logging
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "monarch"))
os.environ.setdefault("MC_DB_PATH", os.path.join(ROOT, "monarch.db"))
os.environ.setdefault("PYTHONPATH", os.path.join(ROOT, "monarch"))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    import run
    try:
        asyncio.run(run.main())
    except KeyboardInterrupt:
        print("\n🛰 MONARCH: ایمن متوقف شد — دیتابیس ذخیره است.")
