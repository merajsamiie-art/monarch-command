# 🈂️ Fa — فارسی‌سازی نام‌های برچسبی (مهارت/فاز/وضعیت/رتبه)
"""قرارداد متنیِ MONARCH: هر چیزی که بازیکن می‌خواند فارسی است؛ لاتین فقط در
`id`ها و دستورهای اسلش می‌ماند (چون تلگرام آن‌ها را لاتین می‌خواهد).

این ماژول دو کار می‌کند:
  ۱) ترجمه‌ی ترکیبی: «Atomic Breath» → «تنفسِ اتمی» (سرِ ترکیب = واژه‌ی آخر، همان‌طور
     که در فارسی صفت پس از موصوف می‌آید).
  ۲) آوانگاری برای واژه‌ی ناشناخته → هیچ حرف لاتینی در متنِ کاربر باقی نمی‌ماند.

`name` اصلی در `en` نگه داشته می‌شود تا جست‌وجو/لاگ/دیتابیسِ اورلی نشکنند.
"""
import re

TOK = { "basic":"پایه", "standard":"استاندارد", "strike":"ضربه", "attack":"حمله", "heavy":"سنگین", "light":"نور", "quick":"سریع",
  "swift":"چابک", "slow":"کند", "power":"توان", "force":"زور", "might":"نیرu", "guard":"سپر", "dodge":"جاخالی", "counter":"ضدحمله",
  "charge":"شارژ", "retreat":"عقب‌نشینی", "ability":"مهارت", "ultimate":"ضربه‌ی نهایی", "overdrive":"بیش‌ران", "overheat":"داغی",
  "cooldown":"خاموشی", "atomic":"اتمی", "nuclear":"هسته‌ای", "radiation":"پرتوافکنی", "radioactive":"پرتوزا", "fission":"شکافت",
  "fusion":"همجوشی", "isotope":"ایزوتوپ", "meltdown":"ذوبِ راکتور", "reactor":"راکتور", "plasma":"پلاسما", "photon":"فوتون",
  "electron":"الکترون", "quantum":"کوانتومی", "ion":"یون", "electric":"برقی", "electro":"برقی", "thunder":"رعد", "storm":"طوفان",
  "lightning":"رعدخیز", "spark":"جرقه", "tesla":"تسلا", "emp":"پالس", "pulse":"تپش", "breath":"تنفس", "flame":"شعله", "fire":"آتش",
  "inferno":"آتشدان", "burn":"سوختن", "burning":"سوزان", "ember":"ژواره", "ash":"خاکستر", "cinder":"خاکسترِ سوزان", "magma":"ماگما",
  "lava":"گدازه", "volcano":"آتشفشان", "volcanic":"آتشفشانی", "eruption":"فوران", "pyroclastic":"خاکسترافکن", "thermal":"حرارتی",
  "combustion":"احتراق", "ignite":"افروختن", "cryo":"برفی", "ice":"یخ", "frost":"یخ", "freeze":"انجماد", "glacier":"یخچال",
  "winter":"زمستان", "blizzard":"توفان‌برفی", "cold":"سرمای", "absolute":"مطلق", "zero":"صفر", "shatter":"ریختن", "ocean":"اقیانوس",
  "tide":"جزر‌ومد", "water":"آب", "wave":"موج", "current":"جریان", "dark":"تاریک", "darkness":"تاریکی", "shine":"درخشش", "glow":"تابش",
  "luminescent":"تابان", "whirl":"چرخش", "maelstrom":"گرداب", "tsunami":"سونامی", "flood":"سیلاب", "depth":"ژرفا", "deep":"ژرفا",
  "abyss":"هیاهو", "pressure":"فشار", "hydraulic":"هیدرولیک", "rip":"کشیدن", "undertow":"مکشِ ژرفا", "tidal":"جزر‌ومدی", "reaver":"غارتگر",
  "crustacean":"صدف‌پوست", "claw":"چنگال", "pincer":"انبرک", "shell":"صدف", "carapace":"سپروار", "spike":"خار", "barb":"باریکه",
  "tail":"دم", "sweep":"جارو", "quake":"لرزه", "quake_drums":"طبل‌های لرزه", "tremor":"لرزه", "seismic":"لرزه‌ای", "burrow":"کندن",
  "subterranean":"زیرزمینی", "tunnel":"تونل", "dig":"کندن", "sink":"فروبردن", "rock":"سنگ", "stone":"سنگ", "boulder":"تخته‌سنگ",
  "granite":"گرانیت", "bedrock":"تختۀ سنگی", "crystal":"بلور", "crystal_grasp":"چنگِ بلور", "diamond":"الماس", "obsidian":"ابسیدین",
  "prism":"منشور", "array":"آرایه", "geo":"زمین", "earth":"خاک", "landslide":"رانش", "land_burrower":"کَنده‌ی سرزمین", "crush":"کوبش",
  "crushing":"کوبنده", "pound":"کوبیدن", "ground":"زمین", "hammer":"چکش", "maul":"گرگ‌آسا", "slam":"فرود", "stomp":"کوبش‌پا", "kick":"لگد",
  "trample":"کوبیدن", "hoof":"سم", "horn":"شاخ", "tusk":"دندان‌گاو", "jaw":"فک", "fang":"دندان", "bite":"گاز", "chomp":"لقمه",
  "gnaw":"جوندن", "tear":"پارگی", "rend":"درید", "shred":"تکه‌تکه", "slash":"برش", "slice":"برش", "blade":"تیغه", "sword":"شمشیر",
  "axe":"تبر", "war_axe":"تبرِ جنگی", "saw":"اره", "buzzsaw":"اره‌برقی", "buzzer":"اره", "lance":"نیزه", "spear":"نیزه",
  "harpoon":"نیزه‌انداز", "arrow":"پیکان", "bolt":"پیکان", "missile":"موشک", "cannon":"توپ", "gun":"توپ", "chest":"سینه",
  "shoulder":"شانه", "arm":"بازو", "fist":"مشت", "punch":"مشت‌زدن", "elbow":"آرنج", "wing":"بال", "buffet":"بال‌زدن", "flap":"بال‌زدن",
  "feather":"پَر", "quill":"پَرِ تیز", "spine":"ستون", "frill":"یقه", "fin":"باله", "gill":"آبشش", "scale":"اِسکیل", "scales":"اِسکیل",
  "dust":"گرد", "powder":"پودر", "sand":"شن", "grit":"شن‌ریزه", "mirage":"سراب", "sandstorm":"طوفان‌شن", "blast":"انفجار",
  "burst":"انفجار", "detonation":"انفجار", "detonate":"ترکاندن", "explosion":"انفجار", "shock":"ضربه‌ای", "concussion":"مغزکوب",
  "shockwave":"موج‌فشار", "wave_front":"جبهه", "front":"جبهه", "generation":"پدیدآوردن", "projector":"افکن", "emitter":"فرستنده",
  "generator":"تولیدکننده", "field":"میدان", "barrier":"سد", "wall":"دیوار", "bulwark":"سنگر", "aegis":"سپرِ اجیس", "ward":"حفاظت",
  "shielding":"سپرکشی", "protective":"حفاظتی", "protect":"حفاظت", "guardian":"حافظ", "sentinel":"نگهبان", "sentry":"پاسدار",
  "watch":"پایانی", "tower":"برج", "anchor":"لنگر", "chain":"زنجیر", "of":"", "the":"", "a":"", "an":"", "beasts":"درندگان",
  "command":"فرمان", "order":"فرمان", "tactical":"taktیکی", "sign":"نشانه", "signal":"سیگنال", "beacon":"فانوس", "broadcast":"پخش",
  "transmit":"ارسال", "interference":"مزاحمت", "sensor":"حسگر", "sensors":"حسگرها", "scan":"اسکن", "scanner":"اسکنر", "sonar":"سونار",
  "radar":"رادار", "echo":"پژواک", "sonic":"فراصوت", "supersonic":"فراصوت", "infrasonic":"فراصوتِ ژرف", "frequency":"بسامد",
  "resonance":"تشدید", "vibration":"لرزش", "hypersonic":"فراصوتِ بلند", "siren":"آواز", "song":"آواز", "chant":"نیایش", "hymn":"سرود",
  "requiem":"مرثیه", "lullaby":"لالایی", "hymn_of":"سرود", "pestilence":"وبا", "chorus":"همخوانی", "roar":"غرّش", "scream":"جیغ",
  "shriek":"جیغ", "howl":"زوزه", "bellow":"قهقهه", "cry":"فریاد", "yell":"داد", "whistle":"سوت", "growl":"غرغر", "snarl":"پچ‌پچ",
  "mind":"ذهن", "mental":"ذهنی", "psychic":"روانی", "hypnosis":"منیص", "mesmer":"افسون", "charm":"افسون", "terror":"وحشت", "fear":"هراس",
  "dread":"هراس", "panic":"هرج‌ومرج", "agony":"درد", "torment":"عذاب", "nightmare":"کابوس", "dream":"رویا", "vision":"دیدار",
  "veil":"پرده", "shroud":"کفن", "mist":"مه", "fog":"مه", "cloud":"ابر", "smog":"دود", "gas":"گاز", "surge":"جهش", "beams":"پرتوها",
  "beam":"پرتو", "ray":"پرتو", "stream":"جویبار", "dance":"رقص", "cluster":" خوشه", "driver":"راهبر", "grasp":"چنگال", "beak":"نوک",
  "lock":"قفل", "bind":"قفل", "regen":"بازسازی", "regeneration":"بازسازی", "spore":"هاگ", "pollen":"گرده", "toxin":"سم", "venom":"زهر",
  "acid":"اسید", "corrosive":"خورنده", "corrosion":"خوردگی", "antitoxin":"پادzahr", "parasite":"انگل", "leech":"زولو", "siphon":"مکش",
  "drain":"مکش", "absorb":"جذب", "devour":"بلعیدن", "consume":"فراخواندن", "feed":"تغذیه", "digest":"هضم", "regurgitate":"بالاآوردن",
  "vomit":"استفراغ", "spray":"پاشش", "spew":"پاشش", "project":"پرتاب", "acid_spray":"پاششِ اسید", "corrosive_spray":"پاششِ خورنده",
  "acid_cloud":"ابرِ اسید", "acid_fog":"مه‌اسید", "acid_storm":"طوفانِ اسید", "spit":"تف", "swarm":"هجوم", "cloud_storm":"طوفان‌ابر",
  "muto":"موتو", "mothra":"موترا", "moth":"پروانه", "imago":"بالغ", "larva":"لارو", "nymph":"پوره", "egg":"تخم", "cocoon":"پیله",
  "chrysalis":"شفرۀ", "metamorphosis":"دگردیسی", "web":"تار", "silk":"ابریشم", "silk_bind":"گره‌ی ابریشم", "wrap":"پیچیدن", "net":"تور",
  "trap":"تله", "snare":"تله", "sting":"نیش", "mandible":"فکک", "antenna":"شاخک", "compound":"مرکب", "eye":"چشم", "cyclops":"تک‌چشم",
  "optic":"نوری", "vision_ray":"پرتوِ دید", "stare":"نگاه", "gaze":"نگاه", "glare":"خیره", "seismic_sense":"حسِ لرزه", "sense":"حس",
  "spider":"عنکبوت", "crawler":"خزنده", "skull":"جمجمه", "saur":"سور", "dino":"دایناسور", "serpent":"مار", "viper":"mar",
  "anaconda":"آناکوندا", "boa":"بُوا", "mamba":"مآمبا", "kobra":"کوبرا", "spit_cobra":"تفِ اژدها", "reptile":"خزانده", "lizard":"مارمولک",
  "salamander":"سمندر", "gecko":"گکو", "raptor":"درنده", "raptor_boots":"چکمه‌ی درنده", "boots":"چکمه", "gauntlets":"دستکش", "jet":"جت",
  "jaguar":"جاگوار", "panther":"پلنگ", "tiger":"ببر", "lion":"شیر", "wolf":"گرگ", "bear":"خرس", "gorilla":"گوریلا", "kong":"کونگ",
  "kong_battle":"نبرد کونگ", "titan":"تایتان", "beholder":"بیننده", "behemoth":"بیهیموث", "rebirth":"نوزاد", "king":"پادشاه",
  "queen":"ملکه", "queen_battle":"نبرد ملکه", "alpha":"آلفا", "omega":"امگا", "prime":"اصلی", "apex":"قله", "predator":"شکارچی",
  "stalker":"ردیاب", "hunter":"شکارچی", "killer":"قاتل", "reaper":"دریابن", "apocalypse":"آخرالزمان", "annihilation":"نیستی",
  "annihilate":"نست‌کردن", "obliterate":"نیستی‌بخش", "extinction":"انقراض", "doom":"شوم", "omen":"پیش‌نشانه", "judgment":"داوری",
  "judgement":"داوری", "verdict":"حکم", "sentence":"دادخواست", "execution":"اعدام", "punish":"مجازات", "retribution":"جزا",
  "vengeance":"انتقام", "wrath":"خشم", "fury":"خشم", "rage":"خشم", "berserk":"دیوانه‌وار", "berserker":"دیوانه‌وار", "frenzy":"دیواری",
  "adrenaline":"آدرنالین", "blood":"خون", "bloodlust":"تشنگی", "thirst":"تشنگی", "hunger":"گرسنگی", "starve":"گرسنگی",
  "hunt_mode":"حالتِ شکار", "state":"وضعیت", "mode":"حالت", "form":"قالب", "shape":"شکل", "aspect":"رخ", "ascension":"عروج",
  "rise":"برخاستن", "lift":"بالابردن", "summon":"فراخوان", "call":"خواندن", "descent":"فرود", "fall":"سقوط", "collapse":"ریختن",
  "crumble":"ریختن", "corona":"تاج", "corona_beam":"پرتوی تاج", "halo":"هاله", "crown":"تاج", "scepter":"صولجان", "throne":"تخت",
  "empire":"امپراتوری", "dynasty":"سلسله", "protocol":"پروتکل", "override":"تخطّی", "override_lock":"لغوِ قفل",
  "protocol_lock":"قفلِ پروتکل", "unleash":"گشودن", "release":"رهایی", "sever":"بریدن", "bind_lock":"قفلِ بند", "anchor_down":"لنگر",
  "orbital":"مداری", "drop":"انداختن", "sky":"آسمان", "space":"فضا", "cosmic":"کیهانی", "stellar":"ستاره‌ای", "astral":"آسمانی",
  "comet":"دنباله‌دار", "meteor":"شهاب", "meteor_swarm":"هجومِ شهاب", "moon":"ماه", "sun":"خورشید", "eclipse":"گرفتگی", "horizon":"افق",
  "black":"سیاه", "hole":"حفره", "event":"رویداد", "void":"پوچ", "nether":"جهنم", "hell":"دوزخ", "demon":"شیطان", "devil":"ابلیس",
  "angel":"فرشته", "saint":"ولی", "sin":"گناه", "curse":"نفرین", "bless":"برکت", "blessing":"برکت", "purify":"پاک‌سازی",
  "cleanse":"پاک‌سازی", "salvation":"رستگاری", "damnation":"لعنت", "sanctuary":"پناهگاه", "refuge":"پناه", "genesis":"آفرینش",
  "exodus":"ستوه", "revelation":"وحی", "testament":"میثاق", "covenant":"پیمان", "ancient":"باستان", "elder":"ریش‌سفید",
  "primordial":"نهادی", "primal":"نهادی", "forgotten":"فراموش", "eternal":"جاودان", "infinite":"بی‌کران", "infinity":"بی‌کرانی",
  "perfection":"کمال", "perfect":"کامل", "absolute_freeze":"انجمادِ مطلق", "maximum":"بیشینه", "ultra":"فرا", "mega":"ابر",
  "giga":"gableh", "tera":"ترا", "hyper":"ابرو", "super":"فوق", "omni":"همه", "multi":"چند", "poly":"بسیار", "fractal":"بُعد‌کُنج",
  "spiral":"مارپیچ", "helix":"مارپیچ", "gyre":"گردش", "spin":"چرخش", "rotate":"چرخش", "cycle":"چرخه", "circle":"دایره", "ring":"حلقه",
  "array_blast":"انفجارِ آرایه", "lattice":"توری", "matrix":"ماتریکس", "grid":"شبکه", "mesh":"تور", "loom":"داربست", "weave":"بافند",
  "fabric":"بافت", "tissue":"بافت", "fiber":"تار", "wire":"سیم", "coil":"سیم‌پیچ", "capacitor":"خازن", "battery":"باتری", "cell":"پیل",
  "core":"هسته", "shard":"قطعه", "fragment":"پاره", "piece":"تکه", "part":"بخش", "engine":"موتور", "reactor_core":"هسته‌ی راکتور",
  "turbine":"توربین", "piston":"پیستون", "gear":"چرخ‌دنده", "servo":"سرو", "hydraulics":"هیدرولیک", "pneumatic":"بادی", "actuator":"عملگر",
  "chassis":"شاسی", "plating":"صفحه‌پوشی", "rivet":"پرچ", "alloy":"آلیاژ", "titanium":"تیتانیوم", "tungsten":"تنگستن", "steel":"فولاد",
  "iron":"آهن", "metal":"فلز", "chrome":"کروم", "copper":"مس", "zinc":"روی", "lead":"سرب", "mercury":"جیوه", "radium":"رادیم",
  "uranium":"اورانیوم", "cobalt":"کبالت", "nickel":"نیکل", "silver":"نقره", "gold":"طلا", "bronze":"برنز", "copper_shell":"صدفِ مسی",
  "nano":"نانو", "micro":"ریز", "macro":"درشت", "mini":"کوچک", "micro_missile":"موشکِ ریز", "mini_barrage":"بارانِ کوچک",
  "barrage":"بارانِ آتش", "volley":"باران", "salvo":"باران", "hail":"بارانِ تگرگ", "tickle":"قلقلک", "flood_lance":"نیزۀ سیلاب",
  "jungle":"جنگل", "forest":"جنگل", "tree":"درخت", "root":"ریشه", "branch":"شاخه", "vine":"پیچک", "bloom":"شکوفایی", "petal":"گلبرگ",
  "thorn":"خار", "rose":"گلِ سرخ", "flora":"گیاه", "leaf":"برگ", "canopy":"تاجِ درخت", "moss":"خزه", "fern":"سرخس", "bark":"پوستِ درخت",
  "sap":"شیره", "nectar":"شهد", "hive":"کندو", "colony":"کلنی", "brood":"لانه", "nest":"لانه", "queen_brood":"لانه‌ی ملکه", "horde":"لشکر",
  "pack":"گله", "herd":"گله", "pride":"گله", "flock":"دانِه", "swarm_colony":"کلنی", "city":"شهر", "urban":"شهری", "subway":"مترو",
  "tower_block":"برج", "tower_crane":"جرثقیل", "highrise":"آسمان‌خراش", "ruin":"ویرانه", "wreck":"لنگرگاه", "wreck_harbor":"بندرگاهِ لنگر",
  "harbor":"بندر", "port":"بندر", "dock":" اسکله", "isle":"جزیره", "island":"جزیره", "skull_island":"جزیرۀ جمجمه", "cave":"غار",
  "cavern":"غار", "rift":"شکاف", "chasm":"داره", "trench":"خندق", "trench_sweep":"جاروی خندق", "ridge":"یال", "peak":"قله",
  "cliff":"پرتگاه", "crag":"سنگلاخ", "glacier_gate":"دروازۀ یخچال", "gate":"دروازه", "door":"دروازه", "vault":"گنجینه", "chest_of":"صندوق",
  "relay":"رله", "switch":"کلید", "circuit":"مدار", "node":"گره", "server":"کارگزار", "terminal":"پایانه", "console":"کنسول",
  "network":"شبکه", "uplink":"بالادست", "downlink":"پایین‌دست", "relay_link":"پیوندِ رله", "data":"داده", "record":"سابقه",
  "archive":"بایگانی", "file":"پرونده", "dossier":"پرونده", "log":"گزارش", "report":"گزارش", "brief":"گزارش", "intel":"اطلاعات",
  "recon":"شناسایی", "survey":"پیمایش", "mapping":"نقشه‌برداری", "survey_mussel":"پیمایش", "mussel":"صدف", "clam":"صدف", "oyster":"صدف",
  "scallop":"صدف", "urchin":"توپِ دریا", "anemone":"شقایق", "coral":"مرجان", "reef":"صخره", "kelp":"جلبک", "brine":"نمک", "salt":"نمک",
  "pearl":"مروارید", "pearl_harbor":"بندر مروارید", "bounty":"جایزه", "bounty_net":"تورِ جایزه", "trophy":"جایزه", "prize":"جایزه",
  "reward":"پاداش", "tribute":"خراج", "tax":"مالیات", "debt":"بدهی", "credit":"اعتبار", "coin":"سکه", "cash":"پول", "market":"بازار",
  "trade":" دادو‌ستد", "exchange":"صرافی", "barter":"تهاتر", "sell":"فروش", "buy":"خرید", "auction":"حراج", "bid":"مناقصه",
  "bid_sting":"نیشِ مناقصه", "ambush":"کمین", "surprise":"غافلگیری", "trap_wire":"سیمِ تله", "sniper":"تک‌تیرانداز", "snag":"ربودن",
  "pull":"کشیدن", "tow":"کشیدن", "drag":"کشیدن", "haul":"کشیدن", "drag_down":"کشیدن", "lift_up":"بالاکشیدن", "hover":"معلق",
  "float":"شناور", "fly":"پرواز", "flight":"پرواز", "soar":"اوج‌گیری", "glide":"سُر", "dive":"شیرجه", "aerial":"هوایی",
  "airstrike":"حمله‌ی هوایی", "air":"هوا", "wind":"باد", "gale":"بادِ تیز", "breeze":"نسیم", "cyclone":"گردباد", "tornado":"گردباد",
  "typhoon":"تایفون", "hurricane":"هری‌کین", "monsoon":"مونسون", "tempest":"توفان", "squall":"توفانک", "pressure_dive":"شیرجۀ فشار",
  "pump":"پمپ", "jackhammer":"چکش‌بُرنده", "jack":"جک", "drill":"دریل", "auger":"مته", "bit":"مته", "scoop":"بیل", "spoon":"قاشق",
  "shovel":"بیل", "bucket":"سطل", "pail":"سطل", "scoop_strike":"ضربه‌ی بیل", "fang_barrage":"بارانِ دندان", "fang_battle":"نبردِ دندان",
  "battle":"نبرد", "war":"جنگ", "conflict":"نزاع", "raid":"یورش", "assault":"حملۀ", "siege":"محاصره", "blockade":"حصار",
  "sortie":"برون‌ریزی", "patrol":"گشت", "sentinel_post":"پایگاهِ نگهبان", "post":"پایگاه", "camp":"اردو", "base":"پایگاه",
  "outpost":"پایگاه", "fort":"دژ", "keep":"دژ", "castle":"قلعه", "citadel":"ارگ", "stronghold":"دژِ محکم", "bunker":"سنگر",
  "trench_war":"جنگِ خندقی", "mine":"معدن", "minefield":"میدانِ مین", "field_mine":"مینِ زمینی", "mine_drop":"ریختنِ مین",
  "dropping":"ریختن", "hollow":"توخالی", "hollow_earth":"زمینِ توخالی", "inner":"درونی", "outer":"بیرونی", "core_hollow":"هستۀ توخالی",
  "empty":"تهی", "vacuum":"خلاء", "suction":"مکش", "vacuum_seal":"مُهرِ خلاء", "seal":"مُهر", "stamp":"مُهر", "brand":"نشان",
  "mark":"نشانه", "mark_target":"نشانه‌گذاری", "target":"هدف", "marking":"نشانه‌گذاری", "locate":"مکان‌یابی", "locate_lock":"قفلِ مکان",
  "tag":"برچسب", "tracked":"ردیابی‌شده", "track":"ردیابی", "trace":"اثر", "trail":"رد", "spoor":"رد", "scent":"بوی", "sniff":"بو‌کشیدن",
  "taste":"چشیدن", "lick":"لیسیدن", "lick_acid":"لیسیدنِ اسید", "acid_lick":"آبشِ اسید", "tongue":"زبان", "mouth":"دهان", "throat":"گلو",
  "throat_crush":"کوبشِ گلو", "crush_throat":"کوبشِ گلو", "neck":"گردن", "constrict":"خفه", "grip":"گیر", "grapple":"کلنگی",
  "hold":"نگهداشتن", "clutch":"چنگ", "seize":"گرفتن", "snatch":"ربودن", "grab":"گرفتن", "hug":"بغل", "squeeze":"فشردن", "wring":"چلاندن",
  "crack":"شکستن", "fracture":"شکست", "rupture":"دریدگی", "rupture_core":"دریدگیِ هسته", "split":"دو‌پاره", "sever_spine":"بریدنِ ستون",
  "back":"پشت", "rib":"دنده", "rib_crusher":"دنده‌کوب", "skull_crusher":"جمجمه‌کوب", "brain":"مغز", "skull_crack":"شکستنِ جمجمه",
  "shock_paddle":"بالۀ ضربه", "paddle":"باله", "spike_fin":"بالۀ خاردار", "fin_flash":"فلاشِ باله", "flash":"جرقه", "blind":"رنگی‌کردن",
  "blind_flash":"جرقۀ کورکننده", "dazzle":"خیره‌سازی", "blind_storm":"طوفانِ کوری", "dust_devil":"غولِ گرد", "dust_storm":"طوفانِ گرد",
  "sandblast":"شن‌پاشی", "bluster":"هو‌هوا", "gust":"نسیم", "scream_stun":"زوزۀ مفلج", "stun":"فلج", "paralytic":"فلج‌کننده",
  "paralysis":"فلجی", "numb":"بی‌حس", "freeze_over":"یخ‌زدگی", "entomb":"گورکردن", "tomb":"گور", "grave":"قبر", "crypt":"دخمه",
  "ossuary":"استودان", "bone":"استخوان", "skeleton":"اسکلت", "corpse":"جسد", "cadaver":"جسد", "decay":"پوسیدگی", "rot":"پوسیدگی",
  "plague":"طاعون", "sickness":"بیماری", "injury":"آسیب", "wound":"زخم", "bleed":"خونریزی", "scar":" جای", "cut":"برش", "gash":"برشِ عمیق",
  "laceration":"پارگی", "trauma":"آسیب", "bruise":"کبود", "swell":"ورم", "inflammation":"التهاب", "infect":"آلوده", "contagion":"سرایت",
  "septic":"گندیده", "venom_bite":"گازِ زهرآگین", "toxic_spit":"تفِ سمی", "orga":"اورگا", "bara":"باراگون"
}

