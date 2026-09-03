# 🌍 World Boss / Raid Engine — عملیات مشترک گروهی با استخر HP و پنج شاخه‌ی جایزه
import random

import balance
import bosses
import ui
import config
import db
import titans as TN
from db import now

ACTIONS = {
    "strike": dict(name="ضربه", emj="sword", cost=6.0, key="dmg", desc="ضربه‌ی هماهنگ به بدنه‌ی باس"),
    "focus": dict(name="ضربهٔ متمرکز", emj="heavy", cost=14.0, key="dmg", desc="×۲ آسیب، ریسک آسیب خودت"),
    "shield": dict(name="خطِ سپر", emj="guard", cost=8.0, key="guard", desc="سپر متحدان؛ امتیاز بهترین دفاع"),
    "repair": dict(name="تعمیر میدانی", emj="medkit", cost=10.0, key="support", desc="ترمیم گروهی؛ بهترین پشتیبانی"),
    "analyze": dict(name="تحلیل ژرفا", emj="research", cost=6.0, key="analyze",
                    desc="جمع داده؛ پیشرفتِ پژوهش + جایزۀ بهترین پژوهش"),
    "regroup": dict(name="بازگروه‌بندی", emj="charge", cost=0.0, key="charge", desc="بازآرایی: شارژ و انرژی"),
}


def state() -> dict:
    st = db.db().getv("raid", None)
    if not st:
        return {}
    if st.get("status") != "live" or float(st.get("ends_at", 0)) < now():
        return dict(over=True, **st)
    return st


def start(boss_id: str = None, hours: float = None) -> dict:
    """آغاز رید جهانی (از موتور رویداد یا دستور ادمین)."""
    bid = boss_id or random.choice([k for k, v in bosses.BOSSES.items() if v.get("world")])
    b = bosses.by_id(bid)
    if not b:
        return dict(ok=False, msg=f"❔ باسِ جهانی «{bid}» در دیتابیس نیست — /boss list")
    chat = dict(zone=(b.get("zones") or ["city"])[0], danger=5, min_rank=6)
    blk = bosses.block_for(bid, chat)
    players = db.db().one("SELECT COUNT(*) c FROM players")
    scale = 1 + 0.06 * min(40, int((players or {}).get("c") or 1))
    # HP استخر بر پایه‌ی بلاکِ باس؛ ضربه‌ی هر کنش کفِ ۰٫۱۵٪ دارد (پایین‌تر از آن،
    # کلیک بی‌معنی می‌شود) پس یک گروه ۱۰ نفره در پنجره‌ی ۳ ساعته می‌تواند تمام کند.
    hp = round(float(blk["max_hp"]) * 3.2 * scale * (1 + 0.1 * bosses.TIERS.index(b["tier"])), 1)
    st = dict(id=int(db.db().bump("raid_seq", 1)), boss_id=bid, name=b["name"], emj=b["emj"],
              hp=hp, max_hp=hp, phase=1, status="live", created=now(),
              ends_at=now() + (hours or config.RAID_DURATION / 3600) * 3600,
              block=blk, participants=0, strikes=0, log=[])
    db.db().setv("raid", st)
    db.db().ex("INSERT INTO raids(id,boss_id,status,state,created_at,updated_at,ends_at) VALUES(?,?,?,?,?,?,?)",
               (st["id"], bid, "live", db.jdump({k: v for k, v in st.items() if k != "block"}),
                now(), now(), st["ends_at"]))
    return dict(ok=True, state=st, text=_announce(bid, st))


def _announce(bid: str, st: dict) -> str:
    b = bosses.by_id(bid)
    return (f"🚨 <b>هشدار سراسری مانارچ</b>\n\n"
            f"🌍 <b>WORLD EVENT — {b['name']}</b>\n"
            f"🕳 {TN.ENVS.get((b.get('zones') or ['city'])[0], 'شهر')} · "
            f"☢️ THREAT: <b>انقراض</b>\n"
            f"🧱 HP POOL: <code>{st['max_hp']:,.0f}</code>\n"
            f"⏱ پنجره: <b>{config.RAID_DURATION/3600:.0f} ساعت</b>\n\n"
            f"<i>{b.get('lore','')}</i>\n\n"
            f"▸ <code>/raid join</code> سپس <code>/raid</code> — ضربه بزن.\n"
            f"🥇 بیشترین آسیب · 🛡 بهترین دفاع · ❤️ بهترین پشتیبانی · 🎯 ضربه آخر · 🔬 بهترین پژوهش")


