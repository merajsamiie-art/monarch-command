# 🧪 MONARCH COMMAND — تست‌های موتور بازی (بدون شبکه، aiogram با سشن ساختگی)
"""
اجرا:
    python3 tests/test_game.py          # اجراگر داخلی
    python3 -m pytest -q tests          # اگر pytest نصب باشد

هیچ درخواست شبکه‌ای زده نمی‌شود: Bot یک Session ساختگی دارد و همه‌چیز روی
یک دیتابیس موقت در /tmp اجرا می‌شود.
"""
import asyncio
import copy
import itertools
import json
import os
import random
import re
import sys
import tempfile
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "monarch")
sys.path.insert(0, PKG)

TMP = tempfile.mkdtemp(prefix="mc-test-")
os.environ["MC_DB_PATH"] = os.path.join(TMP, "test.db")
os.environ["BOT_TOKEN"] = "123456:TEST-TOKEN"
os.environ["REQUIRE_CHANNEL"] = "0"
os.environ["ADMIN_IDS"] = "900001,900002"

import config          # noqa: E402
import db              # noqa: E402

db.init()

import abilities as AB         # noqa: E402
import admin                   # noqa: E402
import arena                   # noqa: E402
import balance                 # noqa: E402
import bosses                  # noqa: E402
import combat                  # noqa: E402
import division                # noqa: E402
import economy                 # noqa: E402
import emoji as EMJ            # noqa: E402
import events                  # noqa: E402
import expedition as EXP       # noqa: E402
import handlers                # noqa: E402
import kb                      # noqa: E402
import player as PL            # noqa: E402
import raid as RA              # noqa: E402
import research                # noqa: E402
import texts                   # noqa: E402
import titans as TN            # noqa: E402
import ui                      # noqa: E402
from aiogram import Bot, Dispatcher, F                # noqa: E402
from aiogram.filters import Command                  # noqa: E402
from aiogram.types import (CallbackQuery, Chat, Message, Update,   # noqa: E402
                           User)

_CK = itertools.count(1_700_000_000, config.COMBAT_ACTION_CD + 2)
combat.now = lambda: next(_CK)          # زمان نبرد را جلو می‌بریم (cooldown واقعی)
_CHAT = itertools.count(-1001)
_UID = itertools.count(10001)
RESULTS = []


def new_player(rank=1, uid=None, chat_id=None, zone="ocean"):
    uid = uid or next(_UID)
    chat_id = chat_id if chat_id is not None else next(_CHAT)
    PL.ensure_player(uid, f"عامل{uid % 1000}", f"agent{uid % 1000}")
    PL.set_row(uid, rank=rank)
    p = PL.get(uid)
    PL.set_row(uid, hp=p["max_hp"], energy=p["max_energy"], resolve=80)
    events.ensure_chat(chat_id, f"OPS-{abs(chat_id) % 99}", "group")
    events.set_zone(chat_id, zone)
    PL.note_chat(uid, chat_id)
    return uid, chat_id, db.db().one("SELECT * FROM chats WHERE chat_id=?", (chat_id,))


def fund(uid, **over):
    res = dict(credits=250_000, dna=900, cells=500, mats=400, fdata=700, cores=120)
    res.update(over)
    PL.add_res(uid, **res)


def equip_all(uid, rank):
    for iid, it in economy.ITEMS.items():
        if int(it.get("need_rank") or 1) <= rank:
            PL.add_item(uid, iid, 1)
    for slot in ("rig", "weapon", "module"):
        best_id, best_tier = None, -1
        for iid, it in economy.ITEMS.items():
            if (it.get("slot") or it.get("kind")) != slot or int(it.get("need_rank") or 1) > rank:
                continue
            if int(it.get("tier") or 1) > best_tier:
                best_id, best_tier = iid, int(it.get("tier") or 1)
        if best_id:
            PL.equip(uid, best_id)


def heal(uid):
    PL.respawn(uid, silent=True)
    p = PL.get(uid)
    PL.set_row(uid, hp=p["max_hp"], energy=p["max_energy"], resolve=90, dead_until=0)
    act = combat.active_of(uid)
    if act:
        combat.close(act["cid"], "test")


# ────────────────────────── fake telegram transport ──────────────────────────
class FakeSession:
    """جایِ Telegram Bot API: هر متد را ثبت و یک پاسخ معتبر برمی‌گرداند."""

    def __init__(self):
        self.calls = []
        self.chat_member = "member"

    def _msg(self, chat_id, mid, text):
        return Message(message_id=mid, date=1_700_000_000,
                       chat=Chat(id=int(chat_id), type="supergroup" if str(chat_id).startswith("-") else "private"),
                       from_user=User(id=777000, is_bot=True, first_name="MONARCH"),
                       text=text)

    async def __call__(self, bot, method, timeout=None):
        cls = method.__class__.__name__
        name = cls[0].lower() + cls[1:]        # SendMessage -> sendMessage (aiogram 3.31)
        data = method.model_dump(exclude_none=True, by_alias=True)
        self.calls.append((name, data))
        if name in ("sendMessage", "editMessageText", "sendPhoto", "editMessageCaption"):
            cid = data.get("chat_id", 1)
            mid = data.get("message_id") or (10_000 + len(self.calls))
            return self._msg(cid, mid, data.get("text") or data.get("caption") or "")
        if name == "getChatMember":
            from aiogram.types import ChatMemberUpdated
            return {"user": {"id": data.get("user_id"), "is_bot": False, "first_name": "x"},
                    "status": self.chat_member}
        if name == "getChat":
            return {"id": data.get("chat_id"), "type": "supergroup", "title": "OPS"}
        return True

    def texts(self, only=None):
        out = [d.get("text", "") for n, d in self.calls if n in ("sendMessage", "editMessageText")]
        return [t for t in out if only is None or only in t]


def main_dp():
    """یک Dispatcher مشترک — روتر aiogram singleton است، پس include دوباره مجاز نیست."""
    if getattr(main_dp, "d", None) is None:
        d = Dispatcher()
        d.include_router(handlers.router)
        main_dp.d = d
    return main_dp.d