TOK.update({
 "gravity":"گرانش","hatch":"فراخوان","web":"تار","silk":"ابریشم","dump":"ریختن","egg":"تخم",
 "fortress":"دژ","emp":"پالسِ الکترومغناطیسی","mhz":"مگاهرتز","presence":"حضور","combat":"رزم",
 "intelligence":"اطلاعات","guardian":"حافظ","vow":"سوگند","three":"سه","heads":"سر","flight":"پرواز",
 "master":"استادی","mastery":"استادی","will":"خواست","aerial":"هوایی","aegis":"سپرِ اجیس",
 "declassified":"از‌طبقه‌خارج‌شده","restricted":"محدود","confidential":"محرمانه","secret":"سری",
 "eyes":"چشمان","only":"فقط","level":"سطح","omega_level":"سطحِ امگا","alpha_prey":"شکارِ آلفا",
})
TOK.update({
 "oxygen":"اکسیژن",
 "shield":"سپر",
 "rush":"یورش",
 "planet":"سیاره",
 "rake":"چنگک",
 "energy":"انرژی",
 "whip":"شلاق",
 "lash":"شلاق‌زدن",
 "silence":"خاموشی",
 "ink":"مرکب",
 "proton":"پروتون",
 "diameter":"قطر",
 "cage":"قفس",
 "reflective":"بازتابنده",
 "max":"بیشینه",
 "instinct":"غریزه",
 "floral":"گیاهی",
 "mineral":"کانی",
 "toxic":"سمّی",
 "whirlpool":"گرداب",
 "beast":"موجوده",
 "monollith":"مونولیت",
 "glacial":"یخی",
 "defense":"دفاع",
 "bounding":"جهنده",
 "snap":"آنی",
 "domination":"سلطه",
 "screen":"پرده",
 "age":"عصر",
 "mire":"باتلاق",
 "screech":"جیغ",
 "double":"دوگانه",
 "overload":"بیش‌بار",
 "tactical":"رزمی",
 "shot":"شلیک",
 "telepathic":"ذهن‌خوان",
 "radiance":"درخشش",
 "firestorm":"طوفانِ آتش",
 "shoot":"شلیک",
 "organ":"اندام",
 "spiny":"خاردار",
 "roll":"غلتیدن",
 "protector":"حامی",
 "seed":"بذر",
 "consumption":"مصرف",
 "spinner":"چرخه‌باف",
 "cybernetic":"سایبر",
 "cybernetics":"سایبرنتیک",
 "slime":"لجن",
 "dissolution":"حل‌شدن",
 "hands":"دستان",
 "pyre":"چوبه‌ی آتش",
 "spirit":"روح",
 "wail":"ناله",
 "prismatic":"منشوری",
 "cleanser":"پاک‌کننده",
 "grow":"رشد",
 "arms":"بازوها",
 "earthen":"خاکی",
 "kangaroo":"کانگورو",
 "matter":"ماده",
 "rises":"برخاستن",
 "clamp":"گیره",
 "spikes":"خارها",
 "tentacle":"بازو",
 "stampede":"یورشِ دسته",
 "molt":"تولک",
 "molting":"تولک‌اندازی",
 "nanite":"نانیت",
 "repair":"تعمیر",
 "laser":"لیزر",
 "big":"بزرگ",
 "ears":"گوش‌ها",
 "bog":"مرداب",
 "boomerang":"بومرنگ",
 "trip":"لنگ‌کردن",
 "den":"لانه",
 "bomb":"بمب",
 "elastic":"کشسان",
 "stab":"خنجرکاری",
 "bait":"طعمه",
 "lockon":"قفلِ هدف",
 "lock_on":"قفلِ هدف",
 "turret":"برجک",
 "maelidon":"مِلدُون",
 "bug":"حشره",
 "lure":"فریب",
 "photosynth":"فتوسنتز",
 "prey":"شکار",
 "solar":"خورشیدی",
 "flail":"گرُز",
 "mace":"گُرز",
 "talon":"پنجه",
 "head":"سر",
 "decoy":"فریب",
 "shear":"قیچی",
 "copy":"کپی",
 "army":"لشکر",
 "continent":"قاره",
 "strangle":"خفگی",
 "constriction":"خفگی",
 "finisher":"تمام‌کننده",
 "exoskeletal":"برون‌اسکلت",
 "feathered":"پَردار",
 "green":"سبز",
 "marsh":"تالاب",
 "discharge":"تخلیه",
 "thrust":"رانش",
 "wraps":"پیچش",
 "all":"همه",
 "oceanic":"اقیانوسی",
 "rending":"دریدنی",
 "one":"یک",
 "thousand":"هزار",
 "rings":"حلقه‌ها",
 "ring":"حلقه",
 "cracker":"شکننده",
 "shisa":"شیسَه",
 "skyhunter":"آسمان‌شکار",
 "triple":"سه‌گانه",
 "triad":"سه‌سواره",
 "flurry":"بارش",
 "machine":"ماشین",
 "adaptive":"سازگار",
 "evolution":"تکامل",
 "link":"پیوند",
 "body":"پیکر",
 "burrower":"کَنده",
 "justice":"عدالت",
 "absorption":"جذب",
 "undying":"نامیرا",
 "devouring":"بلعنده",
 "lord":"ارباب",
 "playful":"شوخ",
 "wings":"بال‌ها",
 "mother":"مادر",
 "living":"زنده",
 "grove":"بوستان",
 "memory":"حافظه",
 "armor":"زره",
 "resonant":"تشدیدی",
 "shrine":"معبد",
 "structure":"ساختار",
 "vein":"رگ",
 "exposure":"برهنه‌سازی",
 "pyro":"آتشین",
 "spittle":"بزاق",
 "splitter":"دو‌پاره‌کن",
 "blindness":"نابینایی",
 "coolant":"خنک‌کننده",
 "breach":"نفوذ",
 "locked":"قفل‌شده",
 "feast":"ضیافت",
 "rain":"باران",
 "well":"چاه",
 "chaos":"آشوب",
 "second":"دوم",
 "impalement":"میزه‌کردن",
 "agonized":"دردناک",
 "destroyer":"ویرانگر",
 "cellular":"سلولی",
 "overcharge":"بیش‌شارژ",
 "arc":"قوس",
 "online":"برخط",
 "self":"خود",
 "diagnostic":"عیب‌یابی",
 "purge":"تصفیه",
 "break":"شکست",
 "skar":"اسکار",
 "descends":"فرود",
 "convergence":"همگرایی",
 "cascade":"ریزش",
 "mirror":"آینه",
 "refraction":"شکست",
 "advance":"پیشروی",
 "rime":"یخ‌نو",
 "hijack":"ربایش",
 "total":"همگانی",
 "sync":"همگامی",
 "drone":"پهپاد",
 "will":"خواست",
 "three":"سه",
 "core":"هسته",
 "presence":"حضور",
 "guard":"نگهبانی",
 "vow":"سوگند",
})
TOK.update({
 # عنصرها/نقطه‌ضعف‌ها (titans.weak / titans.resist)
 "acid":"اسید","ash":"خاکستر","atomic":"هسته‌ای","brute":"زورِ صرف","cold":"سرمای","dark":"تاریکی",
 "electric":"برق","electricity":"برق","falling":"سقوط","fire":"آتش","gravity":"گرانش","ice":"یخ",
 "light":"نور","oxygen":"اکسیژن","poison":"سم","pressure":"فشار","psychic":"ذهن","radiation":"پرتو",
 "sonic":"صوت","sonics":"صوت","tech":"فناوری","venom":"زهر","cryo":"یخ","water":"آب",
 "energy":"انرژی","pollution":"آلودگی","seismic":"لرزه","space":"فضا","nuke":"هسته‌ای",
 "feral":"وحشی","imago":"بالغ","scale":"اِسکیل","shot":"شلیک","cluster":"خوشه","paddle":"باله",
 "stampede":"یورشِ دسته","screech":"جیغ","domination":"سلطه","annihilation":"نیستی","radiance":"درخشش",
 "spittle":"بزاق","discharge":"تخلیه","overload":"بیش‌بار","sentinel":"نگهبان","guardian":"حامی",
 "constriction":"خفگی","tentacle":"بازو","carapace":"سپروار","mandible":"فکک","staccato":"کوتاه",
 "percussion":"کوبش","sonata":"سونات","rondo":"گردان","fugue":"هم‌خوان","prelude":"پیش‌درآمد",
})
TOK = {k: v for k, v in TOK.items()
       if isinstance(v, str) and re.fullmatch(r"[\u0600-\u06FF\u200c ]*", v)}