def join(uid: int) -> dict:
    st = state()
    if not st or st.get("over"):
        return dict(ok=False, msg="🌒 رید جهانی فعالی نیست.")
    import player as PL
    p = PL.get(uid)
    if not p:
        return dict(ok=False, msg="🔒 /start")
    if PL.is_dead(p):
        return dict(ok=False, msg="☠️ در حالت بازیابی نمی‌توانی وارد شیوع شوی.")
    d = db.db()
    r = d.one("SELECT * FROM raid_users WHERE raid_id=? AND user_id=?", (st["id"], int(uid)))
    if not r:
        d.ex("INSERT INTO raid_users(raid_id,user_id,joined) VALUES(?,?,?)", (st["id"], int(uid), now()))
        db.db().setv(f"raid:name:{st['id']}:{uid}", p["name"])
        st["participants"] = int(st.get("participants") or 0) + 1
        db.db().setv("raid", st)
        return dict(ok=True, msg=(f"🛰 <b>تکلیف پذیرفته شد</b>\n"
                                 f"واحد {p['name']} در عملیات <b>{st['name']}</b> ثبت شد.\n"
                                 f"«/raid» برای پنل ضربه."))
    return dict(ok=True, msg="🛰 تو در این عملیات ثبت شده‌ای — «/raid»")


def board() -> str:
    st = state()
    if not st or st.get("over"):
        return "🌒 هیچ رید جهانی فعال نیست. بعدی: سه‌شنبه/جمعه ۲۱:۰۰ تهران."
    import ui
    rows = db.db().q("""SELECT u.user_id, u.dmg, u.guard, u.support, u.analyze, u.strikes, p.name
                        FROM raid_users u LEFT JOIN players p ON p.user_id=u.user_id
                        WHERE u.raid_id=? ORDER BY u.dmg DESC LIMIT 8""", (st["id"],))
    lines = [f"❤️ {ui.meter('جانِ باس', st['hp'], st['max_hp'], '', 12, 'val')}",
             f"👥 {int(st.get('participants') or 0)} عامل · ⚔️ {int(st.get('strikes') or 0)} ضربه "
             f"· ⏱ {ui.eta(st['ends_at'])}", "", "🥇 <b>مشارکت</b>"]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. {r['name']} — 💥{ui.n(r['dmg'])} · 🛡{ui.n(r['guard'])} · "
                     f"❤️{ui.n(r['support'])} · 🔬{ui.n(r['analyze'])}")
    if not rows:
        lines.append("<i>هنوز ضربۀ ثبت‌شدۀ</i>")
    return ui.card(f"یورش جهانی — {st['name']}", lines,
                   stamp="تهدیدِ جهانی", code=st["id"],
                   note="پنج شاخۀ جایزه: آسیب، دفاع، پشتیبانی، ضربۀ آخر، پژوهش.")


