# 🗒 TEXTS — لحن «پرونده‌ی محرمانه»؛ همه‌ی متن‌های بلند اینجا هستند
import config

START = """🛰 <b>MONARCH COMMAND</b>
<code>ACCESS GRANTED · CLEARANCE L0</code>
▬▬▬▬▬▬▬▬▬▬▬▬

👤 OPERATIVE: <b>{name}</b>
🎖 DESIGNATION: <b>MONARCH RECRUIT</b>

هیچ‌کس با Godzilla شروع نمی‌کند. هیچ‌کس.
تو یک انسان با یک هدف‌گیر و یک تیم پشتیبانی ضعیف هستی.

🧭 <b>مسیر خدمت:</b>
🛰 Recruit → 🔬 Researcher → 📡 Field Agent → ⚔️ Titan Specialist → 👑 Alpha Commander

📌 <b>اولین سه دستور:</b>
▪️ <code>/track</code> — سیگنال لرزه‌ای را بگیر (اولین قدم کشف)
▪️ <code>/explore</code> — تیم کاوش اعزام کن (۹ تا ۴۰ دقیقه)
▪️ <code>/codex</code> — دیتابیس تایتان‌ها (اکثریت <b>CLASSIFIED</b> است)

⚔️ <code>/fight</code> برای درگیری، <code>/boss</code> برای عملیات گروهی،
🌍 <code>/raid join</code> برای رید جهانی.

☠️ اگر بمیری: ۱۰ دقیقه Recovery Mode و بخشی از منابع قابل‌افت.
💎 Titan Core هرگز نمی‌افتد.

<i>🦖 THE TITANS ARE ALREADY HERE.</i>"""

HELP = """🛰 <b>MONARCH COMMAND — دستورنامه</b>
▬▬▬▬▬▬▬▬▬▬▬▬

<b>پرونده و پیشرفت</b>
/me — کارت عامل · /clearance — رتبه و الزامات
/codex — دیتابیس تایتان‌ها · /dossier &lt;titan&gt; — پرونده‌ی کامل
/top — رنکینگ · /missions — مأموریت روزانه · /daily — حضور روزانه

<b>کشف و تحقیق</b>
/track — سیگنال · /sample &lt;titan&gt; — نمونه‌برداری (ریسک آسیب)
/analyze &lt;titan&gt; — سیکل آزمایشگاه · /lab — نتیجه · /bond &lt;titan&gt; — پیوند
/bond up &lt;titan&gt; — ارتقای پیوند · /puzzle — رمزنگاری (امتیاز تحقیق)

<b>نبرد</b>
/hunt &lt;titan&gt; — شکار داوطلبانه · /fight — ادامه‌ی نبرد فعال
/boss — عملیات باس گروهی · /scan — وضعیت منطقه
/duel @agent — دوئل · /arena — آرنا رتبه‌ای

<b>جهان</b>
/explore — اعزام تیم کاوش · /explore report — وضعیت · /explore claim — تحویل
/raid join · /raid — رید جهانی · /zone — تغییر منطقه (ادمین)

<b>اقتصاد</b>
/shop · /inv · /equip &lt;id&gt; · /upgrade &lt;id&gt; · /market · /sell &lt;res&gt; &lt;qty&gt;
/vault &lt;amount&gt; — خزنه‌ی Division (محافظت در برابر Drop)
/bounty @agent &lt;MC&gt; — جایزه‌ی شکار

<b>سازمان</b>
/div create &lt;name&gt; &lt;tag&gt; · /div join &lt;code&gt; · /div fac &lt;key&gt;
/div war &lt;assault&gt; &lt;defense&gt; &lt;intel&gt; · /div top

⚙️ قوانین نبرد: /rules"""

