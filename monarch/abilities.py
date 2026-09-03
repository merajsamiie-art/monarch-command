# ☄️ Ability Engine — مهارت‌ها، پسیوها و اولتیمیت‌ها
# هر ability: cost (انرژی) | cd (نوبت) | power (ضریب) | req (شرط فعال‌سازی) | eff (افکت)
# eff کلیدها: dmg, burn, acid, stun, slow, freeze, shield, atkup, defup, accup, blind,
#              heal, drain, charge, knock, dispel, mark, env (تغییر محیط), pull
import emoji as EMJ

ABILITIES: dict = {}
PASSIVES: dict = {}


def ab(aid, name, emj, cost, cd, power, req=None, eff=None, tag="", desc=""):
    ABILITIES[aid] = dict(id=aid, name=name, emj=EMJ.of(emj, "☄️"), cost=cost, cd=cd, power=power,
                          req=req or {}, eff=eff or {}, tag=tag, desc=desc)
    return ABILITIES[aid]


def pas(pid, name, emj, desc, mods=None):
    PASSIVES[pid] = dict(id=pid, name=name, emj=EMJ.of(emj, "🧬"), desc=desc, mods=mods or {})


# ───────── GODZILLA ─────────
ab("atomic_breath", "تنفسِ اتمی", "atom", 62, 0, 2.35, dict(charge=100), {"dmg": 1.0, "burn": 3, "mark": 2},
   "atomic", "پرتو اتمی کامل — فقط با شارژ ۱۰۰٪. تمام‌کننده‌ی نبرد.")
ab("atomic_pulse", "تپشِ اتمی", "atom", 26, 2, 1.15, {}, {"dmg": 1.0, "stun": 1, "knock": 8},
   "atomic", "تپش هسته‌ای: آسیب متوسط + یک نوبت فلج.")
ab("tail_sweep", "Tail Sweep", "sword", 12, 1, 0.72, {}, {"dmg": 1.0, "slow": 2, "blind": 1},
   "brute", "دمِ سنگین: تعادل حریف را می‌گیرد.")
ab("nuclear_grasp", "Nuclear Grasp", "heavy", 20, 3, 0.95, {}, {"dmg": 1.0, "burn": 2, "drain": 0.25},
   "atomic", "چنگال رادیواکتیو: بخشی از انرژی را می‌مکد.")
ab("alpha_roar", "غرّشِ آلفا", "crown", 34, 5, 0.30, {}, {"dmg": 0.5, "dispel": 1, "defdown": 2, "atkup": 2},
   "brute", "رامشِ آلفا: بافرهای حریف را می‌کَنَد و ترس می‌پراکند.")

# ───────── KONG ─────────
ab("axe_slam", "Axe Slam", "heavy", 22, 2, 1.30, {}, {"dmg": 1.0, "stun": 1, "shield": -0.4},
   "brute", "ضربه‌ی تبر؛ سپر حریف را می‌شکافد.")
ab("ground_pound", "Ground Pound", "clash", 18, 3, 0.90, {}, {"dmg": 0.8, "slow": 3, "knock": 14},
   "brute", "کوبیدن زمین — محیط را بی‌ثبات می‌کند.")
ab("sign_language", "Tactical Sign", "data", 8, 4, 0.0, {}, {"atkup": 3, "accup": 3, "charge": 12},
   "psychic", "طرح‌ریزی ساکت: +دقت و +آسیب برای سه نوبت.")
ab("feral_grapple", "Feral Grapple", "sword", 16, 2, 1.05, {}, {"dmg": 1.0, "drain": 0.18, "stun": 1},
   "brute", "کلنگیدن وحشیان؛ انرژی حریف را می‌گیرد.")
ab("battle_axe", "War Axe of the Hollow", "heavy", 58, 0, 2.05, dict(charge=100),
   {"dmg": 1.0, "stun": 2, "shield": -0.8, "env": "hollow"}, "brute",
   "تبرِ جنگی با شارژ کامل؛ ضربدرِ زمین توخالی.")

# ───────── GHIDORAH ─────────
ab("gravity_beam", "Gravity Beams", "spark", 26, 2, 1.28, {}, {"dmg": 1.0, "slow": 2, "pull": 10},
   "gravity", "سه پرتو جاذبه؛ حریف را به هوا می‌کشد.")
ab("storm_front", "Storm Generation", "storm", 22, 4, 0.60, {}, {"env": "city", "blind": 3, "dmg": 0.4},
   "storm", "جبهه‌ی طوفان می‌سازد؛ دید و دقت می‌افتد.")