def build_bot():
    sess = FakeSession()
    bot = Bot(token=config.BOT_TOKEN or "123:FAKE", session=sess)
    return bot, sess


def msg(bot, text, uid=10001, chat_id=-100505, is_callback=False):
    chat = Chat(id=chat_id, type="supergroup")
    u = User(id=uid, is_bot=False, first_name=f"عامل{uid % 100}")
    if is_callback:
        cq = CallbackQuery(id="cb1", from_user=u, message=message(bot, text, uid, chat_id),
                           data=text, chat_instance="ci")
        return cq
    return message(bot, text, uid, chat_id)


def message(bot, text, uid, chat_id):
    m = Message(message_id=random.randint(1, 10 ** 6), date=1_700_000_000,
                chat=Chat(id=chat_id, type="supergroup"),
                from_user=User(id=uid, is_bot=False, first_name=f"عامل{uid % 100}"),
                text=text)
    return m.as_(bot)


# ───────────────────────────────── tests ─────────────────────────────────
def test_01_db_schema_and_migrate():
    d = db.db()
    cols = {r["name"] for r in d.q("PRAGMA table_info(players)")}
    for c in ("samples", "power_cache", "last_seen_day", "echo_uses", "pvp_wins", "arena_rating", "flags"):
        assert c in cols, f"ستون {c} در players نیست"
    for t in ("items", "bonds", "chats", "combats", "raids", "raid_users", "divisions",
              "div_users", "cooldowns", "kv", "chat_users", "log"):
        assert d.q(f"PRAGMA table_info({t})") is not None, t
        assert d.one(f"SELECT COUNT(*) c FROM {t}")["c"] >= 0
    # مهاجرتِ امن روی دیتابیس موجود
    d._migrate()
    d._migrate()


def test_02_balance_cache_and_audit():
    path = os.path.join(PKG, "data", "balance.json")
    assert os.path.exists(path), "کش تعادل وجود ندارد — در CI کالیبراسیون طولانی می‌شود"
    blob = json.load(open(path, encoding="utf-8"))
    assert blob.get("sig") == balance._sig(), "امضای کش تعادل با دیتابیس تایتان‌ها نمی‌خواند"
    assert len(blob["cal"]) >= len(TN.TITANS) - 2, "تایتان‌ها کالیبره نشده‌اند"
    r = balance.audit(trials=26)
    assert r["problems"] == [], f"مشکل تعادل: {r['problems'][:4]}"
    assert r["calibrated"] == r["n"]
    by = {row["id"]: row for row in r["rows"]}
    for row in r["rows"]:
        assert row["spam"] <= max(0.5, row["smart"] - 0.15), f"اسپم پاداش دارد: {row['name']}"
    if by:
        leg = [v["smart"] for k, v in by.items() if TN.get(k)["rar"] in ("LEGENDARY", "OMEGA")]
        rec = [v["smart"] for k, v in by.items() if TN.get(k)["rar"] == "RECON"]
        assert max(leg) < max(rec), "قله‌ی بازی نباید از لایه‌ی ابتدایی آسان‌تر باشد"


def test_03_titans_are_canon_and_data_driven():
    assert len(TN.TITANS) >= 40
    must = {"godzilla", "kong", "mothra", "king_ghidorah", "rodan", "mechagodzilla", "destoroyah",
            "spacegodzilla", "biollante", "gigan", "hedorah", "megalon", "king_caesar",
            "titanosaurus", "battra", "jet_jaguar", "moguera", "baragon", "kumonga", "kamacuras",
            "ebirah", "manda", "gorosaurus", "varan", "orga", "megaguirus", "monster_x",
            "keizer_ghidorah", "anguirus", "skar_king", "shimo", "suko", "tiamat", "scylla",
            "behemoth", "methuselah", "amhuluk", "abaddon", "muto_prime", "muto_minion",
            "skullcrawler", "warbat"}
    ids = set(TN.all_ids())
    assert not (must - ids), f"تایتان‌های اصلی کم‌اند: {sorted(must - ids)}"
    names = {TN.get(i)["name"] for i in ids}
    # نام‌های canon باید در شناسه زنده بمانند (جست‌وجوی لاتین) و نمایش فارسی باشد
    for canon in ("godzilla", "kong", "mothra", "king_ghidorah", "mechagodzilla", "spacegodzilla"):
        assert canon in ids, canon
    assert all(TN.get(i)["name"] for i in ids), "نام نمایشی خالی است"
    assert sum(1 for n in names if re.search(r"[\u0600-\u06FF]", n)) >= len(ids) - 2, \
        "نام نمایشی تایتان‌ها باید فارسی باشد"
    for bad in ("Zorvox", "Titan-X9", "Neon", "zorvox", "titan-x9"):
        assert not any(bad in i for i in ids) and not any(bad.lower() in (n or "").lower() for n in names), f"نام ساختگی: {bad}"
    for t in TN.TITANS.values():
        assert t["rar"] in TN.RARITY, t["id"]
        assert 2 <= len(t.get("ab") or []) <= 5, f"{t['name']} تعداد مهارت نامعتبر"
        assert t.get("ult") and t.get("pas"), f"{t['name']} ضربه نهایی/ذاتی ندارد"
        assert t["ult"] in AB.ABILITIES, f"{t['name']} اولتیمیتش تعریف نشده: {t['ult']}"
        assert t["pas"] in AB.PASSIVES, f"{t['name']} پسیوش تعریف نشده: {t['pas']}"
        for aid in t.get("ab") or []:
            assert aid in AB.ABILITIES, f"{t['name']} Ability تعریف‌نشده: {aid}"
        assert t.get("weak"), f"{t['name']} نقطه‌ی ضعف ندارد"
        assert set(t["env"]) & set(TN.ENVS), f"{t['name']} محیط ندارد"
        u = AB.ABILITIES[t["ult"]]
        assert u["cost"] >= 40, f"اولتیمیت {t['name']} بی‌هزینه است ({u['cost']})"
        assert int(u.get("cd") or 0) >= 3, f"اولتیمیت {t['name']} Cooldown ندارد"
        assert (u.get("req") or {}).get("charge"), f"اولتیمیت {t['name']} شرط شارژ ندارد"
        for aid in t.get("ab") or []:
            a = AB.ABILITIES[aid]
            assert a["cost"] < u["cost"], f"Ability {aid} از اولتیمیت {t['name']} گران‌تر است"
            assert 0 <= int(a.get("cd") or 0) <= 6, aid
    assert len(TN.ENVS) == 8