def act(uid: int, action: str = "strike") -> dict:
    """هر ضربه یک پیام ندارد؛ فید گروه ویرایش می‌شود (ضداسپم)."""
    import player as PL
    st = state()
    if not st or st.get("over"):
        return dict(ok=False, msg="🌒 رید فعال نیست.")
    if PL.on_cd(uid, "raid"):
        return dict(ok=False, msg=f"⏳ {ui.dur(PL.cd_left(uid, 'raid'))} — هماهنگیِ تیمی.")
    a = ACTIONS.get(action)
    if not a:
        return dict(ok=False, msg="❔ کردار نامعتبر.")
    p = PL.get(uid)
    r = db.db().one("SELECT * FROM raid_users WHERE raid_id=? AND user_id=?", (st["id"], int(uid)))
    if not r:
        jr = join(uid)
        r = db.db().one("SELECT * FROM raid_users WHERE raid_id=? AND user_id=?", (st["id"], int(uid)))
    if float(p.get("energy") or 0) < a["cost"]:
        return dict(ok=False, msg=f"🔋 برای {a['name']} {a['cost']:.0f} انرژی لازم است.")
    PL.set_cd(uid, "raid", config.CD_RAID)
    PL.spend(uid, energy=-a["cost"])
    blk = st["block"]
    me = __import__("economy").stats_of(p)
    dmg = 0.0
    hurt = 0.0
    note = ""
    phase = int(st.get("phase") or 1)
    ratio = float(st["hp"]) / max(1.0, float(st["max_hp"]))
    new_phase = 1 + sum(1 for ph in (blk["boss"]["phases"] or []) if ratio <= ph.get("at", 1))
    if new_phase > phase:
        st["phase"] = new_phase
        note = f"\n🔄 <b>PHASE {new_phase}</b> — {(blk['boss']['phases'][new_phase-2] or {}).get('name','تغییر رفتار')}"
    if a["key"] in ("dmg",):
        heavy = action == "focus"
        r_ = balance.resolve_strike(me, blk, mult=(2.0 if heavy else 1.0), env=blk.get("_boss_env"))
        dmg = 0.0 if r_.get("dodged") or r_.get("missed") else r_["dmg"]
        dmg += 0.0015 * float(st["max_hp"])          # سهمِ تضمینی هر کنش از محاصره
        dmg *= 1 + 0.06 * (new_phase - 1)          # ضربات فازهای پایین‌تر قوی‌ترند (مکانیک)
        st["hp"] = round(max(0.0, float(st["hp"]) - dmg), 2)
        st["last_hit"] = int(uid)
        if heavy and random.random() < 0.32:
            hurt = round(random.uniform(0.06, 0.18) * float(me["max_hp"]), 1)
            note += f"\n🩸 فشار پس‌زنی: −{hurt} HP"
    elif a["key"] == "guard":
        dmg = round(random.uniform(30, 90) * (1 + 0.1 * new_phase), 1)
        note = f"\n🛡 خط دفاعی تو {int(round(dmg))} آسیب ورودی گروه را خنثی کرد"
    elif a["key"] == "support":
        dmg = round(random.uniform(40, 110), 1)
        for row in db.db().q("SELECT user_id FROM raid_users WHERE raid_id=? LIMIT 6", (st["id"],)):
            q = PL.get(int(row["user_id"]))
            if q:
                db.db().apply(int(row["user_id"]),
                              hp=min(float(q["max_hp"]), float(q["hp"]) + dmg * 0.4))
        note = f"\n❤️ ترمیم گروهی: +{dmg*0.4:.0f} HP به هر عضو"
    elif a["key"] == "analyze":
        dmg = round(random.uniform(20, 55), 1)
        import research
        bid_base = blk.get("tid")
        res = research.add_points(uid, bid_base, 22, "raid")
        note = (f"\n🔬 داده‌ی حیاتی استخراج شد"
                + (f" · 🚨 <b>ارتقای مرحله</b> → {research.STAGES[res['stage']]['label']}" if res.get("advanced") else ""))
    else:  # regroup
        PL.add_res(uid, energy=24)
        note = "\n🔋 واحد دوباره سازمان‌دهی شد"
    db.db().ex("""UPDATE raid_users SET dmg=dmg+?, guard=guard+?, support=support+?, analyze=analyze+?,
                 strikes=strikes+1, last_hit=? WHERE raid_id=? AND user_id=?""",
               (dmg if a["key"] == "dmg" else 0, dmg if a["key"] == "guard" else 0,
                dmg if a["key"] == "support" else 0, dmg if a["key"] == "analyze" else 0,
                1 if (a["key"] == "dmg" and float(st["hp"]) <= 0) else 0, st["id"], int(uid)))
    if hurt:
        db.db().apply(int(uid), hp=max(1.0, float(p["hp"]) - hurt))
        if float(p["hp"]) - hurt <= 0:
            PL.die(uid, "WORLD_RAID")
            note += "\n☠️ <b>عامل از پا درآمده</b> — واحد پشتیبانی تو را برداشت"
    st["strikes"] = int(st.get("strikes") or 0) + 1
    st["log"] = ((st.get("log") or []) + [f"{PL.name_of(uid)} · {a['name']}"])[-6:]
    PL.progress(uid, "raid_strike", 1)
    PL.track_stat(uid, "raids", 0)
    if float(st["hp"]) <= 0:
        db.db().setv("raid", st)
        return finish(won=True)
    db.db().setv("raid", st)
    return dict(ok=True, msg=f"{a['emj']} <b>{a['name']}</b> — "
                             + (f"💥 {dmg:,.0f} آسیب\n" if dmg else "")
                             + f"🧱 باس: {st['hp']:,.0f}/{st['max_hp']:,.0f} ({int(ratio*100)}%)"
                             + note,
                feed=True)


