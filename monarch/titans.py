# 🦖 Titan Database — دیتابیس رسمی تایتان‌ها (قابل توسعه بدون دست‌زدن به کد)
# هر ردیف یک تایتان واقعی/رسمی است. برای افزودن تایتان جدید کافی است یک فایل
# JSON در data/titans/ بگذاری (ادغام خودکار) یا ردیف جدید به ROWS اضافه کنی.
import json
import os

import emoji as EMJ

COLS = ("id", "name", "emj", "cat", "rar", "threat", "hp", "atk", "df", "spd",
        "eng", "int", "reg", "acc", "dodge", "res", "tags", "weak", "resist",
        "env", "ab", "ult", "pas", "origin", "h", "w", "lore")

RARITY = {
    "RECON":    dict(idx=0, name="شناسایی سبک", cls="از‌طبقه‌خارج‌شده", mult=1.00),
    "RARE":     dict(idx=1, name="کمیاب", cls="محدود", mult=1.16),
    "ELITE":    dict(idx=2, name="الیت", cls="محرمانه", mult=1.34),
    "ALPHA":    dict(idx=3, name="آلفا", cls="سری", mult=1.58),
    "LEGENDARY": dict(idx=4, name="افسانه‌ای", cls="سطحِ امگا", mult=1.86),
    "OMEGA":    dict(idx=5, name="کلاسیفای‌د/امگا", cls="فقط فرمانده", mult=2.10),
}

ENVS = {
    "ocean": "🌊 اقیانوس", "city": "🏙 شهر ویران", "volcano": "🌋 آتشفشان",
    "antarctica": "❄️ جنوبگان", "jungle": "🌲 جنگل", "hollow": "🕳 زمین توخالی",
    "nuclear": "☢️ منطقه‌ی هسته‌ای", "space": "🌌 فضا",
}