RULES = """⚖️ <b>PROTOCOL — قوانین درگیری</b>
▬▬▬▬▬▬▬▬▬▬▬▬

۸ دکمه، یک میدان:
⚔️ Attack · 💥 Heavy · 🛡 Guard · ⚡ Dodge · 🎯 Counter
☄️ Ability · 🔋 Charge · 🏃 Retreat

🚫 <b>اسپم Attack برنده نمی‌شود.</b>
هر ضربه‌ی تکراری پشت‌سرهم → <b>Overextension</b> (کاهش آسیب تا −۳۰٪)
و تایتان‌های باهوش الگوی تکراری را «می‌خوانند» و جریمه می‌کنند.

🚫 <b>هیچ شخصیتی Auto-Win نیست</b> — نه Godzilla، نه King Ghidorah.
هر برد نیازمند آمادگی (نمونه/تحلیل)، محیط سازگار، نقطه‌ی ضعف و تیم است.
یک Rare با نقشه‌ی درست از یک Legendary رد می‌شود؛ یک Legendary با اسپم می‌میرد.

🛡 <b>گارد</b> ۵۵٪ آسیب را می‌گیرد، ☢️ شارژ می‌سازد و یک نوبت
پنجره‌ی <b>🎯 Counter</b> باز می‌کند (×۱٫۹ آسیب). این هسته‌ی بازی است.

☢️ <b>Charge → Overdrive/Ultimate.</b> اولتیمیت‌ها ۱۰۰٪ شارژ می‌خواهند،
هزینه‌ی انرژی سنگین و Cooldown بلند دارند. هیچ ability رایگان نیست.

🌍 <b>محیط واقعی است:</b> Titanosaurus در 🌊 اقیانوس ×۱٫۳۴،
در ❄️ جنوبگان تنبیه می‌گیرد. /hunt در منطقه‌ی سازگار، شکار است؛
در منطقه‌ی بیگانه، خودکشی.

❌ <b>Weakness</b> هر تایتان در /dossier هست. زدنِ نقطه‌ی ضعف ×۱٫۳ است.
🔋 انرژی تمام می‌شود؛ ضربه‌ی نصفه بهتر از بی‌ضربه است، اما شارژ را بساز.

🕹 <b>باس‌ها فاز و Rage دارند.</b> وقتی «INCOMING» آمد، اکشن بعدی‌ات
باید پاسخِ درست باشد (گارد/جاخالی/کانتر) — وگرنه ×۱٫۳ آسیب ویژه.

👑 <b>World Raid</b> یک استخر HP مشترک است و پنج شاخه‌ی جایزه:
Damage · Defense · Support · Last Hit · Research.
دنبال‌کردن فقط Damage، نیمی از جایزه را از دست می‌دهد."""

DEAD = """☠️ <b>AGENT DOWN</b>
<code>RECOVERY MODE</code>
▬▬▬▬▬▬▬▬▬▬▬▬

🫀 وضعیت بحرانی · واحد واکنش سریع در محل
⏳ {left} دقیقه تا <b>❤️ RESPAWN</b>

🩸 Drop:
{drop}

🛡 <b>محافظت‌شده:</b> Titan Core، تجهیزاتها و آیتم‌های Legendary.
<i>MONARCH هیچ‌کس را جا نمی‌گذارد. حتی جسدش را.</i>"""

NO_CLEARANCE = """🔒 <b>ACCESS DENIED — MONARCH GATE</b>

برای دسترسی به شبکه‌ی فرماندهی، عضویت در کانال لازم است:
📢 {channel}

بعد از عضویت، این دستور را بفرست:
<code>/start</code>"""

TITAN_CLASSIFIED = """📁 <b>MONARCH DATABASE</b>

☢️ <b>GODZILLA</b>
STATUS: <code>CLASSIFIED</code>

🐉 <b>UNKNOWN TITAN</b>
STATUS: <code>UNKNOWN</code>

<i>«آن‌ها از قبل اینجا بودند.»</i> — تو باید پیدایشان کنی:
📡 /track → 👁 /sample → 🔬 /analyze → 👑 /bond"""

WELCOME_GROUP = """🛰 <b>MONARCH COMMAND · ONLINE</b>
<code>{zone} SECTOR · THREAT LEVEL {danger}/5</code>

▪️ <code>/start</code> — ثبت‌نام عامل
▪️ <code>/boss</code> — شروع عملیات باس (تا ۵ نفر در یک نبرد)
▪️ <code>/hunt &lt;titan&gt;</code> — شکار داوطلبانه
▪️ <code>/raid</code> — رید جهانی
<i>پیام‌های نبرد در یک فید فشرده ویرایش می‌شوند — گروه شلوغ نمی‌شود.</i>"""