ab("neck_constrict", "Neck Constrict", "sword", 18, 2, 1.10, {}, {"dmg": 1.0, "drain": 0.2, "stun": 1},
   "brute", "گره‌ی سه‌سر: خفگی و سرقت انرژی.")
ab("dark_current", "Dark Current", "spark", 30, 3, 1.35, {}, {"dmg": 1.0, "stun": 1, "burn": 2},
   "electric", "رعد و برق مشکی؛ هم فلج، هم سوختگی.")
ab("gravity_ray_storm", "طوفانِ گرانش پرتو", "storm", 66, 0, 2.45, dict(charge=100),
   {"dmg": 1.0, "stun": 2, "slow": 3, "knock": 25}, "storm",
   "طوفان پرتو جاذبه — آسمان شهر را پاک می‌کند.")

# ───────── MOTHRA ─────────
ab("imago_scale", "Imago Scale Shot", "light", 20, 2, 1.05, {}, {"dmg": 1.0, "blind": 2, "heal": 0.1},
   "light", "پولک درخشان: کوری + التیام سبک.")
ab("silk_bind", "Silk Bind", "guard", 16, 3, 0.60, {}, {"dmg": 0.4, "stun": 2, "slow": 3},
   "silk", "تار ابریشمی: دو نوبت قفل حرکت.")
ab("protective_barrier", "Protective Barrier", "guard", 24, 5, 0.0, {}, {"shield": 0.85, "defup": 3},
   "light", "سد محافظتی؛ آسیب ورودی را تقریباً دو نوبت صفر می‌کند.")
ab("telepathic_song", "Telepathic Song", "signal", 14, 4, 0.0, {}, {"dispel": 2, "heal": 0.22, "accup": 2},
   "psychic", "سرود ذهنی: پاک‌سازی وضعیت‌های منفی + Treated HP.")
ab("rebirth_light", "Rebirth Radiance", "light", 60, 0, 1.95, dict(charge=100),
   {"dmg": 1.0, "heal": 0.42, "dispel": 9, "revive": 0.35}, "light",
   "نورِ تولد دوباره؛ هم زخم حریف، هم احیای خود.")

# ───────── RODAN ─────────
ab("plasma_breath", "تنفسِ پلاسما", "flame", 24, 2, 1.22, {}, {"dmg": 1.0, "burn": 3},
   "fire", "نفس پلاسمایی؛ سوختگی سه‌نوبته.")
ab("supersonic_dive", "Supersonic Dive", "dodge", 18, 2, 1.35, {}, {"dmg": 1.0, "knock": 12},
   "flight", "شیرجه‌ی فراصوت؛ اگر جاخالی بدهی، بی‌ضرر است.")
ab("ash_cloud", "Ash Cloud", "warning", 14, 4, 0.35, {}, {"dmg": 0.3, "blind": 3, "acid": 2},
   "volcanic", "ابر خاکستر؛ دقت همه پایین می‌آید.")
ab("firestorm_spiral", "Firestorm Spiral", "volcano", 56, 0, 2.10, dict(charge=100),
   {"dmg": 1.0, "burn": 4, "env": "volcano"}, "fire", "مارپیچ آتشین؛ محیط را آتشفشان می‌کند.")

# ───────── MECHAGODZILLA ─────────
ab("proton_scream", "جیغِ پروتون", "mecha", 28, 2, 1.32, {}, {"dmg": 1.0, "stun": 1, "heat": 22},
   "tech", "جیغ پروتونی؛ اما هسته را داغ می‌کند.")
ab("missile_barrage", "Missile Barrage", "heavy", 20, 3, 1.05, {}, {"dmg": 1.0, "blind": 1, "heat": 14},
   "tech", "رگبار موشک؛ چند ضربه‌ی پی‌درپی.")
ab("target_lock", "قفلِ هدف", "track", 12, 4, 0.0, {}, {"mark": 4, "accup": 4, "heat": 8},
   "tech", "قفل هدف: ضربه‌ی بعدی کریت قطعی.")
ab("titanium_jaw", "فکِ تیتانیوم", "shield_doc", 14, 2, 0.95, {}, {"dmg": 1.0, "shield": 0.3, "heat": 6},
   "mech", "چنگ فلزی؛ هم ضربه، هم سپر.")
ab("absolute_annihilation", "Absolute Annihilation", "mecha", 64, 0, 2.50, dict(charge=100, heat_max=1),
   {"dmg": 1.0, "stun": 2, "heat": 55, "shield": -0.6}, "tech",
   "نابودی مطلق — پس از آن، Overheat: دو نوبت فلج.")