STOP = {"of", "the", "a", "an", "and", "for", "to", "in", "on", "at", "with"}
GRADE = {"max", "ultra", "prime", "alpha", "omega", "mk2", "mkii", "type0", "type", "final",
         "true", "zero", "neo", "super", "giga", "tera", "v2", "ii", "iii", "iv"}

TR = [("th", "ت"), ("sh", "ش"), ("ch", "چ"), ("ph", "ف"), ("gh", "غ"), ("kh", "خ"), ("qu", "کو"),
      ("ck", "ک"), ("ss", "س"), ("ee", "ی"), ("ea", "ی"), ("oo", "وو"), ("ou", "او"), ("ai", "ای"),
      ("au", "آ"), ("ei", "ای"), ("ie", "ی"), ("x", "کس"), ("z", "ز"), ("j", "ج"), ("w", "و"),
      ("a", "ا"), ("b", "ب"), ("c", "ک"), ("d", "د"), ("e", "ِ"), ("f", "ف"), ("g", "گ"), ("h", "ه"),
      ("i", "ی"), ("k", "ک"), ("l", "ل"), ("m", "م"), ("n", "ن"), ("o", "اُ"), ("p", "پ"), ("r", "ر"),
      ("s", "س"), ("t", "ت"), ("u", "و"), ("v", "و"), ("y", "ی"), ("q", "ق")]