# (id, name, emj-key, cat, rar, threat, hp, atk, df, spd, eng, int, reg, acc, dodge, res,
#  tags, weak, resist, env-boost, abilities, ultimate, passive, origin, height, weight, lore)
ROWS = [
 ("godzilla", "گودزیلا", "godzilla", "godzilla", "LEGENDARY", 5, 9800, 640, 620, 96, 620, 430, 300, 84, 18, 560,
  "atomic|brute", "oxygen|sonic", "radiation|fire|electric", "nuclear:1.34|ocean:1.22|city:1.12",
  "atomic_pulse|tail_sweep|nuclear_grasp|alpha_roar", "atomic_breath", "alpha_presence",
  "هایسی / جهانِ هیولاها", "119 متر", "99630 تن", "پادشاه تایتان‌ها. انرژی‌اش بی‌پایان نیست، اما هر نفسش یک شهر را عوض می‌کند."),
 ("kong", "کونگ", "kong", "monsterverse", "ALPHA", 4, 7600, 610, 470, 168, 420, 520, 190, 92, 34, 300,
  "brute|tech", "atomic|acid", "falling|sonic", "jungle:1.26|hollow:1.20|city:1.10",
  "axe_slam|ground_pound|sign_language|feral_grapple", "battle_axe", "combat_intel",
  "جزیرۀ جمجمه", "102 متر", "—"  , "مغز می‌جنگد، نه فقط بازو. سپرِ نبردِ هوشمند."),
 ("mothra", "موترا", "mothra", "kaiju", "LEGENDARY", 4, 6200, 470, 520, 182, 560, 600, 240, 90, 40, 520,
  "light|silk", "dark|acid", "psychic|sonic", "jungle:1.30|city:1.14|ocean:1.10",
  "imago_scale|silk_bind|protective_barrier|telepathic_song", "rebirth_light", "guardian_vow",
  "موترا در برابر گودزیلا", "100 متر", "—"  , "نگهبانِ زمین؛ وقتی می‌میرد، از تخم بازمی‌گردد."),
 ("king_ghidorah", "کینگ گیدوره", "ghidorah", "kaiju", "LEGENDARY", 5, 9100, 680, 520, 176, 580, 460, 280, 86, 26, 380,
  "storm|gravity", "light|ice", "electric|atomic", "space:1.28|city:1.20|ocean:1.16",
  "gravity_beam|storm_front|neck_constrict|dark_current", "gravity_ray_storm", "three_heads",
  "گیدوره، هیولای سه‌سر", "158 متر", "141966 تن", "هر سر یک اراده دارد؛ طوفان، اثر جانبی است."),
 ("rodan", "رودان", "rodan", "kaiju", "ELITE", 3, 4800, 470, 340, 244, 380, 300, 130, 88, 46, 260,
  "fire|volcanic|flight", "ice|sonic", "falling|ash", "volcano:1.36|city:1.12|hollow:1.08",
  "plasma_breath|supersonic_dive|ash_cloud|wing_gust", "firestorm_spiral", "flight_master",
  "رودان", "70 متر", "—"  , "قبل از اینکه صدا را بشنوی، بال‌هایش رد شده است."),
 ("mechagodzilla", "مکاگودزیلا", "mecha", "kaiju", "LEGENDARY", 5, 8800, 660, 700, 130, 700, 560, 60, 96, 14, 560,
  "tech|mech|atomic", "acid|gravity", "fire|electric|psychic", "city:1.30|space:1.18|nuclear:1.16",
  "proton_scream|missile_barrage|target_lock|titanium_jaw", "absolute_annihilation", "machine_core",
  "گودزیلا در برابر مکاگودزیلا", "100 متر", "—"  , "هیچ دردی را حس نمی‌کند؛ اما داغ می‌کند. گرمای بیش‌ازحد تنها دشمن اوست."),
 ("anguirus", "آنجیروس", "anguirus", "kaiju", "RARE", 2, 4200, 380, 520, 138, 300, 240, 190, 82, 28, 300,
  "brute|burrow", "sonic|tech", "fire|falling", "volcano:1.24|city:1.16|jungle:1.10",
  "spiny_roll|burrow_ambush|tail_flail|protect_instinct", "aegis_of_the_ancient", "guardian_link",
  "گودزیلا دوباره حمله می‌کند", "60 متر", "—"  , "سپر زنده‌ی گودزیلا؛ وقتی کنار اوست، پادشاه نمی‌افتد."),
 ("destoroyah", "دسترویا", "destoroyah", "kaijs", "LEGENDARY", 5, 7400, 640, 430, 210, 520, 480, 300, 90, 40, 340,
  "oxygen|fire|flight", "atomic|ice", "acid|brute", "city:1.28|nuclear:1.34|jungle:1.16",
  "microoxygen_beam|agony_shoot|ash_form|cell_swarm", "perfection_ascends", "adaptive_evolution",
  "گودزیلا در برابر دسترویا", "120 متر", "—"  , "از ریزسلول‌های مرگ ساخته شده و در هر فاز، شکل را عوض می‌کند."),
 ("spacegodzilla", "اسپیس‌گودزیلا", "spacegod", "godzilla", "LEGENDARY", 5, 8200, 620, 600, 150, 660, 470, 260, 88, 24, 520,
  "crystal|atomic|ice", "sonic|brute", "fire|electric|acid", "space:1.34|city:1.24|antarctica:1.30",
  "crystal_array|corona_beam|diameter_cage|reflective_shield", "corona_burst_max", "crystal_growth",
  "گودزیلا در برابر اسپیس‌گودزیلا", "100 متر", "—"  , "هر بلور، یک آینه؛ هر آینه، یک مرگ."),
 ("biollante", "بیولانت", "biollante", "kaiju", "ELITE", 3, 6000, 470, 460, 96, 460, 520, 420, 74, 18, 400,
  "plant|acid|brute", "fire|sonic", "cold|brute", "jungle:1.32|city:1.18|nuclear:1.12",
  "vine_lash|acid_spray|seed_barrage|cell_absorb", "floral_consumption", "green_regen",
  "گودزیلا در برابر بیولانت", "80 متر", "—"  , "نیمی گل، نیمی کابوس؛ ریشه‌هایش در DNA گودزیلا گره خورده‌اند."),
 ("gigan", "گیگان", "gigan", "kaiju", "ELITE", 3, 5400, 540, 430, 190, 480, 360, 150, 90, 30, 380,
  "mech|atomic|blade", "sonic|gravity", "fire|acid|brute", "city:1.26|space:1.14|nuclear:1.12",
  "cyclops_beam|spinner_blade|chest_cannon|buzzer_saw", "cybernetic_execution", "cyber_enhanced",
  "گودزیلا در برابر گیگان", "65 متر", "—"  , "سازندگانش او را برای کشتن پادشاه ساختند؛ پادشاه زنده ماند."),
 ("hedorah", "هدورا", "hedorah", "kaiju", "ELITE", 4, 5200, 430, 500, 132, 460, 400, 380, 78, 26, 460,
  "acid|venom|pollution", "electric|fire", "brute|poison|acid", "city:1.34|ocean:1.24|nuclear:1.18",
  "acid_fog|slime_shard|mineral_absorb|siren_descent", "toxic_dissolution", "corrosive_body",
  "گودزیلا در برابر هیولای دریا", "—"  , "—"  , "محققِ آلودگی؛ از دود بزرگ شد و از خشکی می‌ترسد."),
 ("megalon", "مگالون", "megalon", "kaiju", "RECON", 1, 3000, 300, 300, 118, 220, 220, 130, 76, 24, 200,
  "burrow|drill|brute", "sonic|tech", "falling|brute", "city:1.18|volcano:1.16|jungle:1.08",
  "drill_hands|burrow_charge|horn_burst|boomerang_shield", "pyre_spiral", "burrower",
  "گودزیلا در برابر مِگالون", "55 متر", "—"  , "نماینده‌ی جهان زیرین، با دست‌های مته‌ای."),
 ("king_caesar", "کینگ سزار", "caesar", "kaiju", "RARE", 2, 4400, 380, 600, 140, 320, 380, 180, 80, 30, 420,
  "brute|guardian|light", "acid|gravity", "atomic|fire", "city:1.22|jungle:1.16",
  "guardian_roar|fang_rush|elastic_tail|spirit_ward", "shisa_ward", "guardian_ward",
  "گودزیلا در برابر مکاگودزیلا", "30 متر", "—"  , "مجسمه‌ای که فقط وقتی شهر در خطر است، زنده می‌شود."),
 ("titanosaurus", "تایتانوسوروس", "titanosaurus", "kaiju", "RARE", 2, 4300, 400, 360, 126, 300, 280, 160, 82, 26, 300,
  "sonic|aquatic|brute", "sonic|electric", "cold|pressure", "ocean:1.32|city:1.10",
  "sonic_wail|tail_sweep|whirlpool_slam|depth_ambush", "resonance_collapse", "aquatic_pulse",
  "وحشتِ گودزیلا", "60 متر", "—"  , "فریادش استخوان را می‌لرزاند؛ در آب، تقریباً مغلوب‌ناپذیر."),
 ("battra", "باترا", "battra", "kaiju", "ALPHA", 4, 5600, 520, 470, 208, 480, 460, 240, 90, 42, 400,
  "light|silk|storm", "dark|acid", "sonic|psychic", "jungle:1.28|city:1.20|volcano:1.14",
  "prismatic_lance|obsidian_dust|tusk_charge|darkness_shroud", "planet_cleanser", "dark_guardian",
  "گودزیلا در برابر موترا", "68 متر", "—"  , "برادر تاریک مothra؛ عدالت را با انتقام می‌آمیزد."),
 ("jet_jaguar", "جت جاگار", "jet", "kaiju", "RARE", 1, 2800, 300, 260, 260, 380, 480, 60, 92, 52, 240,
  "tech|flight", "gravity|acid", "fire|electric", "city:1.24|space:1.10",
  "missile_fist|jet_dash|grow_protocol|scan_lock", "max_thrust_overdrive", "machine_core",
  "گودزیلا در برابر مِگالون", "60m→40m", "—"  , "رباتِ آزاد؛ اندازه را خودش انتخاب می‌کند."),
 ("moguera", "M.O.G.U.E.R.A.", "moguera", "kaiju", "RARE", 2, 3400, 340, 420, 150, 420, 440, 70, 88, 22, 360,
  "tech|mech", "acid|brute", "fire|electric", "city:1.22|antarctica:1.20",
  "ga_plasma|drill_arms|shield_generator|lockon_turret", "geo_cannon_overload", "machine_core",
  "زادگاه دوباره‌ی موترا ۳", "50 متر", "—"  , "تانکِ مداری مانارچ؛ در جنوبگان متولد شده."),
 ("baragon", "باراگون", "baragon", "kaiju", "RECON", 1, 2600, 280, 280, 160, 220, 240, 130, 80, 36, 200,
  "fire|burrow", "ice|tech", "falling|ash", "volcano:1.30|jungle:1.14",
  "earthen_ray|tunnel_ambush|big_ears_defense|horn_lance", "subterranean_detonation", "burrower",
  "فرانکنشتاین در برابر باراگون", "45 متر", "—"  , "گوش‌هایش را می‌بندد، سپس زمین را می‌شکافد."),
 ("kumonga", "کومونگا", "kumonga", "kaiju", "RECON", 1, 2400, 300, 240, 172, 200, 220, 140, 84, 40, 180,
  "silk|venom|brute", "fire|sonic", "acid|brute", "jungle:1.30|hollow:1.20|volcano:1.12",
  "silk_snare|venom_bite|web_tunnel|eye_beam", "nest_wraps_all", "ambush_webs"),
 ("kamacuras", "کاماکوراس", "kamacuras", "kaiju", "RECON", 1, 2000, 260, 200, 214, 180, 180, 120, 86, 48, 140,
  "brute|burrow", "fire|sonic", "acid", "jungle:1.26|volcano:1.10",
  "drill_arms|pack_swarm|prey_drag|burrow_trip", "triple_swarm_flurry", "pack_hunter"),
 ("ebirah", "ابیرا", "ebirah", "kaiju", "RARE", 2, 3600, 380, 340, 128, 260, 200, 150, 78, 24, 280,
  "aquatic|electric|brute", "electric|sonic", "cold|pressure", "ocean:1.36|city:1.06",
  "electro_claw|crustacean_crush|ink_screen|rip_current", "double_claw_execution", "aquatic_pulse"),
 ("manda", "ماندا", "manda", "kaiju", "RARE", 2, 4000, 360, 320, 140, 280, 320, 170, 80, 30, 280,
  "aquatic|silk|brute", "fire|sonic", "pressure|acid", "ocean:1.34|city:1.14",
  "coil_crush|tail_lash|deep_drag|glow_bait", "continent_strangle", "aquatic_pulse"),
 ("gorosaurus", "گوروسوروس", "gorosaurus", "kaiju", "RECON", 1, 2900, 320, 280, 176, 220, 200, 130, 82, 38, 200,
  "brute", "sonic|tech", "acid|falling", "jungle:1.24|city:1.16",
  "kangaroo_kick|tail_axe|bounding_charge|dust_screen", "double_kick_finisher", "leaper"),
 ("varan", "وران", "varan", "kaiju", "RECON", 1, 2300, 280, 240, 220, 200, 240, 130, 84, 46, 160,
  "flight|brute", "ice|sonic", "falling", "jungle:1.26|city:1.12",
  "glide_rake|wing_blast|cry_dive|claw_snag", "skyhunter_rush", "flight_master"),
 ("orga", "اورگا", "orga", "kaiju", "ALPHA", 4, 6000, 560, 430, 156, 420, 380, 260, 84, 26, 380,
  "brute|void", "gravity|sonic", "atomic|fire|acid", "city:1.22|volcano:1.18",
  "void_claw|energy_absorb|arm_fang|tail_whip", "annihilation_wave_copy", "absorption"),
 ("megaguirus", "مگاگیروس", "megaguirus", "kaiju", "ELITE", 3, 3800, 420, 300, 230, 360, 320, 190, 88, 44, 260,
  "fire|drain|flight", "electric|ice", "brute|acid", "city:1.24|jungle:1.16",
  "quantum_swarm|micro_bug_storm|solar_ring|plasma_sting", "annihilation_ring", "swarm_mind"),
 ("monster_x", "مانستر ایکس", "monsterx", "kaiju", "LEGENDARY", 5, 7200, 600, 640, 110, 620, 500, 300, 86, 12, 560,
  "void|dark", "light|sonic", "atomic|fire|acid|electric", "space:1.30|nuclear:1.26|city:1.20",
  "dark_matter_barrier|void_beam|corpse_regeneration|black_hole_pulse", "the_beast_rises", "undying_shell"),
 ("keizer_ghidorah", "کایزر گیدوره", "keizer", "kaiju", "OMEGA", 5, 9400, 700, 560, 170, 700, 520, 380, 88, 24, 520,
  "gravity|void|storm", "light|oxygen", "atomic|fire|acid", "space:1.34|city:1.26",
  "gravity_clamp|energy_siphon|neck_bite_lock|storm_call", "planet_devour", "siphon_crown"),
 ("skar_king", "اسکار کینگ", "skar", "monsterverse", "OMEGA", 5, 8600, 660, 540, 190, 600, 480, 300, 88, 30, 460,
  "brute|void|tech", "light|fire", "atomic|acid", "hollow:1.38|jungle:1.20",
  "monollith_whip|beast_chain|bone_bolt|domination_roar", "chain_of_command", "chain_lord"),
 ("shimo", "شیمو", "shimo", "monsterverse", "LEGENDARY", 5, 8000, 620, 560, 140, 580, 440, 320, 84, 20, 520,
  "ice|storm", "fire|atomic", "cold|acid|pressure", "antarctica:1.40|ocean:1.18|space:1.16",
  "frost_breath|glacial_spikes|ice_age_cloud|tail_quake", "absolute_zero_front", "winter_engine"),
 ("suko", "سوکو", "suko", "monsterverse", "RECON", 1, 2100, 260, 220, 226, 180, 300, 140, 88, 52, 140,
  "brute|flight", "sonic|acid", "falling", "jungle:1.30|hollow:1.18",
  "feather_stab|sky_dive|three_head_decoy|wind_shear", "feathered_fury", "young_trickster"),
 ("tiamat", "تیامت", "tiamat", "monsterverse", "ELITE", 3, 5000, 440, 400, 208, 340, 300, 200, 84, 40, 320,
  "aquatic|flight|storm", "sonic|ice", "pressure|cold", "ocean:1.36|city:1.16",
  "tidal_wing|salt_lash|dive_bomb|maelidon_call", "oceanic_rending", "storm_wings"),
 ("scylla", "سیلا", "scylla", "monsterverse", "ELITE", 3, 5200, 430, 440, 120, 320, 300, 220, 78, 22, 360,
  "aquatic|brute", "fire|sonic", "pressure|acid", "ocean:1.34|hollow:1.14",
  "tentacle_gale|toxic_ink|shell_crush|abyss_pull", "army_of_the_deep", "brood_mother"),
 ("behemoth", "بیهیموث", "behemoth", "monsterverse", "ELITE", 2, 5400, 420, 480, 110, 300, 320, 210, 76, 18, 340,
  "plant|brute", "fire|sonic", "acid|psychic", "jungle:1.34|hollow:1.22",
  "vine_mace|stampede|spore_bloom|root_hold", "green_hammer", "grove_walker"),
 ("methuselah", "متوشالح", "methuselah", "monsterverse", "ELITE", 3, 5000, 400, 460, 118, 360, 420, 240, 78, 20, 380,
  "plant|brute|light", "fire|acid", "sonic|psychic", "jungle:1.32|hollow:1.16",
  "canopy_slam|ancient_gaze|branch_lash|photosynth_field", "one_thousand_rings", "eldritch_root"),
 ("amhuluk", "امهولوک", "amhuluk", "monsterverse", "RARE", 2, 4200, 380, 360, 128, 280, 300, 190, 78, 24, 280,
  "aquatic|lightning", "fire|tech", "acid|pressure", "ocean:1.30|jungle:1.22",
  "electro_net|mire_lure|pincer_snap|bog_silence", "marsh_discharge", "swamp_ambush"),
 ("abaddon", "ابدون", "abaddon", "monsterverse", "ELITE", 3, 4800, 440, 420, 146, 300, 340, 200, 80, 26, 320,
  "brute|plague", "fire|light", "acid|venom", "hollow:1.30|jungle:1.20",
  "molt_whip|carapace_charge|parasite_spit|den_collapse", "exoskeletal_rage", "molt_armor"),
 ("muto_prime", "موتوی اصلی", "muto", "monsterverse", "ALPHA", 4, 6000, 520, 420, 216, 400, 360, 210, 88, 42, 320,
  "sonic|flight|brute", "atomic|ice", "fire|tech", "city:1.26|ocean:1.18|jungle:1.14",
  "resonance_call|silence_barrage|aerial_rake|nest_defense", "planet_cracker_chorus", "sonic_lord"),
 ("skullcrawler", "اسکال‌کراولر", "skullcrawler", "monsterverse", "RECON", 1, 2600, 320, 220, 190, 180, 200, 150, 82, 40, 160,
  "brute|ambush", "fire|tech", "acid|falling", "jungle:1.34|hollow:1.24",
  "skull_crush|burrow_snap|acid_spit|nest_drag", "apex_of_the_isle", "hollow_apex"),
 ("warbat", "واربت", "warbat", "monsterverse", "RECON", 1, 2000, 280, 200, 240, 180, 220, 130, 86, 50, 150,
  "flight|brute", "sonic|ice", "acid", "hollow:1.30|jungle:1.18",
  "wing_gust|talon_rip|swarm_dive|screech", "skull_island_cyclone", "flight_master"),
 ("muto_minion", "لانهٔ موتو", "muto", "monsterverse", "RECON", 1, 2200, 300, 240, 200, 200, 200, 140, 80, 44, 170,
  "sonic|brute", "atomic|fire", "tech", "city:1.22|hollow:1.18",
  "silk_bind|resonance_screech|claw_rake|burrow_egg", "swarm_resonance", "pack_hunter"),
]