# ───────── DESTOROYAH ─────────
ab("microoxygen_beam", "Oxygen Micro-Beam", "destoroyah", 24, 2, 1.24, {}, {"dmg": 1.0, "acid": 3, "heal": 0.08},
   "oxygen", "پرتوی که سلول را از هم می‌پاشد.")
ab("agony_shoot", "Agony Shoot", "boss", 18, 3, 1.02, {}, {"dmg": 1.0, "stun": 1, "slow": 2},
   "brute", "شاخ‌های درد؛ تعویق و فلج کوتاه.")
ab("ash_form", "قالبِ خاکستر", "flee", 16, 4, 0.0, {}, {"dodgeup": 3, "dispel": 2, "shield": 0.25},
   "void", "فرم خاکستر: دو نوبت تقریباً نامرئی.")
ab("cell_swarm", "Micro-Organ Cell Swarm", "swarm", 22, 3, 0.88, {}, {"dmg": 1.0, "acid": 2, "drain": 0.2},
   "acid", "موج ریزسلول‌ها؛ خوردگی و سرقت انرژی.")
ab("perfection_ascends", "Ascension to Perfection", "destoroyah", 62, 0, 2.20, dict(charge=100),
   {"dmg": 1.0, "phase": 1, "regen": 3, "stun": 1}, "oxygen",
   "تکامل نهایی: فاز عوض می‌کند و ترمیم می‌گیرد.")

# ───────── SPACEGODZILLA ─────────
ab("crystal_array", "Crystal Array", "gem", 22, 3, 1.18, {}, {"dmg": 1.0, "freeze": 2, "shield": 0.3},
   "crystal", "آرایه‌ی بلور؛ هم تیزه، هم سنگر.")
ab("corona_beam", "Corona Beam", "atom", 30, 2, 1.36, {}, {"dmg": 1.0, "burn": 2, "freeze": 1},
   "crystal", "پرتو تاجی؛ ترکیب یخ و آتش هسته‌ای.")
ab("diameter_cage", "Diameter Cage", "lock", 20, 4, 0.55, {}, {"dmg": 0.3, "stun": 3, "blind": 2},
   "crystal", "قفس بلورین: سه نوبت بدون اکشن.")
ab("reflective_shield", "Reflective Shield", "guard", 24, 5, 0.0, {}, {"shield": 0.9, "reflect": 0.4, "freeze": 1},
   "crystal", "سپر بازتابنده؛ بخشی از آسیب را برمی‌گرداند.")
ab("corona_burst_max", "Corona Burst MAX", "gem", 66, 0, 2.42, dict(charge=100),
   {"dmg": 1.0, "freeze": 3, "stun": 2}, "crystal", "انفجار تاجی کامل — منطقه را شیشه می‌کند.")

# ───────── بقیه‌ی کایجو (امضای هر تایتان) ─────────
ab("spiny_roll", "Spiny Roll", "anguirus", 16, 2, 1.06, {}, {"dmg": 1.0, "bleed": 2}, "brute", "غلت تیغ‌دار.")
ab("burrow_ambush", "کمینِ کندن", "dodge", 18, 3, 1.28, {}, {"dmg": 1.0, "stun": 1, "knock": 10}, "burrow", "از زیر زمین، بی‌صدا.")
ab("protect_instinct", "Protector Instinct", "guard", 12, 4, 0.0, {}, {"shield": 0.6, "defup": 3}, "brute", "سپر زنده.")
ab("aegis_of_the_ancient", "Aegis of the Ancient", "guard", 52, 0, 1.70, dict(charge=100),
   {"dmg": 1.0, "shield": 0.9, "dispel": 4}, "brute", "سپر باستانی: هم ضربه، هم سپر کامل.")
ab("acid_spray", "Acid Spray", "acid", 16, 2, 1.00, {}, {"dmg": 1.0, "acid": 3}, "acid", "اسید فرساینده.")
ab("vine_lash", "کوبشِ پیچک", "dna", 18, 2, 1.14, {}, {"dmg": 1.0, "stun": 1, "drain": 0.22}, "brute", "ریشه‌ها می‌فشارند.")
ab("seed_barrage", "Seed Barrage", "dna", 20, 3, 0.92, {}, {"dmg": 1.0, "acid": 2, "blind": 1}, "venom", "باران دانه‌های اسیدی.")
ab("cell_absorb", "Cell Absorb", "dna", 14, 4, 0.40, {}, {"dmg": 0.3, "heal": 0.30, "drain": 0.2}, "plant", "جذب زیست‌توده.")
ab("floral_consumption", "Floral Consumption", "dna", 54, 0, 1.90, dict(charge=100),
   {"dmg": 1.0, "heal": 0.5, "stun": 2}, "plant", "گل کامل می‌شود و حریف را می‌خورد.")
