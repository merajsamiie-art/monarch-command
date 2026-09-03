# 🦖☢️ MONARCH COMMAND — The Titans Are Already Here.

ربات **نوردی/استراتژیک گروهی تلگرام** به‌سبک **پرونده‌های طبقه‌بندی‌شده‌ی MONARCH**.
یک دنیای زنده‌ی ۲۴/۷: تایتان‌ها تا کشف‌نشده «CLASSIFIED/UNKNOWN» می‌مانند، پیشرفت
سخت و بلندمدت است، و هیچ شخصیتی — حتی Godzilla — دکمه‌ی بردِ خودکار ندارد.

> 📌 این ریپو **خصوصی** است و ربات روی **GitHub Actions** به‌عنوان سرور رایگان اجرا می‌شود
> (الگوی ربات‌های قبلی: هر job ~۵٫۵ ساعت، هر ۱۰ دقیقه یک job جدید، و **ذخیره‌ی خودکار
> دیتابیس در گیت هر ۶۰ ثانیه**).

---

## 🚀 اجرای محلی

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # BOT_TOKEN را وارد کن
python3 run.py                # 🛰 MONARCH ONLINE
```

دیتابیس: `monarch.db` (کنار `run.py`) — مسیر با `MC_DB_PATH` عوض می‌شود.
ساختار جداول + ستون‌های جدید به‌صورت خودکار مهاجرت می‌کند (`db._migrate`).

## 🚪 دروازۀ بازی (بازی فقط در گروه)

* **پیوی**: هیچ دستوری از بازی اجرا نمی‌شود؛ ربات فقط کارتِ «من را به گروه اضافه کن»
  را می‌فرستد (با دکمۀ افزودن به گروه + لینکِ گروه و کانال). منوی اسلشِ پیوی هم
  فقط سه مورد است: `/start` · `/help` · `/join`.
* **گروه**: باید بیش از ۴ عضو داشته باشد (`MIN_MEMBERS=5`). گروه خلوت نبرد
  نمی‌بیند و ربات هم برای «نشدن» بیشتر از یک پیام در ۱۵ دقیقه نمی‌فرستد.
* **گروهِ اصلی**: بدونِ هیچ سقفي فعال است — یا `GROUP_ID` را در تنظیمات
  Actions بگذار، یا داخلِ خودِ گروه (توسط فرمانده) `/setmain` را بفرست.
  اگر خودِ فرمانده ربات را به گروهی اضافه کند، آن گروه خودکار اصلی می‌شود.
  با `/setmain off` هم می‌شود از فهرست بیرونش آورد (در دیتابیس می‌ماند).

```
vars: GROUP_ID = -100XXXXXXXXXX      # اختیاری
vars: MIN_MEMBERS = 5                # اختیاری
```

## 📢 آموزش‌ها در کانال

سریِ «پروندۀ آموزشی مانارچ» از متن‌های خودِ بازی ساخته می‌شود (۱۲ درس +
پروتکلِ نبرد + دیتابیسمُعرّفی + پرسش‌های مکرر + دستورنامۀ کامل = ۱۷ پرونده):

```
BOT_TOKEN=… python3 tools/post_channel.py --dry-run     # پیش‌نمایش
BOT_TOKEN=… python3 tools/post_channel.py --pin          # انتشار + پینِ پروندۀ ۰۰۰
```

وضعیتِ انتشار در `monarch/data/channel_posts.json` می‌ماند؛ اجرای دوباره
فقط پرونده‌های نو می‌فرستد (`--force` برای انتشارِ کاملِ دوباره).

## 🌐 استقرار ۲۴/۷ روی GitHub Actions

1. ریپوی خصوصی بساز (مثلاً `مرحله: monarch-command`).
2. در **Settings → Secrets and variables → Actions** این‌ها را ست کن:

| Secret | مقدار |
|---|---|
| `BOT_TOKEN` | توکن ربات از @BotFather |
| `ADMIN_IDS` | `8694290031` (با کاما جدا کن) |
| `CHANNEL_ID` | `-1004499194759` (اید منفی کانال) |
| `CHANNEL_URL` | `https://t.me/PLAYTIMEPROTOCOL` |
| `GROUP_URL` | لینک دعوت گروه |