# ستون‌های اختصاری برای ردیف‌های کوتاه‌شده (origin/h/w/lore در صورت نبود)
_DEFAULT_TAIL = dict(origin="توهو / جهانِ هیولاها", h="—", w="—",
                     lore="پرونده‌ی کلاسیفای‌د — دسترسی با Research باز می‌شود.")

TITANS: dict = {}


def sync_kits():
    """کیت‌های تازه (یا تایتانِ افزوده‌شده با overlay) را بلافاصله بساز."""
    try:
        import abilities
        abilities.sync_kits()
    except Exception:
        pass
BY_NAME: dict = {}


def _parse_env(s: str) -> dict:
    out = {}
    for part in (s or "").split("|"):
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip()] = float(v)
    return out


def build():
    for row in ROWS:
        d = dict(zip(COLS, row))
        for k, v in _DEFAULT_TAIL.items():
            d.setdefault(k, v)
        d["emj"] = EMJ.of(d.get("emj") or "file")
        d["env"] = _parse_env(d.get("env", ""))
        d["tags"] = [x for x in d.get("tags", "").split("|") if x]
        d["weak"] = [x for x in d.get("weak", "").split("|") if x]
        d["resist"] = [x for x in d.get("resist", "").split("|") if x]
        d["ab"] = [x for x in d.get("ab", "").split("|") if x]
        d["pas"] = d.get("pas") or "stoic"
        d["cat"] = "godzilla" if d["id"] in ("godzilla", "spacegodzilla") else d.get("cat")
        if d.get("cat") == "kaijs":
            d["cat"] = "kaiju"
        d["power"] = round(
            d["hp"] * 0.42 + d["atk"] * 2.1 + d["df"] * 1.6 + d["spd"] * 0.9 +
            d["eng"] * 0.5 + d["int"] * 0.5 + d["reg"] * 0.8 + d["res"] * 0.9, 1)
        TITANS[d["id"]] = d
        BY_NAME[d["name"].lower()] = d["id"]