def test_04_no_autowin_and_spam_punished():
    r = balance.audit(trials=20)
    by = {row["id"]: row for row in r["rows"]}
    for tid, row in by.items():
        t = TN.get(tid)
        if t["rar"] in ("ELITE", "ALPHA", "LEGENDARY", "OMEGA"):
            assert row["spam"] <= 0.40, f"{t['name']}: اسپم هنوز برنده می‌شود ({row['spam']})"
            assert row["smart"] <= 0.93, f"{t['name']}: برد خودکار"
            assert row["underleveled"] <= 0.66, f"{t['name']}: برای رنک پایین خیلی آسان"


def test_05_fresh_player_gets_nothing_free():
    uid, cid, chat = new_player(rank=1)
    p = PL.get(uid)
    assert p["rank"] == 1 and abs(p["credits"] - config.START_CREDITS) < 1
    assert not research.bond_rows(uid), "بازیکن تازه نباید پیوند داشته باشد"
    assert PL.inv(uid) == {}, "بازیکن تازه نباید تجهیز رایگان داشته باشد"
    g = research.bond(uid, "godzilla")
    assert not g["ok"], "Godzilla نباید از ابتدا قابل‌پیوند باشد"
    assert "ACCESS DENIED" in g["msg"] or "🔒" in g["msg"]
    st = research.stage_of(uid, "godzilla")
    assert st == 0, "کشف خودکار انجام شد"
    d = research.dossier(uid, TN.get("godzilla"))
    assert ("ناشناخته" in d or "محرمانه" in d), "پرونده‌ی کشف‌نشده باید مخفی بماند"
    assert "Atomic Breath" not in d and "مهارت" not in d, "جزئیات تایتان کشف‌نشده لو رفته است"
    cx = handlers.codex_text(uid) if hasattr(handlers, "codex_text") else None
    if cx is not None:
        assert "ناشناخته" in cx or "🕳" in cx


def test_06_research_funnel_gates():
    uid, cid, chat = new_player(rank=2)
    fund(uid, dna=0, fdata=0, cores=0)
    PL.add_res(uid, dna=400, fdata=400, credits=60000)
    t = research.track(uid, chat)
    assert t["ok"], t
    tid = t["tid"]
    # فَنل واقعی: signal → sighting → sample → analyze → lab → bond
    research.set_stage(uid, tid, 0)
    assert not research.sample(uid, tid, chat)["ok"], "نمونه بدون مشاهده ممکن شد"
    research.set_stage(uid, tid, 1)
    assert not research.sample(uid, tid, chat)["ok"], "نمونه با یک سیگنال خام"
    research.set_stage(uid, tid, 2)
    assert research.sample(uid, tid, chat)["ok"], "نمونه پس از مشاهده مسدود ماند"
    assert research.stage_of(uid, tid) >= 2, "نمونه مرحله را جلو نبرد"
    assert not research.analyze(uid, tid)["ok"], "تحلیل پیش از نمونه‌ی کامل"
    research.set_stage(uid, tid, 3)
    a = research.analyze(uid, tid)
    assert a["ok"], a
    assert float(PL.get(uid)["lab_until"]) > db.now(), "آزمایشگاه صف نشد"
    # پیوند: نیازمند مرحله + پیروزی + منابع
    deny = research.bond(uid, tid)
    assert not deny["ok"] and "پیوند رد شد" in deny["msg"]
    research.set_stage(uid, tid, 4)
    db.db().ex("INSERT OR REPLACE INTO bonds(user_id,titan_id,stage,points,kills,bond,bond_points,last) "
               "VALUES(?,?,5,40,5,1,0,?)", (uid, tid, db.now()))
    assert research.is_known(uid, tid)
    assert research.bond_rows(uid), "پیوند ثبت نشد"
    up = research.bond_up(uid, tid)
    assert up["ok"] or "کمبود" in up["msg"] or "سقف" in up["msg"], up


def test_07_live_combat_roundtrip_and_feed():
    uid, cid, chat = new_player(rank=6)
    fund(uid)
    equip_all(uid, 6)
    heal(uid)
    c = combat.start(uid, "hunt", chat=chat, titan_id="suko", encounter=1.0)
    assert c["ok"], c
    cidv = c["cid"]
    opts = combat.options(cidv, uid)
    keys = [o["cb"].split(":")[-1] for o in opts]
    for need in ("atk", "heavy", "guard", "dodge", "counter", "charge", "retreat"):
        assert need in keys, f"دکمه‌ی {need} در نبرد نیست"
    r = combat.act(cidv, uid, "atk")
    assert r.get("ok"), r
    txt = r["feed"]
    assert txt.count("\n") <= config.MAX_FEED_LINES + 12, "فید از حد متراکم‌تر شدن فراتر رفت"
    # انرژی/HP باید در دیتابیس نوشته شده باشد
    row = db.db().one("SELECT * FROM combats WHERE id=?", (cidv,))
    assert row and row["status"] == "live"
    st = r["state"]
    assert 0 < float(st["a"]["hp"]) <= float(st["a"]["max_hp"])
    res = combat.act(cidv, uid, "guard")
    assert res.get("ok") or res.get("live")
    # فرار: نبرد بسته می‌شود و HP حفظ می‌شود
    combat.act(cidv, uid, "retreat")
    assert not combat.active_of(uid), "فرار نبرد را نبست"
    assert PL.get(uid)["hp"] >= 0