def translit(word: str) -> str:
    w = re.sub(r"[^a-z]", "", (word or "").lower())
    out, i = [], 0
    while i < len(w):
        for a, b in TR:
            if w.startswith(a, i):
                out.append(b); i += len(a); break
        else:
            i += 1
    s = "".join(out)
    if word and word[0].lower() in "aeiou" and s.startswith("ِ"):
        s = "اَ" + s[1:]
    s = re.sub(r"^[\u200cِ]+", "", s)
    return re.sub(r"\s+", "", s) or (word or "")


def _split(name: str):
    out = []
    for piece in re.split(r"[ \-_·'\u200c]+", (name or "").strip()):
        if not piece:
            continue
        if re.fullmatch(r"[A-Za-z.]{2,}\.", piece):          # «M.U.T.O.» → «MUTO»
            out.append(re.sub(r"[.]", "", piece))
        else:
            out.append(piece)
    return out


def name_for(latin: str, tag: str = "") -> str:
    """«Atomic Breath» → «تنفسِ اتمی» — و برای واژۀ ناشناخته آوانگاری.

    قاعده‌ی فارسی: سرِ ترکیب (اسمِ main) اول می‌آید و پس از آن با کسره «ِ»
    وابسته‌ها. در ساختار «X of the Y» هم زنجیرۀ اضافه ادامه پیدا می‌کند:
    «War Axe of the Hollow» → «تبرِ جنگِ توخالی».
    """
    toks = _split(latin)
    if not toks:
        return latin or "ضربه"
    if any(re.search(r"[\u0600-\u06FF]", x) for x in toks):
        return latin                              # از قبل فارسی است

    def word(x: str):
        xl = x.lower()
        if xl in TOK:
            return TOK[xl]
        if xl in STOP or not x:
            return ""
        core = re.sub(r"[^a-z]", "", xl)
        if core and core.isalpha():
            return translit(core)
        return x if x.isdigit() else ""

    # زنجیرۀ اضافه: بخش‌های جداشده با «of / 's»
    parts, cur = [], []
    for x in toks:
        if x.lower() in ("of", "the_of") or x.endswith("'s"):
            parts.append(cur); cur = []
        else:
            cur.append(x)
    parts.append(cur)
    parts = [q for q in parts if q]

    chunks = []
    for q in parts:
        tr = [w for w in (word(x) for x in q) if w]
        if not tr:
            continue
        tr = [re.sub(r"^[\u200cِ]+", "", x) for x in tr]
        head, mods = tr[-1], tr[:-1]
        if len(q) > 1 and q[-1].lower().strip(".-") in GRADE:
            head, mods = (mods[-1] if mods else head), (mods[:-1] + [tr[-1]] if mods else mods)
        head = head.rstrip("ِ").rstrip("\u200c")
        chunks.append((head, [m.rstrip("ِ").rstrip("\u200c") for m in mods]))
    if not chunks:
        return TOK.get(tag) or "ضربه"

    head, mods = chunks[0]
    if mods and head.endswith("ها"):
        head = head[:-2] + "های"        # «بال‌های طوفان» نه «بال‌هاِ طوفان»
        out = head + " " + " ".join(mods)
    else:
        out = head
        if mods:
            out += "ِ " + " ".join(mods)
    for h2, m2 in chunks[1:]:
        if h2.endswith("ها"):
            h2 = h2[:-2] + "های"
        out += "ِ " + h2
        if m2:
            out += "ِ " + " ".join(m2)
    out = re.sub(r"\s+ِ\s*", "ِ ", out)   # کسره به سرِ واژۀ بعد می‌چسبد
    out = out.replace("هاِ ", "های ").replace("‌ها", "‌ها")
    out = re.sub(r"[\u200cِ]+$", "", out)
    out = re.sub(r"^[\u200cِ]+", "", out)
    return out.strip()