def finish(won: bool = None) -> dict:
    """تسویه: توزیع جوایز بر پایه‌ی پنج شاخه."""
    st = db.db().getv("raid", {}) or {}
    if not st:
        return dict(ok=False)
    bid = st.get("boss_id")
    b = bosses.by_id(bid)
    rows = db.db().q("SELECT * FROM raid_users WHERE raid_id=?", (st["id"],))
    awards, lines = {}, []
    if rows:
        def best(key):
            c = sorted(rows, key=lambda r: -float(r[key] or 0))
            return c[0] if c and float(c[0][key] or 0) > 0 else None
        awards = dict(damage=best("dmg"), defense=best("guard"), support=best("support"),
                      research=best("analyze"),
                      last_hit=next((r for r in sorted(rows, key=lambda r: -r["last_hit"])), None))
    import player as PL
    rw = b.get("reward", {})
    if won:
        for r in rows:
            PL.add_res(int(r["user_id"]), **{k: v for k, v in rw.items() if k in
                                            ("credits", "cores", "dna", "cells", "mats", "fdata")})
            PL.add_xp(int(r["user_id"]), 60)
            PL.track_stat(int(r["user_id"]), "raids", 1)
            import division
            division.credit_activity(int(r["user_id"]), "raid", 1)
        labels = dict(damage="🥇 بیشترین آسیب", defense="🛡 بهترین دفاع", support="❤️ بهترین پشتیبانی",
                      last_hit="🎯 ضربه آخر", research="🔬 بهترین پژوهش")
        for k, r in awards.items():
            if r:
                nm = db.db().getv(f"raid:name:{st['id']}:{r['user_id']}", "") or PL.name_of(int(r["user_id"]))
                bonus = {kk: (vv * 0.35) for kk, vv in rw.items() if kk in ("credits", "cells")}
                if k in ("damage", "last_hit"):
                    bonus["cores"] = 2
                PL.add_res(int(r["user_id"]), **bonus)
                lines.append(f"{labels[k]} → <b>{nm}</b>")
        txt = (f"🏆 <b>تهدید جهانی خنثی شد</b> — {st.get('name')}\n"
               f"👥 {len(rows)} عامل · ⚔ {int(st.get('strikes') or 0)} ضربه\n"
               + ("\n".join(lines) if lines else "")
               + f"\n🪙 جوایز توزیع شد · <i>پرونده برای تجزیه‌وتحلیل بسته شد.</i>")
    else:
        for r in rows:
            PL.add_xp(int(r["user_id"]), 14)
            PL.add_res(int(r["user_id"]), credits=round(float(rw.get("credits", 1000)) * 0.12, 0))
        txt = (f"⌛ <b>عملیات بسته شد</b> — {st.get('name')}\n"
               f"باس زنده ماند؛ خسارت محدود وارد شد ({float(st.get('hp',0))/max(1.0,float(st.get('max_hp',1)))*100:.0f}% HP باقی). "
               f"جایزه‌ی مشارکت پرداخت شد.")
    st["status"] = "done"
    db.db().setv("raid", st)
    db.db().ex("UPDATE raids SET status='done', state=?, updated_at=? WHERE id=?",
               (db.jdump({k: v for k, v in st.items() if k != "block"}), now(), st["id"]))
    return dict(ok=True, msg=txt, won=bool(won), awards=awards)


def check_expiry() -> dict:
    st = state()
    if not st:
        prev = db.db().getv("raid", {}) or {}
        if prev.get("status") == "live":
            return finish(won=False)
    return {}