ab("cyclops_beam", "Cyclops Beam", "gigan", 22, 2, 1.20, {}, {"dmg": 1.0, "burn": 1}, "atomic", "پرتو چشم‌یک.")
ab("spinner_blade", "Spinner Blade", "sword", 18, 2, 1.16, {}, {"dmg": 1.0, "bleed": 3}, "blade", "تیغه‌های چرخان سینه.")
ab("chest_cannon", "Chest Cannon", "heavy", 24, 3, 1.10, {}, {"dmg": 1.0, "knock": 12}, "tech", "توپ قفسه.")
ab("buzzer_saw", "Buzzer Saw", "heavy", 20, 3, 1.12, {}, {"dmg": 1.0, "bleed": 2, "stun": 1}, "blade", "اره‌ی بال‌دار.")
ab("cybernetic_execution", "Cybernetic Execution", "gigan", 58, 0, 2.15, dict(charge=100),
   {"dmg": 1.0, "bleed": 4, "stun": 2}, "blade", "اعدام سایبرنتیک.")
ab("acid_fog", "Acid Fog", "hedorah", 20, 3, 0.72, {}, {"dmg": 0.6, "acid": 4, "blind": 3}, "venom", "مه اسیدی کل میدان.")
ab("slime_shard", "Slime Shard", "acid", 14, 2, 0.98, {}, {"dmg": 1.0, "acid": 2}, "acid", "تکه‌لجن برّنده.")
ab("mineral_absorb", "Mineral Absorb", "material", 12, 4, 0.30, {}, {"dmg": 0.2, "heal": 0.2, "shield": 0.4}, "venom", "معدن را می‌خورد و زره می‌سازد.")
ab("siren_descent", "Siren Descent", "boss", 26, 4, 1.18, {}, {"dmg": 1.0, "acid": 3, "stun": 1}, "venom", "فاز سیiren بالای شهر.")
ab("toxic_dissolution", "Toxic Dissolution", "hedorah", 56, 0, 2.05, dict(charge=100),
   {"dmg": 1.0, "acid": 5, "dispel": 3}, "venom", "حل‌شدن سمی؛ همه‌چیز.")
ab("drill_hands", "Drill Hands", "megalon", 16, 2, 1.08, {}, {"dmg": 1.0, "bleed": 2}, "brute", "مته‌های دست.")
ab("burrow_charge", "شارژِ کندن", "dodge", 14, 2, 1.00, {}, {"dmg": 1.0, "knock": 14}, "burrow", "حمله از تونل.")
ab("horn_burst", "Horn Burst", "spark", 20, 3, 1.14, {}, {"dmg": 1.0, "stun": 1}, "energy", "تخلیه‌ی شاخک.")
ab("pyre_spiral", "Pyre Spiral", "flame", 50, 0, 1.80, dict(charge=100), {"dmg": 1.0, "burn": 3}, "fire", "مارپیچ آتش.")
ab("guardian_roar", "غرّشِ حافظ", "crown", 18, 4, 0.5, {}, {"atkup": 3, "shield": 0.4}, "light", "رامش نگهبان.")
ab("fang_rush", "Fang Rush", "sword", 14, 2, 1.04, {}, {"dmg": 1.0}, "brute", "دویدنِ نیش‌دار.")
ab("spirit_ward", "Spirit Ward", "guard", 22, 5, 0.0, {}, {"shield": 0.8, "reflect": 0.3}, "light", "حریم شینتویی.")
ab("sonic_wail", "Sonic Wail", "track", 20, 3, 1.06, {}, {"dmg": 0.8, "stun": 2, "blind": 2}, "sonic", "ناله‌ی فروسونیک.")
ab("whirlpool_slam", "Whirlpool Slam", "ocean", 18, 2, 1.12, {}, {"dmg": 1.0, "knock": 10, "slow": 2}, "aquatic", "چرخش آب و تنه.")
ab("resonance_collapse", "ریزشِ تشدید", "titanosaurus", 52, 0, 1.95, dict(charge=100),
   {"dmg": 1.0, "stun": 3, "dispel": 3}, "sonic", "فروپاشی تشدیدی.")