RUN = re.compile(r"[A-Za-z][A-Za-z0-9.'\-]{1,}")


FA_DIGITS = str.maketrans("0123456789.", "۰۱۲۳۴۵۶۷۸۹٫")


def fa_num(x) -> str:
    """رقمِ فارسی برای متنِ روایی (داشته‌های عددی/کدها لاتین می‌مانند)."""
    return str(x).translate(FA_DIGITS)


def clean_str(s: str) -> str:
    """واژه‌های لاتینِ شناخته‌شده را در دلِ یک sentence فارسی هم ترجمه می‌کند.

    «Hatch — نوزادها بیرون می‌آیند» → «فراخوان — نوزادها بیرون می‌آیند»
    """
    if not s or not re.search(r"[A-Za-z]{3}", s):
        return s

    def rep(m):
        w = m.group(0)
        k = re.sub(r"[^a-z]", "", w.lower())
        if k in TOK and TOK[k] and not k.endswith((".", "-")):
            return TOK[k]
        return w
    return RUN.sub(rep, s)


def fix(d, keys=("name", "label", "title", "desc", "cls"), deep: int = 3) -> int:
    """فارسی‌کردنِ نام‌های لاتینِ موجود در دیکشنری/لیست (نام اصلی در `en`)."""
    n = 0

    def walk(obj, depth=0):
        nonlocal n
        if isinstance(obj, dict):
            tag = str(obj.get("tag") or obj.get("key") or "")
            for k in keys:
                v = obj.get(k)
                if not (isinstance(v, str) and v) or not re.search(r"[A-Za-z]{3,}", v):
                    continue
                if re.search(r"[\u0600-\u06FF]", v):
                    w = clean_str(v)
                    if w != v:
                        obj.setdefault("en", v)
                        obj[k] = w
                        n += 1
                elif k == "cls":
                    obj[k] = clean_str(v)
                    n += 1
                else:
                    obj.setdefault("en", v)
                    obj[k] = name_for(v, tag)
                    n += 1
            if depth < deep:
                for v in obj.values():
                    walk(v, depth + 1)
        elif isinstance(obj, list) and depth < deep:
            for v in obj:
                walk(v, depth + 1)

    walk(d)
    return n