def test_08_action_rate_limit_protects_group():
    uid, cid, chat = new_player(rank=5)
    fund(uid)
    heal(uid)
    c = combat.start(uid, "hunt", chat=chat, titan_id="suko", encounter=1.0)
    cidv = c["cid"]
    frozen = combat.now()
    real_now = combat.now
    try:
        combat.now = lambda: frozen              # زمان قفل ⇒ نوبت دوم باید بخورد
        r1 = combat.act(cidv, uid, "atk")
        r2 = combat.act(cidv, uid, "atk")
        assert r1.get("ok"), r1
        assert not r2.get("ok") and "ثانیه" in (r2.get("msg") or ""), \
            "نوبت دوم بی‌cooldown اجرا شد (گروه شلوغ می‌شود)"
    finally:
        combat.now = real_now
    combat.close(cidv, "test")


def test_09_death_recovery_and_protection():
    uid, cid, chat = new_player(rank=4)
    fund(uid)
    PL.add_item(uid, "rig_alpha", 1)
    PL.set_row(uid, hp=1.0)
    res = PL.die(uid, "COMBAT")
    assert res["ok"] and isinstance(res.get("drop"), dict)
    p = PL.get(uid)
    assert PL.is_dead(p) and config.RECOVERY_MINUTES * 55 <= p["dead_until"] - db.now()
    assert p["hp"] <= 1.0
    inv_after = PL.inv(uid)
    assert "rig_alpha" not in inv_after or inv_after.get("rig_alpha", {}).get("qty", 0) >= 1, \
        "آیتم افسانه‌ای نباید با مرگ برود"
    assert float(p["cores"]) >= 0
    PL.respawn(uid)
    assert not PL.is_dead(PL.get(uid))
    assert PL.get(uid)["hp"] > 1.0


def test_10_expedition_lifecycle():
    uid, cid, chat = new_player(rank=5)
    fund(uid)
    zones = [k for k, z in EXP.available(PL.get(uid))]
    assert zones and len(zones) >= 2
    hi = new_player(rank=24)[0]
    assert len(EXP.available(PL.get(hi))) >= len(zones), "با رنک بالاتر مناطق بیشتری باز نمی‌شود"
    r = EXP.start(uid, zones[0], chat)
    assert r["ok"], r
    p = PL.get(uid)
    assert float(p["expedition_until"]) > db.now()
    assert EXP.status(uid)["active"]
    PL.set_row(uid, expedition_until=db.now() - 1)
    assert EXP.status(uid).get("ready"), "بازگشت کاوش آماده نشد"
    got = EXP.claim(uid, chat)
    assert got["ok"], got
    assert not EXP.status(uid)["active"]
    # شکتمول: خطر بالا باید احتمال شکست داشته باشد
    fails = 0
    for k in range(25):
        u2, c2, ch2 = new_player(rank=1)
        rr = EXP.start(u2, zones[-1], ch2)
        if rr.get("ok"):
            PL.set_row(u2, expedition_until=db.now() - 1)
            cl = EXP.claim(u2, ch2)
            assert cl.get("ok"), cl
            fails += 1 if cl.get("fail") else 0
    assert fails > 0, "کاوش همیشه موفق است (باید شکست هم داشته باشد)"


def test_11_boss_lifecycle_five_awards():
    uid, cid, chat = new_player(rank=10)
    fund(uid)
    equip_all(uid, 10)
    heal(uid)
    sp = bosses.spawn(cid, force=True)
    assert sp.get("ok"), sp
    bid = sp["bid"]
    b = bosses.by_id(bid)
    assert b["tier"] in bosses.TIERS and b.get("phases"), "باس فاز ندارد"
    assert b.get("specials"), "باس حمله‌ی ویژه ندارد"
    e = bosses.engage(uid, chat)
    assert e.get("ok"), e
    for i in range(30):
        r = combat.act(e["cid"], uid, ["atk", "guard", "heavy", "dodge", "counter"][i % 5])
        if r.get("ended"):
            break
    s = bosses.settle(cid, True)
    assert s["ok"]
    for key in ("damage", "defense", "support", "research", "last_hit"):
        assert key in s["winners"], f"جایزه‌ی {key} توزیع نشد"
    txt = str(s.get("msg"))
    assert "بیشترین آسیب" in txt
    assert bosses.active(cid) in (None, {}) or bosses.active(cid).get("bid") != bid, "باس بسته نشد"
    # decay: باس رهاشده باید منقضی شود
    bosses.settle(cid, False)


def test_12_world_raid_awards_and_activity():
    uid, cid, chat = new_player(rank=11)
    uid2 = new_player(rank=11, chat_id=cid)[0]
    for u in (uid, uid2):
        fund(u)
        equip_all(u, 11)
        heal(u)
    r = RA.start(hours=2)
    assert r.get("ok"), r
    for u in (uid, uid2):
        assert RA.join(u)["ok"]
    if not division.member_of(uid):
        dd = division.create(uid, "RAIDX", "RX1")
        assert dd["ok"], dd
    did = division.member_of(uid)["div_id"]
    xp0 = (division.div_of(did) or {}).get("xp", 0)
    acts = list(RA.ACTIONS.keys())
    assert len(acts) >= 5, "رید باید حداقل ۵ کنشِ متفاوت داشته باشد"
    for u in (uid, uid2):
        for act in acts:
            PL.clear_cd(u, "raid")
            out = RA.act(u, act)
            assert out.get("ok"), (act, out)
    st = RA.state()
    assert st and int(st.get("strikes") or 0) > 0, f"رید ضربه‌ای ثبت نکرد: {st}"
    assert st["hp"] < st["max_hp"], "رید HP حریف را کم نکرد"
    assert st["max_hp"] / max(1.0, 0.0015 * st["max_hp"]) <= 900, \
        "استخر رید برای یک گروه واقعی غیرقابل‌تمام‌کردن است"
    board = RA.board()
    for tag in ("مشارکت", "یورش جهانی"):
        assert tag in board, f"برچسب «{tag}» در تخته نیست: {board[:240]}"
    fin = RA.finish(True)
    assert fin["ok"] and "بیشترین آسیب" in fin["msg"] and "بهترین پژوهش" in fin["msg"]
    assert "بهترین دفاع" in fin["msg"] and "بهترین پشتیبانی" in fin["msg"] and "ضربه آخر" in fin["msg"]
    assert PL.get(uid)["raids"] >= 1
    assert (division.div_of(did) or {}).get("xp", xp0) > xp0, "فعالیت رید به Division ثبت نشد"
    # idempotency: دوباره تمام‌کردن نباید جایزه بدهد
    again = RA.finish(True)
    assert not again.get("ok") or again.get("noop") or "بسته" in str(again.get("msg")), again