ab("prismatic_lance", "Prismatic Lance", "light", 20, 2, 1.18, {}, {"dmg": 1.0, "blind": 2}, "light", "نیزه‌ی منشور.")
ab("obsidian_dust", "گردِ  ابسیدین", "warning", 18, 3, 0.86, {}, {"dmg": 0.7, "blind": 3, "acid": 2}, "dark", "گرد سیاه انتقام.")
ab("planet_cleanser", "Planet Cleanser", "battra", 58, 0, 2.12, dict(charge=100),
   {"dmg": 1.0, "stun": 2, "env": "jungle"}, "light", "پاکسازی سیاره.")
ab("missile_fist", "Missile Fist", "heavy", 18, 2, 1.10, {}, {"dmg": 1.0, "burn": 1}, "tech", "مشت موشکی.")
ab("jet_dash", "جهشِ جت", "dodge", 12, 1, 0.95, {}, {"dmg": 1.0, "knock": 8}, "flight", "دویدن جت‌مانند.")
ab("grow_protocol", "Grow Protocol", "binary", 16, 5, 0.0, {}, {"atkup": 4, "hp_temp": 0.15}, "tech", "پروتکل بزرگ‌شدن.")
ab("scan_lock", "Scan & Lock", "track", 10, 3, 0.0, {}, {"mark": 3, "accup": 3}, "tech", "اسکن و قفل.")
ab("ga_plasma", "Go Plasma", "spark", 20, 2, 1.14, {}, {"dmg": 1.0, "burn": 2}, "tech", "پلاسمای ماسر.")
ab("drill_arms", "Drill Arms", "megalon", 16, 2, 1.06, {}, {"dmg": 1.0, "bleed": 2}, "mech", "بازوهای مته‌ای.")
ab("earthen_ray", "Earthen Ray", "flame", 18, 2, 1.10, {}, {"dmg": 1.0, "burn": 2}, "fire", "پرتو خاکی.")
ab("tunnel_ambush", "Tunnel Ambush", "dodge", 14, 2, 1.02, {}, {"dmg": 1.0, "stun": 1}, "burrow", "کمین تونلی.")
ab("silk_snare", "Silk Snare", "guard", 14, 3, 0.55, {}, {"dmg": 0.3, "stun": 2, "slow": 2}, "silk", "تار چسبنده.")
ab("venom_bite", "گازِ زهر", "acid", 14, 2, 1.02, {}, {"dmg": 1.0, "acid": 2}, "venom", "نیش سمی.")
ab("pack_swarm", "Pack Swarm", "swarm", 16, 3, 0.90, {}, {"dmg": 1.0, "blind": 1}, "brute", "حمله‌ی دسته‌جمعی.")
ab("electro_claw", "Electro-Claw", "spark", 18, 2, 1.14, {}, {"dmg": 1.0, "stun": 1}, "electric", "چنگال برقی.")
ab("crustacean_crush", "Crustacean Crush", "heavy", 20, 3, 1.20, {}, {"dmg": 1.0, "knock": 12}, "brute", "پارچۀ سخت‌پوست.")
ab("coil_crush", "کوبشِ پیچ", "manda", 20, 3, 1.22, {}, {"dmg": 1.0, "stun": 2, "drain": 0.15}, "brute", "حلقه‌های مرگ.")
ab("kangaroo_kick", "Kangaroo Kick", "heavy", 16, 2, 1.08, {}, {"dmg": 1.0, "knock": 10}, "brute", "لگد دوپا.")
ab("glide_rake", "Glide Rake", "sword", 14, 2, 1.00, {}, {"dmg": 1.0, "bleed": 2}, "flight", "خزش و چنگال.")
ab("void_claw", "چنگالِ پوچ", "monsterx", 20, 2, 1.20, {}, {"dmg": 1.0, "acid": 2}, "void", "چنگال پوچی.")
ab("energy_absorb", "Energy Absorb", "charge", 10, 3, 0.40, {}, {"dmg": 0.2, "drain": 0.5, "charge": 18}, "void", "جذب انرژی حریف.")
ab("arm_fang", "دندانِ بازو", "sword", 16, 2, 1.10, {}, {"dmg": 1.0, "bleed": 2}, "brute", "دندانِ بازو.")
ab("quantum_swarm", "دستهِ کوانتومی", "swarm", 18, 3, 0.95, {}, {"dmg": 1.0, "drain": 0.25}, "energy", "موج مگس‌های کوانتومی.")
ab("annihilation_ring", "Annihilation Ring", "megaguirus", 54, 0, 2.05, dict(charge=100),
   {"dmg": 1.0, "burn": 3, "dispel": 2}, "solar", "حلقه‌ی فانی؛ خورشید را می‌آورد.")