3. `.github/workflows/bot.yml` فعال است: هر ۱۰ دقیقه یک job، `timeout-minutes: 350`،
   با trap روی EXIT تا اگر job وسط کار کشته شد هم دیتابیس کامیت شود.
4. بات را **ادمین گروه و کانال** کن (پیام/ویرایش/حذف پیام + عکس، برای فید فشرده‌ی نبرد
   و یکسان‌سازی هویت). بدون ادمین بودنِ کانال، گیتِ عضویت و پست‌های کانال کار نمی‌کند.
5. `keepalive.yml` هر دوشنبه یک کامیت خالی می‌زند تا GitHub cron را بعد از ۶۰ روز خاموش نکند.

⚠️ اگر توکنی جایی (چت/لاگ) رد و بدل شده، بعد از استقرار در @BotFather **rotate** کن.

## 🪪 یکسان‌سازی هویت (بات + گروه + کانال)

```bash
python3 tools/setup_bot_ui.py                 # منوی /commands، بیو، توضیح
python3 tools/setup_bot_ui.py --photos        # + عکس پروفایل بات (assets/bot_avatar.jpg)
python3 tools/setup_bot_ui.py --group -100… --channel -100… --photos
```

## 🕹 دستورات (۳۷ تا — همه با mirror فارسی)

`/start /me /clearance /rules /help /codex /track /dossier /hunt /boss /raid /arena /duel
/explore /shop /inv /equip /use /upgrade /sell /market /missions /daily /top /div /scan
/bounty /report /join /profile /wiki /faq /news /bond /gear /feed /admin /recal`

فارسی هم کار می‌کند: «مانارچ من»، «مانارچ رنکینگ»، «مانارچ راهنما» … (پیشوند: `مانارچ`).

## ⚔️ چیزی که بازی را «عمیق» نگه می‌دارد

* **۱۰ آمار + Weakness** برای هر تایتان؛ محیط (اقیانوس/شهر/آتشفشان/جنوبگان/جنگل/زمین توخالی/منطقه‌ی هسته‌ای/ فضا) ضربات را جابه‌جا می‌کند.
* کیت هر تایتان: **۱ Passive + ۲–۴ Ability + ۱ Ultimate** — اولتیمیت انرژی‌ی ≥۴۴، Cooldown ≥۳ و شرط شارژ/HP می‌خواهد (`kits.py` هر کیتِ تعریف‌نشده را از روی الگوی رفتاریِ نامش می‌سازد؛ `monarch/data/kits.json` پوششِ دستی است).
* **۸ اکشن نبرد**: Attack / Heavy / Guard / Dodge / Counter / Ability / Charge / Retreat — لایه‌ی بالا ساده، لایه‌ی پایین (ضد‌ضربه، بافرها، وضعیت‌ها، شارژ) پیچیده.
* **مرگ**: ☠️ AGENT DOWN + Recovery ۱۰ دقیقه، افت منابع (آیتم‌های افسانه‌ی پیوندخورده محافظت می‌شوند)، سپس Respawn.
* **باس‌ها**: Normal/Elite/Legendary/Alpha/World با Phase، Rage Mode، رفتار AI و حمله‌ی ویژه؛ رید جهانی ۵ جایزه می‌دهد: Most Damage / Best Defense / Best Support / Last Hit / Best Research.
* **پژوهش**: قیفِ ۵ مرحله‌ای (سیگنال → مشاهده → نمونه → تحلیل → پیوند) با هزینه‌ی Samples/Data/Credits و کشتارِ هدفمند. Godzilla هفته‌ها دور است.
* **تقسیم‌ها (Division)**: Radar/Laboratory/Storage/Defense/Engineering + Tracking/Expedition/Raid/Division War — جنگ‌ها با **تخصیص سه‌لاینه** (assault/defense/intel = ۱۰۰٪) برنده می‌شوند، نه با کلیک‌کردن.
* **اقتصاد بدون P2W**: 🪙 Monarch Credit / ✨ Titan Core / 🧬 DNA / 🔋 Cell / 🔩 Material / 📡 Data. فروشِ رتبه، ریسک تایتان یا قدرتِ پولی در کاتالوگ نیست (`test_15` این را قفل می‌کند).
* **ضداسپم**: پنجره‌ی ۱۲ ثانیه / ۹ درخواست + جریمه‌ی پلکانی، **فیلترِ بی‌صدا** برای سیل دستورات (یک هشدار در ۹۰ دقیقه، بقیه دور ریخته می‌شود)، و ویرایشِ پیامِ نبرد به‌جای ارسال پیام جدید.