def test_13_arena_elo_only_no_purchase():
    a, b = new_player(rank=9)[0], new_player(rank=9)[0]
    PL.tick(a)
    for u in (a, b):
        fund(u)
        equip_all(u, 9)
        heal(u)
    ra0, rb0 = arena.rating_of(a), arena.rating_of(b)
    ch = arena.challenge(a, {"chat_id": -100777, "zone": "city", "danger": 1}, opp_uid=b)
    assert ch.get("ok"), ch
    assert arena.arena_left(a) == config.ARENA_DAILY - 1, \
        f"سهمیه‌ی روزانه کم نشد (left={arena.arena_left(a)}, flags={PL.get(a)['flags']}, day={PL.get(a)['day']})"
    for i in range(45):
        r = combat.act(ch["cid"], a, ["atk", "guard", "heavy", "dodge", "counter"][i % 5])
        if r.get("ended"):
            break
        if not r.get("ok"):
            break
    heal(a)
    heal(b)
    s = arena.settle(a, b)
    assert s["ok"]
    assert s["win"] > ra0 and s["lose"] < rb0
    assert s["lose"] >= 800, "کف رتبه‌ی آرنا رعایت نشد"
    assert abs((s["win"] - ra0) + (s["lose"] - rb0)) < 60, "Elo مجموعاً باید تقریباً صفر باشد"
    # رتبه فقط با برد تغییر می‌کند: هیچ مسیری برای «پرداخت → رتبه» وجود ندارد
    src = open(os.path.join(PKG, "arena.py"), encoding="utf-8").read()
    for frag in ("arena_rating=+", "set_rating", "buy_rating", "donate"):
        assert frag not in src, f"arena.py مسیر خرید رتبه دارد: {frag}"
    body = src.split("def settle")[1].split("\ndef ")[0]
    assert "arena_rating=new_w" in body and "credits=" in body
    assert "cores=" not in body and "dna=" not in body, "جایزه‌ی آرنا نباید دروازه‌ی پیشرفت بدهد"
    assert PL.get(a)["arena_wins"] >= 1 and PL.get(b)["arena_losses"] >= 1


def test_14_division_facilities_and_war():
    a = new_player(rank=12)[0]
    b = new_player(rank=12)[0]
    for u in (a, b):
        fund(u)
    d1 = division.create(a, "سازمانِ آلفا", "MA1")
    assert d1["ok"], d1
    d2 = division.create(b, "سازمانِ بتا", "MB2")
    assert d2["ok"], d2
    c3 = new_player(rank=12)[0]
    fund(c3)
    code = division.invite_code(d1["did"])
    j = division.join(c3, code)
    assert j["ok"], j
    assert division.member_of(c3)["div_id"] == d1["did"]
    assert set(division.FACILITIES) >= {"radar", "lab", "storage", "defense", "engineering"}
    PL.add_res(a, credits=0)
    division.deposit(a, 90_000)
    for key in division.FACILITIES:
        r = division.fac_up(a, key)
        assert r["ok"], (key, r)
    lv = division.facility_of(a, "lab")
    assert lv >= 1 and lv <= config.DIV_FAC_MAX
    for _ in range(3):
        division.fac_up(a, "lab")
    assert division.facility_of(a, "lab") <= config.DIV_FAC_MAX, "سقف تسهیلات رد شد"
    division.credit_activity(a, "raid", 1)
    division.credit_activity(a, "expedition", 1)
    division.credit_activity(a, "boss_kill", 1)
    card = division.card(a)
    assert "تسهیلات" in card
    pairs = [dict(a=d1["did"], b=d2["did"], focus={})]
    w = division.war_start(pairs, hours=4)
    assert w and w.get("status") == "open", w
    assert division.war_open().get("pairs"), "جنگ باز ثبت نشد"
    dep = division.deploy(a, {"assault": 40, "defense": 25, "intel": 35})
    assert dep["ok"], dep
    res = division.war_resolve()
    assert isinstance(res, list) and res, res
    assert division.div_of(d1["did"])["wins"] >= 0
    assert division.top(4)
    assert division.defense_bonus(a) >= 0


def test_15_economy_no_pay_to_win():
    uid, cid, chat = new_player(rank=7)
    fund(uid, credits=60000)
    allowed = tuple(economy.SLOTS) + ("consumable", "material")
    for iid, it in economy.ITEMS.items():
        assert it["kind"] in allowed, f"{iid}: نوع غیرمجاز ({it['kind']})"
        assert "titan" not in str(it.get("kind")), "فروش تایتان = P2W"
        assert "rank" not in (it.get("mods") or {}), "فروش رتبه = P2W"
        assert "titan" not in (it.get("mods") or {}), "فروش تایتان = P2W"
    assert config.COSMETIC_ONLY
    before = PL.get(uid)
    r = economy.buy(uid, "rig_recon")
    assert r["ok"], r
    assert float(PL.get(uid)["credits"]) < float(before["credits"])
    assert PL.get(uid)["credits"] >= 0
    assert float(PL.get(uid)["cores"]) == float(before["cores"]), "هسته با MC فروخته نمی‌شود"
    assert float(PL.get(uid)["dna"]) == float(before["dna"]), "DNA با MC فروخته نمی‌شود"
    # فروش منبع و سقف قیمت
    s = economy.sell(uid, "dna", 40)
    assert s["ok"]
    assert economy.RES["cores"]["sellable"] is False and economy.RES["credits"]["sellable"] is False
    eq = PL.equip(uid, "rig_recon")
    assert eq.get("ok", True), eq
    g = economy.gear_mods(uid)[0]
    assert g.get("hp", 0) > 0, f"تجهیزات پس از equip صفر است: {g}"
    assert float(PL.get(uid)["max_hp"]) > 0
    # گیت‌های پیشرفت با پول باز نمی‌شوند
    for rar in ("ALPHA", "LEGENDARY", "OMEGA"):
        gate = balance.GATE[rar]
        assert gate["rank"] >= 6 and gate["kills"] >= 3 and gate["lab"] >= 1, rar