ab("dark_matter_barrier", "Dark Matter Barrier", "guard", 22, 4, 0.0, {}, {"shield": 0.95, "reflect": 0.5}, "dark", "سد ماده‌ی تاریک.")
ab("void_beam", "پرتوِ پوچ", "destoroyah", 24, 2, 1.26, {}, {"dmg": 1.0, "acid": 2}, "void", "پرتو پوچ.")
ab("the_beast_rises", "The Beast Rises", "monsterx", 60, 0, 2.30, dict(charge=100),
   {"dmg": 1.0, "phase": 1, "stun": 1, "heal": 0.2}, "void", "Monster X از خاکستر بلند می‌شود.")
ab("gravity_clamp", "Gravity Clamp", "spark", 26, 2, 1.30, {}, {"dmg": 1.0, "slow": 3, "pull": 14}, "gravity", "گیره‌ی جاذبه.")
ab("energy_siphon", "Energy Siphon", "charge", 18, 4, 0.55, {}, {"dmg": 0.4, "drain": 0.6, "heal": 0.2}, "void", "مکش انرژی.")
ab("planet_devour", "Planet Devour", "keizer", 68, 0, 2.55, dict(charge=100),
   {"dmg": 1.0, "drain": 0.5, "stun": 2}, "gravity", "خورندۀ سیاره.")
ab("monollith_whip", "Monollith Whip", "heavy", 22, 2, 1.24, {}, {"dmg": 1.0, "knock": 16}, "brute", "شلاق سنگی.")
ab("beast_chain", "Chain of Beasts", "boss", 24, 3, 1.10, {}, {"dmg": 0.9, "stun": 2, "pull": 10}, "dark", "زنجیرِ بردگی تایتان‌ها.")
ab("chain_of_command", "Chain of Command", "skar", 62, 0, 2.35, dict(charge=100),
   {"dmg": 1.0, "stun": 3, "dispel": 4}, "dark", "فرمان زنجیر؛ تایتان‌ها زانو می‌زنند.")
ab("frost_breath", "Frost Breath", "ice", 22, 2, 1.20, {}, {"dmg": 1.0, "freeze": 2}, "ice", "نفس یخی.")
ab("glacial_spikes", "Glacial Spikes", "ice", 20, 3, 1.12, {}, {"dmg": 1.0, "slow": 3, "bleed": 2}, "ice", "میخ‌های یخی.")
ab("absolute_zero_front", "Absolute Zero Front", "ice", 64, 0, 2.30, dict(charge=100),
   {"dmg": 1.0, "freeze": 4, "env": "antarctica"}, "ice", "جبهه‌ی صفر مطلق.")
ab("tidal_wing", "Tidal Wing", "ocean", 18, 2, 1.10, {}, {"dmg": 1.0, "knock": 12}, "aquatic", "بالِ مدی.")
ab("tentacle_gale", "Tentacle Gale", "scylla", 20, 2, 1.16, {}, {"dmg": 1.0, "stun": 1, "pull": 8}, "aquatic", "گردباد بازوآبی.")
ab("stampede", "Stampede", "behemoth", 18, 2, 1.06, {}, {"dmg": 1.0, "knock": 12}, "brute", "یورش گله.")
ab("branch_lash", "Branch Lash", "dna", 14, 2, 1.00, {}, {"dmg": 1.0, "slow": 2}, "plant", "شلاق شاخه.")
ab("electro_net", "Electro Net", "spark", 18, 3, 1.05, {}, {"dmg": 1.0, "stun": 2}, "electric", "شبکه‌ی برکه.")
ab("molt_whip", "Molt Whip", "abaddon", 16, 2, 1.04, {}, {"dmg": 1.0, "bleed": 2, "shield": 0.2}, "brute", "شلاق پوست‌اندازی.")
ab("resonance_call", "Resonance Call", "muto", 20, 3, 1.02, {}, {"dmg": 0.8, "stun": 2, "blind": 2}, "sonic", "فراخوان تشدید.")
ab("skull_crush", "کوبشِ جمجمه", "skullcrawler", 16, 2, 1.12, {}, {"dmg": 1.0, "bleed": 2}, "brute", "فشار فک.")
ab("wing_gust", "Wing Gust", "dodge", 12, 2, 0.92, {}, {"dmg": 0.9, "knock": 8}, "flight", "تندباد بال.")
ab("strike_basic", "ضربهِ استاندارد", "sword", 8, 0, 0.80, {}, {"dmg": 1.0}, "kinetic", "ضربه‌ی استاندارد مانارچ.")
ab("emp_charge", "شارژِ پالس", "spark", 22, 4, 1.10, {}, {"dmg": 0.8, "stun": 1, "drain": 0.4}, "electric", "تخلیه‌ی الکترومغناطیسی.")
ab("concussion_grenade", "Concussion Charge", "heavy", 18, 3, 1.00, {}, {"dmg": 1.0, "stun": 1, "blind": 1}, "kinetic", "شارج کوبنده.")
ab("nanite_repair", "Nanite Repair", "medkit", 16, 5, 0.0, {}, {"heal": 0.28, "dispel": 2}, "tech", "ترمیم نانو.")
ab("orbital_laser", "Orbital Laser", "track", 30, 4, 1.45, dict(needs_mark=1), {"dmg": 1.0, "burn": 1}, "tech", "لایزِ مداری — فقط روی هدف قفل‌شده.")