## ⚖️ قرارداد تعادل

`balance.py` ضرایب هر تایتان را با **شبیه‌سازیِ موتور واقعی** حل می‌کند (`resolve_strike`،
محیط، وضعیت‌ها، فشار Ability دو طرف) و `monarch/data/balance.json` را می‌سازد.
اهدافِ اندازه‌گیری‌شده (کشف‌شده، نه فرضی):

| قرارداد | سقف |
|---|---|
| بردِ بازیکنِ باهوش در رنکِ مجاز | ۰٫۴۵–۰٫۹۳ (هیچ‌وقت ۱۰۰٪) |
| بردِ اسپم (spam) | ≤ ۰٫۳۴ |
| بازیکنِ پایین‌تر از گیت (ELITE+) | ≤ ۰٫۶۶ |
| فاصله‌ی مهارت (باهوش − اسپم) | ≥ ۰٫۲۲ |

```bash
python3 tools/recalibrate.py --force    # بعد از هر تغییر آمار/کیت/تجهیزات
python3 tools/recalibrate.py --audit    # باید «۰ مشکل» بدهد
```

## 🧪 تست‌ها

```bash
python3 tests/test_game.py     # 25/25 · include: هرج‌ومرج دیتا، تعادل، ضداسپم، هندلرها، هویت ایموجی
```

پوشش: مهاجرت دیتابیس، کشِ تعادل، canon بودن تایتان‌ها (نام ساختگی ممنوع)، نبودِ auto-win،
قیف پژوهش، رفت‌و‌برگشت نبرد زنده، سقف نرخ، مرگ/Recovery، کاوش، چرخه‌ی باس، رید جهانی،
سهمیه‌ی آرنا (فقط Elo، بدون خرید)، تسهیلات و جنگ تقسیم، اقتصادِ بدونِ P2W، فروشگاه/بازار/ارتقا/فروش،
مأموریت‌های روزانه و سقف پیوند، تمیزیِ متن‌ها، قفل‌های UI، بی‌صداییِ سیکل‌های رویداد،
کامل‌بودن هندلرها، **دودِ واقعی aiogram** (Update → فیلتر → هندلر → Transport ساختگی)،
گیتِ عضویت کانال، یکپارچگی رجیستری ایموجی، ماندگاری داده پس از ری‌استارت.

## 🗂 چیدمان

```
run.py                     نقطه‌ی ورود
requirements.txt
monarch/
  config.py                تمام ضرایب/سقف‌ها/دوره‌ها
  emoji.py                 رجیستری مرکزی ایموجی (+ <tg-emoji> اگر پشتیبانی شود)
  db.py                    sqlite + کش + مهاجرت خودکار
  titans.py abilities.py kits.py   ۴۲ تایتان canon · ۲۱۱ Ability · کیت‌ساز خودکار
  balance.py               کالیبراسیون/ممیزی (contract بالا)
  player.py ui.py texts.py kb.py   پروفایل، رندر، متن‌ها، شیشه‌ای‌ها
  combat.py bosses.py raid.py arena.py   نبرد زنده، باس، رید جهانی، آرنا
  economy.py research.py expedition.py division.py events.py   چرخه‌ی بازی
  handlers.py run.py admin.py      لایه‌ی تلگرام و حلقه‌ی رویدادها
  data/                    balance.json · kits.json · titans/*.json (اورلی)
tools/                     recalibrate · export_data · setup_bot_ui
tests/test_game.py
.github/workflows/         bot.yml (۲۴/۷ + autosave) · keepalive.yml
```

## 🔐 نکات امنیتی

* `.env` و `*.db` محلی در `.gitignore` هستند؛ **تنها** دیتابیسِ سرور در ریپو کامیت می‌شود (چون خود ریپو خصوصی است و همین مکانیزمِ بکاپِ ماست).
* برای ریپوی عمومی‌شونده، `MC_DB_PATH` را به فضای ذخیره‌سازی خارجی ببر و بخش «کامیت دیتابیس» را از workflow حذف کن.
* توکن بات و PAT گیت‌هاب را در چت نگه ندار؛ بعد از استقرار rotate کن.
