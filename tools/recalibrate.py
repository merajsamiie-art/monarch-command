#!/usr/bin/env python3
"""⚖️ کالیبراسیون مجدد تعادل پس از هر تغییرِ آمار/تجهیزات/کیت.

    python3 tools/recalibrate.py            # فقط اگر امضای دیتا عوض شده باشد
    python3 tools/recalibrate.py --force    # اجباری (تغییر فرمول/ضرایب)
    python3 tools/recalibrate.py --audit    # فقط ممیزی (بدون بازنویسی)

خروجی: monarch/data/balance.json + گزارش ممیزی (هدف: problems = 0).
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import _path  # noqa: F401

import balance  # noqa: E402

if __name__ == "__main__":
    if "--audit" in sys.argv:
        r = balance.audit(trials=32)
        print(f"تعداد تایتان: {len(r['rows'])} · مشکل: {len(r['problems'])}")
        for p in r["problems"]:
            print("  ⚠️", p)
        sm = sorted(x["smart"] for x in r["rows"])
        print(f"  بردِ بازیکنِ باهوش: میانه {sm[len(sm)//2]:.2f} · کمینه {sm[0]:.2f} · بیشینه {sm[-1]:.2f}")
        sys.exit(1 if r["problems"] else 0)
    import economy  # noqa: F401  (تأمین‌کننده‌ی gear provider — بدون آن کالیبراسیون کور است)
    stats = balance.calibrate(force="--force" in sys.argv)
    print(f"کالیبره شد: {len(stats)} تایتان")
    r = balance.audit(trials=32)
    print(f"ممیزی: {len(r['problems'])} مشکل")
    for p in r["problems"]:
        print("  ⚠️", p)
    sys.exit(1 if r["problems"] else 0)