# ───────── Passive Registry ─────────
pas("alpha_presence", "Alpha Presence", "crown", "آسیب +۸٪، آسیب ورودی در دو نوبت اول −۱۲٪.",
    dict(dmg=0.08, early_dr=0.12))
pas("combat_intel", "Combat Intelligence", "intel", "شانس جاخالی +۶٪ و دقت +۶٪.", dict(dodge=0.06, acc=0.06))
pas("guardian_vow", "Guardian Vow", "guard", "یک بار در نبرد، ضربه‌ی کشنده را به ۱۵٪ HP تبدیل می‌کند.", dict(deathguard=1))
pas("three_heads", "Three Will", "storm", "سه نوبتِ یک‌درمیان: آسیب +۱۵٪، اما پیش‌بینی‌پذیر.", dict(alternate=0.15))
pas("flight_master", "Aerial Mastery", "flight", "بی‌نیاز از جریمه‌ی محیط، جاخالی +۱۰٪.", dict(no_env_pen=True, dodge=0.10))
pas("machine_core", "Machine Core", "mecha", "مصون در برابر سم/سوختگی، اما بدون ترمیم طبیعی.", dict(immune="acid|burn|bleed", no_regen=True))
pas("adaptive_evolution", "Adaptive Evolution", "phase", "در هر فاز، یک مقاومت تصادفی +۲۰٪.", dict(phase_res=0.20))
pas("guardian_link", "Guardian Link", "shield_doc", "اگر متحدی در میدان باشد، آسیب ورودی −۱۰٪.", dict(ally_dr=0.10))
pas("green_regen", "Floral Regen", "dna", "ترمیم بالا؛ هر نوبت +۴٪ HP.", dict(regen_pct=0.04))
pas("cyber_enhanced", "Cybernetics", "mecha", "ضربه‌ی اول هر نبرد کریت قطعی.", dict(first_crit=True))
pas("corrosive_body", "Corrosive Body", "acid", "هر ضربه‌ی نزدیک، ۶٪ اسید می‌دهد.", dict(thorns=0.06, thorns_tag="acid"))
pas("burrower", "Burrower", "dodge", "یک بار هر ۳ نوبت، حمله‌ی فاصله‌دور را نادیده می‌گیرد.", dict(untargetable=3))
pas("aquatic_pulse", "Deep Pressure", "ocean", "در آب آسیب +۱۵٪، خشکی −۸٪.", dict(home_bonus=0.15))
pas("dark_guardian", "Dark Justice", "dark", "اگر HP حریف بالای ۶۰٪ باشد، آسیب +۱۴٪.", dict(execution=0.14))
pas("absorption", "Energy Absorption", "charge", "هر حمله‌ی انرژی‌ای که به او می‌خورد، ۳۰٪ شارژ می‌دهد.", dict(absorb=0.30))
pas("swarm_mind", "Swarm Mind", "swarm", "شانس حمله‌ی دوباره ۲۰٪.", dict(extra_hit=0.20))
pas("undying_shell", "Undying Shell", "lock", "مرگ فقط با دو ضربه‌ی متوالی ممکن است.", dict(shell=True))
pas("siphon_crown", "Devouring Crown", "crown", "هر ضربه ۸٪ HP می‌مکد.", dict(lifesteal=0.08))
pas("chain_lord", "Chain Lord", "boss", "در نبردهای چندنفره آسیب +۲۰٪.", dict(mob_bonus=0.20))
pas("winter_engine", "Winter Engine", "ice", "هر ۴ نوبت محیط را یخ‌زده می‌کند (سرعت حریف −۲۰٪).", dict(periodic_freeze=4))
pas("young_trickster", "Playful Predator", "suko", "جاخالی +۱۴٪ اما آسیب −۸٪.", dict(dodge=0.14, dmg=-0.08))
pas("storm_wings", "Storm Wings", "ocean", "در طوفان/آب، آسیب +۱۸٪.", dict(home_bonus=0.18))
pas("brood_mother", "Brood Mother", "queen", "هر چهار نوبت، یک بچه‌تایتان ۲۵٪ آسیب اضافه می‌کند.", dict(spawn=4))
pas("grove_walker", "Living Grove", "jungle", "ترمیم ۲.۵٪ و مقاومت سم کامل.", dict(regen_pct=0.025, immune="acid|venom"))
pas("eldritch_root", "Elder Memory", "methuselah", "دفاع +۱۰٪ و بی‌نیازی از جریمه‌ی محیط.", dict(df=0.10, no_env_pen=True))
pas("swamp_ambush", "Mire Ambush", "jungle", "ضربه‌ی اول پس از گارد، +۲۵٪.", dict(counter_bonus=0.25))
pas("molt_armor", "Molting Armor", "abaddon", "وقتی زیر ۴۰٪ HP است دفاع +۲۵٪.", dict(berserk_def=0.25))
pas("sonic_lord", "Resonant King", "muto", "نیم‌سازهای فلج‌شده ۳۰٪ آسیب بیشتر می‌گیرند.", dict(vs_stun=0.30))
pas("hollow_apex", "Apex of the Hollow", "skullcrawler", "در زمین توخالی/جنگل آسیب +۲۰٪.", dict(home_bonus=0.20))
pas("leaper", "Bounding Charge", "gorosaurus", "اولین حمله‌ی هر نبرد +۲۰٪.", dict(opener=0.20))
pas("pack_hunter", "Pack Hunter", "kamacuras", "هر متحد در میدان +۶٪ آسیب (سقف +۲۴٪).", dict(per_ally=0.06))
pas("ambush_webs", "Web Ambush", "kumonga", "حریفِ فلج‌شده ۲۵٪ آسیب بیشتر می‌بیند.", dict(vs_stun=0.25))
pas("guardian_ward", "Ward of the Shrine", "caesar", "یک سپر رایگان ۵۰٪ در ابتدای نبرد.", dict(start_shield=0.5))
pas("stoic", "Instinct", "file", "هیچ مزیت ویژه؛ فقط غریزه.", {})