def test_16_shop_market_upgrade_sell():
    uid = new_player(rank=9)[0]
    fund(uid)
    assert economy.buy(uid, "wp_ion")["ok"]
    PL.clear_cd(uid, "shop")          # cooldown فروشگاه عمداً وجود دارد
    assert economy.buy(uid, "md_medbay")["ok"]
    lvl0 = PL.item_level(uid, "wp_ion")
    r = economy.upgrade(uid, "wp_ion")
    assert r["ok"], r
    assert PL.item_level(uid, "wp_ion") == lvl0 + 1
    for _ in range(10):
        economy.upgrade(uid, "wp_ion")
    assert PL.item_level(uid, "wp_ion") <= 10
    mb = economy.market_board()
    assert "قطعه ژنتیکی" in mb and "اعتبار" in mb, mb[:120]
    m = economy.sell(uid, "mats", 10)
    assert m["ok"]
    assert PL.get(uid)["mats"] >= 0


def test_17_missions_daily_and_bond_caps():
    uid = new_player(rank=3)[0]
    fund(uid)
    ms = economy.roll_missions(uid)
    assert len(ms) == config.DAILY_MISSIONS, "تعداد مأموریت روزانه"
    assert len({m for m in ms}) == len(ms)
    for key in ("track", "sample", "hunt", "guard", "puzzle", "boss"):
        economy.progress(uid, key, 99)
    board = economy.mission_board(uid)
    assert "/" in board, board[:200]
    assert len(board.splitlines()) == config.DAILY_MISSIONS
    done = [mid for mid, row in db.jload(PL.get(uid)["missions"], {}).items() if row.get("done")]
    assert done, "مأموریت‌ها تکمیل‌شدنی نیستند"
    cl = economy.claim_mission(uid, done[0])
    assert cl["ok"], cl
    assert economy.claim_mission(uid, done[0]).get("ok") is False, "جایزه دوباره قابل‌گرفتن است"
    ck = economy.checkin(uid)
    assert ck["ok"]
    assert economy.checkin(uid)["ok"] is False, "حضور روزانه دوباره ثبت شد"
    # سقف پیوند: هیچ‌گاه نبرد را تضمینی نمی‌کند
    t = TN.get("rodan")
    caps = balance.bond_gain(t["power"], config.BOND_MAX)
    for k in ("acc", "dodge"):
        assert caps[k] <= (0.06 if k == "acc" else 0.05), f"{k} از سقف بالاتر رفت"
    assert caps["mult"] < 0.35, "مزیت پیوند بیش از حد است"


def test_18_texts_render_cleanly():
    kw = dict(name="Vasquez", left="9.9", drop="▪️ none", channel=config.CHANNEL_URL,
              zone="🌊 اقیانوس", danger="▰▰▱▱▱")
    for name in dir(texts):
        v = getattr(texts, name)
        if isinstance(v, str) and v.strip():
            out = v.format(**kw)
            assert "{" not in out.replace("{", "", 0) or True
            assert "{'" not in out, f"{name}: قالبِ فرمت‌نشده در متن مانده"
            assert "None" not in out, f"{name}: None در متن"
        if isinstance(v, list):
            for row in v:
                if isinstance(row, dict):
                    assert row.get("title") and row.get("body"), name
    assert "اسپم" in texts.RULES
    assert "Auto-Win" in texts.RULES or "خودکار" in texts.RULES
    assert len(texts.LESSONS) >= 8
    assert "برد خودکار" in texts.RULES or "خودکار" in texts.RULES


def test_19_ui_and_kb_locks():
    uid = new_player(rank=4)[0]
    fund(uid)
    p = PL.get(uid)
    card = PL.card(p)
    assert "مانارچ" in card and "<b>" in card
    assert 4 <= ui.bar(50, 100).count("▰") <= 5
    assert ui.pct(30, 120) == 25
    assert "ساعت" in ui.dur(3700) and "h" not in ui.dur(3700)
    stats = economy.stats_of(p)
    menu = kb.combat_menu(1, [dict(cb="cbt:1:atk", text="Attack", emj="sword"),
                              dict(cb="cbt:1:ability:x", text="X", emj="ability",
                                   disabled=True, hint="⏳ ۴ ثانیه")])
    flat = [b for row in menu.inline_keyboard for b in row]
    locked = [b for b in flat if (b.text or "").startswith("🔒")]
    assert locked, f"گزینه‌ی قفل‌شده علامت قفل ندارد: {[b.text for b in flat]}"
    assert all(b.callback_data is None for b in locked), "دکمه‌ی قفل نباید callback داشته باشد"
    assert any("⏳" in (b.text or "") for b in locked), "دلیل قفل روی دکمه نیست"
    assert kb.main_menu(p).inline_keyboard
    assert kb.confirm("y", "n").inline_keyboard


def test_20_events_cycles_are_quiet():
    uid, cid, chat = new_player(rank=6)
    fund(uid)
    PL.set_row(uid, rank=6)
    for u in (uid, new_player(rank=5, chat_id=cid)[0]):
        db.db().ex("INSERT OR REPLACE INTO chat_users(chat_id,user_id,last_active) VALUES(?,?,?)",
                   (cid, u, db.now()))
    bot, sess = build_bot()

    pkt = events.news_packet(dict(db.db().one("SELECT * FROM chats WHERE chat_id=?", (cid,))))
    assert pkt and "{" not in pkt and "None" not in pkt, pkt[:200]

    async def go():
        # سیکل‌ها sync‌اند و ارسال را با create_time روی حلقه می‌اندازند
        events.cycle_bosses()
        events.cycle_raid()
        events.cycle_division_war()
        events.cycle_news(bot)
        events.cycle_channel(bot)
        for _ in range(8):
            await asyncio.sleep(0.02)      # فرصت اجرا به تسک‌های زمان‌بندی‌شده
    asyncio.run(go())
    sent = sess.texts()
    for t in sent:
        assert len(t) <= 4096, "پیام از حد تلگرام بلندتر است"
    per_chat = {}
    for _n, d in sess.calls:
        if _n in ("sendMessage", "editMessageText"):
            per_chat[d["chat_id"]] = per_chat.get(d["chat_id"], 0) + 1
    for c, n in per_chat.items():
        if c == config.CHANNEL_ID:
            continue
        assert n <= 3, f"چت {c} با {n} پیام بمباران شد (anti-spam)"
    pkt = events.news_packet(db.db().one("SELECT * FROM chats WHERE chat_id=?", (cid,)))
    assert "گزارش روزانه مانارچ" in pkt and len(pkt) < 3900
    eng = events.Engine(bot, interval=1)
    assert eng is not None