LESSONS = [
 dict(title="درس ۰۱ — کشف، نه فروشگاه",
      body="هیچ تایتانی از اول باز نیست. با <code>/track</code> سیگنال جمع کن،\n"
           "امضا را در <code>/dossier</code> بب و با /sample نمونه بگیر.\n"
           "هر مرحله از تحقیق، کلید مرحله‌ی بعد است."),
 dict(title="درس ۰۲ — گارد، نصف نیمی از برد است",
      body="گارد ۵۵٪ آسیب را می‌گیرد، ☢️ ۱۲٪ شارژ می‌سازد و پنجره‌ی\n"
           "🎯 Counter را باز می‌کند. کانتر ×۱٫۹ آسیب می‌زند.\n"
           "یک گاردِ به‌جا از پنج ضربه‌ی تصادفی ارزشمندتر است."),
 dict(title="درس ۰۳ — محیط را انتخاب کن",
      body="Rodan در 🌋 آتشفشان ×۱٫۳۶ است و در ❄️ جنوبگان قربانی.\n"
           "قبل از شکار، <code>/zone</code> و /dossier را بخوان.\n"
           "بسیاری از نبردها پیش از اولین ضربه تعیین می‌شوند."),
 dict(title="درس ۰۴ — Weakness را بزن",
      body="سردبیر MONARCH: نقطه‌ی ضعف هر تایتان در پرونده‌اش است.\n"
           "Sonics روی بلورها و گیاه‌ها، Light روی موجودات تاریکی،\n"
           "Ice روی موجودات آتشی. ضربه‌ی هم‌عنصر ×۱٫۳ آسیب می‌زند."),
 dict(title="درس ۰۵ — انرژی، منبع واقعی توست",
      body="HP را می‌توان ترمیم کرد؛ انرژیِ تمام‌شده یعنی ضربه‌ی نصفه.\n"
           "🔋 Charge هم شارژ هسته می‌دهد هم انرژی. دو نوبت Charge،\n"
           "یک اولتیمیت است."),
 dict(title="درس ۰۶ — مرگ بخشی از بازی است",
      body="☠️ ۱۰ دقیقه Recovery، افت اعتبار و منابعِ غیرمحافظت‌شده.\n"
           "🏦 خزنه‌ی Division (Storage) از Drop می‌کاهد.\n"
           "💎 Titan Core هرگز نمی‌افتد."),
 dict(title="درس ۰۷ — باس‌ها پاسخ می‌خواهند، نه کلیک",
      body="هر چند نوبت، پیام INCOMING می‌آید و یک «پاسخ لازم» دارد:\n"
           "گارد/جاخالی/کانتر. پاسخ درست = ۵٪ آسیب به باس + ۳۰٪ شارژ.\n"
           "پاسخ ندادن = ۱٫۳× آسیب ویژه."),
 dict(title="درس ۰۸ — پیوند تایتان",
      body="وقتی پرونده کامل شد، <code>/bond</code> تو را به اکسِ آن تایتان\n"
           "می‌رساند: مهارت امضایی در نبرد + مزیت آماری.\n"
           "تراز پیوند را با /bond up بالا ببر — گران، اما تعیین‌کننده."),
 dict(title="درس ۰۹ — Division",
      body="تسهیلات سازمان، عددِ خام تو را عوض می‌کند:\n"
           "📡 Radar → ردیابی سریع‌تر · 🔬 Lab → تحلیل ارزان‌تر\n"
           "📦 Storage → خزنه · 🛡 Defense → دفاع · ⚙️ Eng → کاوش سریع‌تر"),
 dict(title="درس ۱۰ — رید جهانی",
      body="سه‌شنبه/جمعه ۲۱:۰۰ تهران: یک استخر HP برای همه.\n"
           "پنج شاخه جایزه: Damage · Defense · Support · Last Hit · Research.\n"
           "اگر فقط ضربه بزنی، جایزه‌ات نصف است."),
 dict(title="درس ۱۱ — آنلاک Legendary",
      body="Godzilla با رتبه‌ی پایین باز نمی‌شود: 🎖 رتبه، 🧬 DNA،\n"
           "💎 Core، 📡 داده و ⚔️ پیروزی‌های پیاپی عليه همان تایتان.\n"
           "طراحی عمدتاً سخت است تا ارزشش را حفظ کند."),
 dict(title="درس ۱۲ — مأموریت روزانه",
      body="سه مأموریت در روز، هر روز ساعت ۰۳:۳۰ تهران تازه می‌شود.\n"
           "<code>/daily</code> برای حضور روزانه (استریک ۷ روزه).\n"
           "کمترین تلاشِ روزانه، بیشترین اثر هفتگی را دارد."),
]