def get(aid: str):
    return ABILITIES.get(aid) or ABILITIES["strike_basic"]


def for_titan(tid: str):
    """مهارت‌های قابل‌استفاده‌ی اکسِ یک تایتان (بدون اولتیمیت)."""
    import titans
    t = titans.get(tid)
    return [get(a) for a in (t or {}).get("ab", []) if a in ABILITIES]


def ult_of(tid: str):
    import titans
    t = titans.get(tid)
    return get(t["ult"]) if t and t.get("ult") in ABILITIES else None


def passive_of(tid: str):
    import titans
    t = titans.get(tid)
    return PASSIVES.get((t or {}).get("pas", "stoic"), PASSIVES.get("stoic"))


# ─────────── همگام‌سازی کیت‌ها (Ability/Ultimate/Passive تعریف‌نشده) ───────────
def sync_kits() -> dict:
    """هر شناسه‌ای که titans.py ارجاع می‌دهد و اینجا تعریف نشده، ساخته می‌شود.

    سقف‌ها در kits.py نگهبانی می‌کنند: Ultimate گران + شرط‌دار + Cooldown بلند،
    پس هیچ کیتی «دکمه‌ی جادویی» نیست. data/kits.json پوششِ دستیِ بدونِ کد است.
    """
    import titans as _T
    import kits
    r = kits.synthesize(ABILITIES, PASSIVES, _T.TITANS)
    for _a in ABILITIES.values():
        _a["emj"] = EMJ.of(_a.get("emj"), "☄️")
    return r


STATS = sync_kits()

# 🈂️ قراردادِ متنی: هر نامِ لاتینِ باقی‌مانده (از جمله مهارت‌های سنتز‌شده و اورلی‌های
# data/kits.json) در زمانِ بارگذاری فارسی می‌شود؛ `en` برای جست‌وجو/لاگ می‌ماند.
import fa as _fa
_fa.fix(ABILITIES)
_fa.fix(PASSIVES)
for _p in PASSIVES.values():
    _p["emj"] = EMJ.of(_p.get("emj"), "🧬")