def load_overlays(path: str = None):
    """➕ توسعه‌پذیری: هر JSON در data/titans/*.json روی دیتابیس سوار می‌شود.
    فایل می‌تواند تایتان جدید بدهد یا فیلدهای موجود را patch کند."""
    d = path or os.path.join(os.path.dirname(__file__), "data", "titans")
    n = 0
    if not os.path.isdir(d):
        return 0
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(d, fn), encoding="utf-8") as f:
                blob = json.load(f)
        except Exception:
            continue
        for item in (blob if isinstance(blob, list) else [blob]):
            tid = item.get("id")
            if not tid:
                continue
            if tid in TITANS:
                TITANS[tid].update(item)
            else:
                base = dict(TITANS.get("godzilla") or {})
                base.update(item)
                base["env"] = _parse_env(base.get("env") or "") if isinstance(base.get("env"), str) else {}
                for key in ("tags", "weak", "resist", "ab"):
                    if isinstance(base.get(key), str):
                        base[key] = [x for x in base[key].split("|") if x]
                base.setdefault("cat", "custom")
                base.setdefault("rar", "RARE")
                base.setdefault("threat", 2)
                base.setdefault("ult", base["ab"][0] if base.get("ab") else "strike")
                base.setdefault("passive", "stoic")
                base.setdefault("pas", "stoic")
                base.setdefault("origin", "افزوده‌شده")
                base.setdefault("h", "—")
                base.setdefault("w", "—")
                base.setdefault("lore", "پرونده‌ی تازه — در حال راستی‌آزمایی مانارچ.")
                TITANS[tid] = base
            n += 1
    if n:
        for t in TITANS.values():
            t["power"] = round(
                t["hp"] * 0.42 + t["atk"] * 2.1 + t["df"] * 1.6 + t["spd"] * 0.9 +
                t["eng"] * 0.5 + t["int"] * 0.5 + t["reg"] * 0.8 + t["res"] * 0.9, 1)
        sync_kits()
    return n


def get(tid: str):
    return TITANS.get(tid)


def all_ids():
    return list(TITANS.keys())


def by_rarity(rar: str):
    return [t for t in TITANS.values() if t["rar"] == rar]


def by_cat(cat: str):
    return [t for t in TITANS.values() if t.get("cat") == cat]


def search(q: str):
    """جست‌وجوی فارسی/انگلیسی/آلایاس."""
    q = (q or "").strip().lower()
    if not q:
        return []
    out = []
    for t in TITANS.values():
        hay = f'{t["id"]} {t["name"]} {t.get("alias", "")} {t.get("cat","")}'.lower()
        if q in hay or q.replace(" ", "") in hay.replace(" ", ""):
            out.append(t)
    return out


def roster(chat=None):
    """لیست نمایشی با پرچم کلاسیفیکیشن (هیچ‌چیز از اول لو نمی‌رود)."""
    return sorted(TITANS.values(), key=lambda t: (-t["power"], t["name"]))


build()
sync_kits()
load_overlays()
