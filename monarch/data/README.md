# 📁 داده‌های بازی — توسعه بدون دست‌زدن به کد

| فایل / پوشه | نقش | چه‌کسی می‌خواندش |
|---|---|---|
| `titans.py` (بیرون از این پوشه) | **منبع اصلی** ۴۲ تایتان canon | موتور |
| `balance.json` | ضرایب کالیبره‌شده (hp_k/atk_k/smart/spam/ttk/pace) | `balance.py` |
| `kits.json` | پوششِ دستی Ability/Ultimate/Passive (نمونه: `kits.example.json`) | `kits.py` |
| `titans/*.json` | **اورلی**: افزودن تایتان تازه یا اصلاح فیلدها | `titans.load_overlays()` |

## افزودن تایتان تازه (۱ فایل، بدون کد)
1. `cp titans/_TEMPLATE.json.example titans/thingthus.json`
2. `id` یکتا، `name` واقعی/canon، `rar` از: `RECON · RARE · ELITE · LEGENDARY · ALPHA · OMEGA`
3. `ab` فقط شناسه‌هایAbility؛ اگر تعریفشان در `abilities.py` نباشد،
   `kits.py` از روی **معنای نامشان** می‌سازدشان (الگوهای: breath/claw/burrow/cryo/acid/roar/…)
4. ری‌استارت ربات (یا `/admin reload` برای ادمین) → `power` و لیست‌ها خودکار rebuild می‌شوند.

> ⚠️ فایلِ کهنه در این پوشه، کدِ تازه را **می‌پوشاند**. برای ساختِ عمدیِ فایل‌ها از
> `python3 tools/export_data.py --live` استفاده کن، نه کپی‌پیست دستی.

## بالانس دستی
- تغییر آمار/کیت/تجهیزات ⇒ `python3 tools/recalibrate.py --force` (سپس `--audit` باید `0`/problem بدهد).
- `balance.json` را **هرگز دستی** ویرایش نکن: امضای `_sig()` با آمارِ تایتان‌ها مقایسه می‌شود
  و در صورت عدم‌تطابق، ربات در حالت محافظه‌کارانه (بدون کش) اجرا می‌شود.