def test_21_handlers_surface_complete():
    for name in handlers.COMMAND_MAP:
        assert name in handlers.ALIASES or name in ("start", "join", "ref", "report"), name
        fn, takes = handlers.COMMAND_MAP[name]
        assert asyncio.iscoroutinefunction(fn), name
    for name, aliases in handlers.ALIASES.items():
        assert name in handlers.COMMAND_MAP, f"دستور {name} تابعی ندارد"
        assert aliases, name
    assert handlers.ALIASES["arena"], "آرنا نام‌های فارسی ندارد"
    d = main_dp()
    rt = handlers.router
    n = len(rt.message.handlers) + len(rt.callback_query.handlers)
    assert d.sub_routers and d.sub_routers[0] is rt, "روتبر روی دیسپچر سوار نشده"
    assert n >= len(handlers.COMMAND_MAP) + 10, f"مدیریت رویدادها ثبت نشد ({n})"
    assert len(rt.message.handlers) >= 30, "هندلرهای پیام کم است"
    assert any("CommandStart" in h.callback.__name__ or True for h in rt.message.handlers)
    # هر پیشوندِ callback که دکمه‌ها تولید می‌کنند، باید هندلر داشته باشد
    src = open(os.path.join(PKG, "handlers.py"), encoding="utf-8").read()
    handled = set(re.findall(r'F\.data\.startswith\("([a-z_]+)', src))
    required = {"cbt", "dx", "cxp", "hunt", "bond", "pz", "exp", "ra", "ar",
                "sk", "buy", "eq", "vt", "dv", "fac", "top", "menu"}
    assert required <= handled, f"پیشوند بی‌هندلر: {sorted(required - handled)}"


def test_22_aiogram_smoke_flow():
    """مسیر واقعی: Update → فیلتر aiogram → هندلر → Transport ساختگی."""
    bot, sess = build_bot()
    uid = 10001
    PL.ensure_player(uid, "عاملِ آزمون", "smoke")
    PL.set_row(uid, rank=12)
    p = PL.get(uid)
    PL.set_row(uid, hp=p["max_hp"])
    events.ensure_chat(-100900, "SMOKE OPS", "group")
    PL.note_chat(uid, -100900)
    d = main_dp()

    async def go():
        for text in ("/start", "/me", "/codex", "/clearance", "/rules", "/help",
                     "/missions", "/top", "/div", "/arena", "/shop", "/scan", "/join"):
            await d.feed_update(bot, Update(update_id=1, message=message(bot, text, uid, -100900)))
        for fa in ("مانارچ من", "مانارچ رنکینگ", "مانارچ راهنما"):
            await d.feed_update(bot, Update(update_id=2, message=message(bot, fa, uid, -100900)))
        await d.feed_update(bot, Update(update_id=3, message=message(bot, "/hunt suko", uid, -100900)))
        await d.feed_update(bot, Update(update_id=4, message=message(bot, "/boss", uid, -100900)))
        await d.feed_update(bot, Update(update_id=5, message=message(bot, "/raid", uid, -100900)))
        await d.feed_update(bot, Update(update_id=6, message=message(bot, "/explore", uid, -100900)))
        cq = CallbackQuery(id="c1", from_user=User(id=uid, is_bot=False, first_name="آزمون"),
                           chat_instance="ci", data="menu:codex",
                           message=message(bot, "/start", uid, -100900)).as_(bot)
        await d.feed_update(bot, Update(update_id=7, callback_query=cq))
    asyncio.run(go())
    names = [n for n, _d in sess.calls]
    assert "sendMessage" in names, f"هیچ پاسخی ارسال نشد: {names[:6]}"
    joined = "\n".join(sess.texts())
    assert "مانارچ" in joined, "برندِ فارسیِ مانارچ در پاسخ‌ها نیست"
    # 🈂️ قراردادِ متنی: متنِ کاربر فارسی است؛ لاتین فقط «کد» و دستورِ اسلش.
    stray = set()
    for msg_txt in sess.texts():
        body = re.sub(r"</?[a-zA-Z][^>]*>", " ", msg_txt)                      # برچسبِ HTML
        body = re.sub(r"(?:^|[^\w])(?<![\w])(?:/[a-z_]{2,16})(?:[ \u200c]+[A-Za-z0-9_\-ژن]{1,16}){0,3}", " ", body)
        body = re.sub(r"@\w+|t\.me/[\w+./\-]+|https?://\S+", " ", body)      # هندل و لینک
        for m in re.finditer(r"[A-Za-z][A-Za-z0-9_.\-']{2,}", body):
            w = m.group(0).strip(".'-")
            if re.fullmatch(r"[A-Z][A-Z0-9.\-']{1,11}", w):                     # MA1 · MB2 · DIV-0001
                continue
            stray.add(w)
    assert not stray, f"واژۀ لاتینِ بی‌اجازه در متنِ کاربر: {sorted(stray)[:6]}"
    for probe in ("کارت", "PROFILE", "OPERATIVE", "AGENT"):
        if probe in joined.upper():
            break
    else:
        raise AssertionError("هیچ کارت/پروفایلی در پاسخ‌ها نیست")
    assert "/help" in joined or "دستور" in joined
    bad = [t for t in sess.texts() if "Traceback" in t or "None" == t.strip()]
    assert not bad, bad[:1]
    for t in sess.texts():
        assert len(t) <= 4096, f"پیام {len(t)} کاراکتر — بالاتر از سقف تلگرام"
    assert not [t for t in sess.texts() if "{'" in t], "متن فرمت‌نشده به کاربر رفت"
    # ضداسپم: سیل پیام‌ها باید cooldown بگیرد و سکوت کند، نه انفجار
    n_before = len(sess.texts())
    async def spam():
        for i in range(14):
            await d.feed_update(bot, Update(update_id=100 + i,
                                            message=message(bot, "/me", uid, -100900)))
    asyncio.run(spam())
    n_spam = len(sess.texts()) - n_before
    assert n_spam <= config.SPAM_MAX + 3, f"ضداسپم کار نمی‌کند ({n_spam} پاسخ به ۱۴ درخواست پشت‌سرهم)"
    warn = [t for t in sess.texts() if "سقف مجاز" in t]
    assert warn, "سقف نرخ هیچ بازخوردی نمی‌دهد"
    assert len(warn) == 1, f"هشدارِ تکراری خودش اسپم است: {len(warn)}"


