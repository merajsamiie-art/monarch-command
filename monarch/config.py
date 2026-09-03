# ⚙️ MONARCH COMMAND — تنظیمات مرکزی (HARD MODE / پیشرفت بسیار سخت)
# همه‌ی اعداد بازی فقط از همین فایل خوانده می‌شوند؛ هیچ عددی در موتورّها پخش نیست.
import os


def _load_dotenv():
    """فایل .env کنار کد (بدون کتابخانه‌ی اضافه). فقط متغیرهای تعریف‌نشده را پر می‌کند."""
    for path in (os.path.join(os.path.dirname(__file__), ".env"),
                 os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")):
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
        except FileNotFoundError:
            pass


_load_dotenv()

# ─────────── اتصال ───────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
_FA = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def _ids(raw: str) -> set:
    out = set()
    for part in (raw or "").translate(_FA).split(","):
        d = "".join(c for c in part if c.isdigit())
        if d:
            out.add(int(d))
    return out


ADMIN_IDS = _ids(os.getenv("ADMIN_IDS", "8694290031"))
DB_PATH = os.getenv("MC_DB_PATH", os.path.join(os.path.dirname(__file__), "monarch.db"))
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
TZ_KEY = "Asia/Tehran"

# ─────────── کانال / گروه ───────────
CHANNEL_ID = int(os.getenv("CHANNEL_ID") or -1004499194759)
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/PLAYTIMEPROTOCOL")
GROUP_URL = os.getenv("GROUP_URL", "https://t.me/+BdlZ6aF4ai8xZjNk")
REQUIRE_CHANNEL = os.getenv("REQUIRE_CHANNEL", "1") == "1"   # گیت عضویت کانال
MEMBERSHIP_CACHE = 900                                       # کش عضویت ۱۵ دقیقه

BRAND = "MONARCH COMMAND"
TAGLINE = "🦖☢️ MONARCH COMMAND — The Titans Are Already Here."
BOT_USER = "MonarchCommandBot"
PREFIX = "مانارچ"          # پیشوند دستورات متنی فارسی («مانارچ من»)

# ─────────── شروع بازی ───────────
START_CREDITS = 250.0
START_HP = 120.0
START_ENERGY = 100.0
START_RESOLVE = 40.0

# ─────────── ranks ───────────
XP_BASE = 260
XP_STEP = 210
RANK_BONDS = dict(hp=18, energy=6, atk=1.6, df=1.2)

# ─────────── بازسازی ساعتی (lazy tick) ───────────
HP_REGEN_H = 9.0
ENERGY_REGEN_H = 22.0
RESOLVE_REGEN_H = 3.0
TICK_CAP_H = 6.0                 # سقف محاسبه‌ی آفلاین

# ─────────── مرگ و Drop ───────────
RECOVERY_MINUTES = 10            # ☠️ دقیقاً ۱۰ دقیقه Recovery Mode
DROP_CREDIT = 0.18               # سهم MC که می‌افتد
DROP_RESOURCE = 0.35             # سهم منابع قابل‌افت (Core/دیتا محافظت‌اند)
DROP_PROTECTED = ("cores",)      # 💎 Titan Core هرگز نمی‌افتد
INJURY_HP = 0.35                 # بعد از احیا، HP تا ۳۵٪

# ─────────── کول‌داون‌ها (ثانیه) ───────────
CD_GLOBAL = 2                    # ضداسپم پایه برای هر دستور
CD_TRACK = 25
CD_SAMPLE = 45
CD_ANALYZE = 120
CD_BOND = 180
CD_PUZZLE = 300
CD_HUNT = 90
CD_ARENA = 40
CD_SHOP = 12
CD_BOSS = 60
CD_RAID = 18                     # هر Strike در رید جهانی
CD_EXPED = 30
CD_DAILY = 3600
COMBAT_ACTION_CD = 5             # فاصله‌ی حداقلی بین دو اکشن در یک نبرد

# ─────────── مبارزه ───────────
DEF_K = 46.0                     # ثابت کاهش دفاع: dmg *= 1 - def/(def+K)
DMG_VAR = (0.86, 1.14)
CRIT_BASE = 0.06
CRIT_MULT = 1.75
GUARD_REDUCE = 0.55              # گارد ۵۵٪ آسیب را می‌گیرد
GUARD_BUILD = 12.0               # گارد → Charge
COUNTER_WINDOW = 1               # پس از گارد موفق، یک نوبت پنجره‌ی کانتر
COUNTER_MULT = 1.9
DODGE_CAP = 0.34
HEAVY_MULT = 1.85
HEAVY_CD = 2                     # نوبت
WEAK_BONUS = 1.30                # ضربه روی Weakness
ENV_HOME = 1.22                  # مزیت محیط خانگی
ENV_AWAY = 0.84                  # تنبیه محیط نامناسب
CHARGE_GAIN = 34.0
CHARGE_MAX = 100.0
ULT_CHARGE = 100.0
ECHO_DAMAGE_CAP = 2.4            # سقف ضربه‌ی اکس تایتان نسبت به خودِ بازیکن
FEED_EDIT_WINDOW = 600           # پنجره‌ی edit پیام نبرد
COMBAT_TIMEOUT = 900             # نبرد بی‌فعال بعد از ۱۵ دقیقه بسته می‌شود
MAX_FEED_LINES = 6               # کمپکت: همیشه حداکثر ۶ خط در نبرد

# ─────────── تحقیق و کشف (بسیار سخت) ───────────
# مرحله → امتیاز لازم برای عبور
RESEARCH_STAGES = [
    ("signal", "📡 سیگنال", 60),
    ("sighting", "👁 مشاهده", 150),
    ("sampled", "🧬 نمونه", 320),
    ("analyzed", "🔬 تحلیل", 620),
    ("bonded", "👑 پیوند", 1100),
]
LAB_MINUTES = 40                 # هر سیکل آزمایشگاه
LAB_FAIL = 0.18                  # شانس شکست سیکل (بسته به Facility)
PUZZLE_POINTS = 26
SAMPLE_INJURY = 0.22             # احتمال آسیب هنگام نمونه‌برداری میدانی

# ─────────── پیوند (Bond) ───────────
BOND_MAX = 5
BOND_POINT_REQ = (120, 320, 720, 1400, 2400)
BOND_HP = 0.06                   # هر تراز → ۶٪ HP بیشتر (برای اکس/پسیو)
BOND_ATK = 0.075
BOND_ECHO_DMG = 0.55             # آسیب اکس = ضریب × (power تایتان) × تراز پیوند

# ─────────── کاوش ───────────
EXPED_MIN = 9 * 60
EXPED_MAX = 40 * 60
EXPED_FAIL = 0.24
EXPED_RARE = 0.07

# ─────────── باس‌ها ───────────
BOSS_CHANCE = 0.30               # شانس زلزله → اسپاون باس در چت فعال
BOSS_CHECK = 1800
BOSS_DURATION = 45 * 60
BOSS_RAGE_AFTER = 30 * 60
RAID_DURATION = 3 * 3600
RAID_WEEKDAYS = (2, 5)           # سه‌شنبه و جمعه (۰=شنبه) — رید جهانی

# ─────────── اقتصاد ───────────
SELL_SPREAD = 0.12
BOUNTY_MIN = 200
VAULT_BASE = 4000
VAULT_PER_DIV_LEVEL = 2500
DAILY_MISSIONS = 3
CHECKIN = [40, 60, 90, 130, 190, 260, 400]
CHECKIN_XP = 14
MISSION_DAYS_RESET_UTC = 3       # ساعت ۰۳:۳۰ تهران (۰۰:۰۰ UTC)

# ─────────── آرنا ───────────
ARENA_K = 26
ARENA_DAILY = 6
ARENA_SEASON_DAYS = 7

# ─────────── Division ───────────
DIV_CREATE_COST = 24000
DIV_MAX_MEMBERS = 12
DIV_FAC_MAX = 6
DIV_FAC_BASE = 1800
DIV_FAC_STEP = 1.75
DIV_WAR_LANES = ("assault", "defense", "intel")
WAR_BONUS = 0.05

# ─────────── رویدادها ───────────
EVENT_INTERVAL = 900             #心跳 موتور رویداد (ثانیه)
GROUP_NEWS_HOURS = 4
TUTORIAL_HOUR = 17               # درس روزانه‌ی کانال (تهران)
RANK_DAY = 4                     # پنجشنبه: اعلام رنکینگ کانال
RANK_HOUR = 21
ALERT_COOLDOWN_CHAT = 5 * 3600

# ─────────── ضداسپم نسل ۲ ───────────
SPAM_WINDOW = 12
SPAM_MAX = 9
SPAM_PENALTY = 6
SPAM_PENALTY_MAX = 240
SPAM_DECAY = 1800

# ─────────── Pay-to-Win ───────────
# 🔒 هیچ آیتم پولی‌ای قدرت نمی‌خرد. پک‌های پشتیبانی فقط کیهانی/اداری‌اند.
SUPPORT_URL = os.getenv("SUPPORT_URL", "")
COSMETIC_ONLY = True


def is_admin(uid: int) -> bool:
    return int(uid) in ADMIN_IDS