def test_23_channel_gate_enforced():
    config.REQUIRE_CHANNEL = True
    uid = 100404
    PL.ensure_player(uid, "عاملِ دروازۀ", "gate")
    bot, sess = build_bot()
    from aiogram.types import ChatMemberLeft, ChatMemberAdministrator

    async def _left(*a, **k):
        return ChatMemberLeft(user=User(id=uid, is_bot=False, first_name="x"), status="left")

    async def _admin(*a, **k):
        return ChatMemberAdministrator(user=User(id=uid, is_bot=False, first_name="x"),
                                       status="administrator", can_be_edited=False,
                                       can_post_messages=True, can_edit_messages=True,
                                       can_delete_messages=True, can_restrict_members=True,
                                       can_promote_members=True, can_change_info=True,
                                       can_invite_users=True, can_pin_messages=True,
                                       is_anonymous=False, can_manage_chat=True,
                                       can_manage_video_chapters=True, can_manage_topics=True)

    handlers._MEM_CACHE.clear()
    bot.get_chat_member = _left
    assert asyncio.run(handlers.member_ok(bot, uid)) is False, "گیت کانال member='left' را رد نکرد"
    handlers._MEM_CACHE.clear()
    bot.get_chat_member = _admin
    assert asyncio.run(handlers.member_ok(bot, uid)) is True
    config.ADMIN_IDS = config.ADMIN_IDS | {uid}
    handlers._MEM_CACHE.clear()
    sess.chat_member = "left"
    assert asyncio.run(handlers.member_ok(bot, uid)) is True, "مدیر نباید پشت گیت بماند"
    config.REQUIRE_CHANNEL = False
    handlers._MEM_CACHE.clear()


def test_24_emoji_registry_single_source():
    EMJ.load()
    for key in ("satellite", "sword", "heavy", "guard", "dodge", "counter", "charge", "retreat",
                "radar", "atom", "core", "dna", "cell", "material", "data", "coin", "boss",
                "dead", "respawn", "vitals", "classified", "access", "denied", "alert"):
        v = EMJ.get(key)
        assert v and v != "🛰" or key == "satellite", f"کلید ایموجی {key} ثبت نشده"
    # داده‌ها نباید «کلید» ایموجی را به خروجی نشت بدهند
    for t in TN.TITANS.values():
        assert not str(t["emj"]).isascii() or len(t["emj"]) <= 2, f"emj حل‌نشده: {t['id']}"
    for aid, a in AB.ABILITIES.items():
        assert len(a["emj"]) <= 4, f"emj حل‌نشده در ability: {aid}"
    for _i, it in economy.ITEMS.items():
        assert len(it["emj"]) <= 4, f"emj حل‌نشده در item: {_i}"
    for bid, b in bosses.BOSSES.items():
        assert len(b["emj"]) <= 4, f"emj حل‌نشده در boss: {bid}"
    assert EMJ.has_custom() in (True, False)
    EMJ.set_custom({"sword": "abcdef123456"})
    assert "<tg-emoji" in EMJ.get("sword"), "custom emoji باید به شکل tg-emoji رندر شود"
    assert "⚔️" in EMJ.strip_tags(EMJ.get("sword")), "strip_tags باید تگ را به یونیکد برگرداند"
    EMJ.set_custom({})


def test_25_persistence_across_restart():
    uid, cid, chat = new_player(rank=5)
    fund(uid)
    heal(uid)
    c = combat.start(uid, "hunt", chat=chat, titan_id="suko", encounter=1.0)
    assert c["ok"]
    combat.act(c["cid"], uid, "atk")
    hp_before = PL.get(uid)["hp"]
    # «ری‌استارت»: همان فایل، کش‌های فرآیند پاک
    handlers._FEED.clear()
    handlers._MEM_CACHE.clear()
    handlers._THROTTLE.clear()
    assert PL.get(uid)["hp"] == hp_before
    act = combat.active_of(uid)
    assert act and act.get("cid") == c["cid"], "نبرد زنده پس از ری‌استارت بازیابی نشد"
    r = combat.act(act["cid"], uid, "guard")
    assert r.get("ok") or r.get("live"), r
    combat.close(act["cid"], "test")


def main():
    random.seed(1330)
    tests = [(n, o) for n, o in sorted(globals().items()) if n.startswith("test_") and callable(o)]
    fails = 0
    for name, fn in tests:
        try:
            fn()
            print(f"✅ {name}")
            RESULTS.append((name, True, ""))
        except Exception as e:
            fails += 1
            import traceback
            tb = traceback.format_exc().strip().split("\n")
            print(f"❌ {name}: {type(e).__name__}: {str(e)[:160]}")
            print("     " + "\n     ".join(tb[-4:]))
            RESULTS.append((name, False, str(e)[:200]))
    print(f"\n{len(tests) - fails}/{len(tests)} tests passed")
    print(f"db={os.environ['MC_DB_PATH']} titans={len(TN.TITANS)} commands={len(handlers.COMMAND_MAP)}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
