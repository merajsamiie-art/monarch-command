# 🗄 دیتابیس — SQLite + WAL + کش + مهاجرت؛ همه‌ی حالت‌ها پایدار (resume-after-restart)
import json
import os
import sqlite3
import threading
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS players(
  user_id INTEGER PRIMARY KEY, name TEXT, username TEXT,
  created_at REAL, last_seen REAL, last_tick REAL,
  rank INTEGER DEFAULT 1, xp REAL DEFAULT 0,
  hp REAL, max_hp REAL, energy REAL, max_energy REAL, resolve REAL, max_resolve REAL,
  credits REAL DEFAULT 0, cores REAL DEFAULT 0, dna REAL DEFAULT 0,
  cells REAL DEFAULT 0, mats REAL DEFAULT 0, fdata REAL DEFAULT 0, vault REAL DEFAULT 0,
  kills INTEGER DEFAULT 0, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0,
  boss_kills INTEGER DEFAULT 0, raids INTEGER DEFAULT 0, deaths INTEGER DEFAULT 0,
  flees INTEGER DEFAULT 0, samples INTEGER DEFAULT 0, puzzles INTEGER DEFAULT 0,
  expeditions INTEGER DEFAULT 0, research_done INTEGER DEFAULT 0, guards INTEGER DEFAULT 0,
  arena_rating REAL DEFAULT 1000, arena_wins INTEGER DEFAULT 0, arena_losses INTEGER DEFAULT 0,
  pvp_wins INTEGER DEFAULT 0, pvp_losses INTEGER DEFAULT 0,
  arena_fights INTEGER DEFAULT 0, season TEXT DEFAULT '',
  expedition_zone TEXT, expedition_until REAL DEFAULT 0, expedition_tier INTEGER DEFAULT 0,
  lab_titan TEXT, lab_stage TEXT, lab_until REAL DEFAULT 0, lab_points REAL DEFAULT 0,
  dead_until REAL DEFAULT 0,
  day TEXT DEFAULT '', last_seen_day TEXT DEFAULT '', checkin INTEGER DEFAULT 0, streak INTEGER DEFAULT 0,
  missions TEXT DEFAULT '{}', flags TEXT DEFAULT '{}', invuln_until REAL DEFAULT 0,
  power_cache REAL DEFAULT 0, last_target TEXT, echo_uses INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS items(
  user_id INTEGER, item_id TEXT, qty INTEGER DEFAULT 0, equipped INTEGER DEFAULT 0,
  level INTEGER DEFAULT 0,
  PRIMARY KEY(user_id, item_id));
CREATE TABLE IF NOT EXISTS bonds(
  user_id INTEGER, titan_id TEXT,
  stage INTEGER DEFAULT 0, points REAL DEFAULT 0, kills INTEGER DEFAULT 0,
  bond INTEGER DEFAULT 0, bond_points REAL DEFAULT 0, last REAL DEFAULT 0,
  PRIMARY KEY(user_id, titan_id));
CREATE TABLE IF NOT EXISTS chats(
  chat_id INTEGER PRIMARY KEY, kind TEXT DEFAULT 'group', zone TEXT DEFAULT 'ocean',
  title TEXT, danger INTEGER DEFAULT 1, created_at REAL,
  last_news REAL DEFAULT 0, last_alert REAL DEFAULT 0,
  boss_id TEXT, boss_state TEXT, boss_until REAL DEFAULT 0,
  feed_msg INTEGER DEFAULT 0, seen_users TEXT DEFAULT '{}');
CREATE TABLE IF NOT EXISTS combats(
  id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, kind TEXT, status TEXT,
  a_id INTEGER, b_id INTEGER, state TEXT, msg_id INTEGER DEFAULT 0,
  created_at REAL, updated_at REAL);
CREATE INDEX IF NOT EXISTS idx_combat_chat ON combats(chat_id, status);
CREATE TABLE IF NOT EXISTS raids(
  id INTEGER PRIMARY KEY AUTOINCREMENT, boss_id TEXT, status TEXT,
  state TEXT, created_at REAL, updated_at REAL, ends_at REAL);
CREATE TABLE IF NOT EXISTS raid_users(
  raid_id INTEGER, user_id INTEGER, dmg REAL DEFAULT 0, guard REAL DEFAULT 0,
  support REAL DEFAULT 0, analyze REAL DEFAULT 0, strikes INTEGER DEFAULT 0,
  last_hit INTEGER DEFAULT 0, joined REAL, PRIMARY KEY(raid_id, user_id));
CREATE TABLE IF NOT EXISTS divisions(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, tag TEXT UNIQUE,
  owner_id INTEGER, level INTEGER DEFAULT 1, xp REAL DEFAULT 0,
  credits REAL DEFAULT 0, cores REAL DEFAULT 0, mats REAL DEFAULT 0,
  cells REAL DEFAULT 0, dna REAL DEFAULT 0, fdata REAL DEFAULT 0,
  facilities TEXT DEFAULT '{}', created_at REAL,
  war TEXT DEFAULT '{}', wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0,
  points REAL DEFAULT 0, morale REAL DEFAULT 50);
CREATE TABLE IF NOT EXISTS div_users(
  user_id INTEGER PRIMARY KEY, div_id INTEGER, role TEXT DEFAULT 'agent', joined REAL,
  contrib REAL DEFAULT 0, tracked INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS cooldowns(user_id INTEGER, kind TEXT, until REAL,
  PRIMARY KEY(user_id, kind));
CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS chat_users(chat_id INTEGER, user_id INTEGER, last_active REAL,
  PRIMARY KEY(chat_id, user_id));
CREATE TABLE IF NOT EXISTS log(ts REAL, kind TEXT, payload TEXT);
CREATE INDEX IF NOT EXISTS idx_log_ts ON log(ts DESC);
"""

_RES = ("credits", "cores", "dna", "cells", "mats", "fdata", "vault", "xp", "hp",
        "energy", "resolve", "lab_points")


class Store:
    """اتصال مشترک (thread-safe) + کش سطری + نوشتن دسته‌ای."""

    def __init__(self, path: str):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.path = path
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=-16000")
        with self.lock:
            self.conn.executescript(SCHEMA)
            self._migrate()
            self.conn.commit()

    def _migrate(self):
        """➕ افزودن ستون جدید بدون از دست رفتن دیتای بازیکنان."""
        want = {"players": {"power_cache": "REAL DEFAULT 0", "last_target": "TEXT",
                            "echo_uses": "INTEGER DEFAULT 0", "last_seen_day": "TEXT DEFAULT ''",
                            "pvp_wins": "INTEGER DEFAULT 0", "pvp_losses": "INTEGER DEFAULT 0"},
                "items": {"level": "INTEGER DEFAULT 0"},
                "bonds": {"echo_level": "INTEGER DEFAULT 0"},
                "divisions": {"cells": "REAL DEFAULT 0", "dna": "REAL DEFAULT 0",
                              "fdata": "REAL DEFAULT 0"}}
        for table, cols in want.items():
            have = {r["name"] for r in self.conn.execute(f"PRAGMA table_info({table})").fetchall()}
            for col, decl in cols.items():
                if col not in have:
                    self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        self._pcache = {}
        self._kv = {}
        self._kv_ts = 0.0

    # ── primitives ──
    def q(self, sql, p=()):
        with self.lock:
            return [dict(r) for r in self.conn.execute(sql, p).fetchall()]

    def one(self, sql, p=()):
        with self.lock:
            r = self.conn.execute(sql, p).fetchone()
            return dict(r) if r else None

    def ex(self, sql, p=()):
        with self.lock:
            cur = self.conn.execute(sql, p)
            self.conn.commit()
            return cur

    def executemany(self, sql, seq):
        with self.lock:
            self.conn.executemany(sql, seq)
            self.conn.commit()

    # ── player row (کش‌شده) ──
    def player(self, uid: int):
        row = self._pcache.get(uid)
        if row is not None:
            return dict(row)
        r = self.one("SELECT * FROM players WHERE user_id=?", (uid,))
        if r:
            self._pcache[uid] = r
        return r

    def cache_put(self, row: dict):
        self._pcache[row["user_id"]] = dict(row)

    def cache_flush(self, uid: int):
        self._pcache.pop(uid, None)

    def apply(self, uid: int, **fields):
        """به‌روزرسانی ستون‌های عددی/متنی player + بی‌اعتبار کردن کش."""
        if not fields:
            return
        cols = ",".join(f"{k}=?" for k in fields)
        self.ex(f"UPDATE players SET {cols} WHERE user_id=?", tuple(fields.values()) + (uid,))
        cached = self._pcache.get(uid)
        if cached:
            cached.update(fields)
        else:
            self._pcache[uid] = dict(fields, user_id=uid)

    def add(self, uid: int, **deltas):
        p = self.player(uid)
        if not p:
            return
        fields = {}
        for k, v in deltas.items():
            cur = float(p.get(k) or 0.0)
            fields[k] = round(cur + float(v), 3)
        self.apply(uid, **fields)

    # ── kv ──
    def getv(self, key: str, default=None):
        now = time.time()
        if now - self._kv_ts > 5:
            self._kv = {}
            self._kv_ts = now
        if key in self._kv:
            return self._kv[key]
        r = self.one("SELECT v FROM kv WHERE k=?", (key,))
        val = None
        if r:
            try:
                val = json.loads(r["v"])
            except Exception:
                val = r["v"]
        self._kv[key] = val
        return val if val is not None else default

    def setv(self, key: str, value):
        self.ex("INSERT INTO kv(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                (key, json.dumps(value, ensure_ascii=False)))
        self._kv[key] = value
        self._kv_ts = time.time()

    def bump(self, key: str, amount: float = 1):
        cur = self.getv(key, 0)
        self.setv(key, (float(cur) if isinstance(cur, (int, float)) else 0) + amount)
        return self.getv(key)

    # ── misc ──
    def feed(self, kind: str, payload: str):
        try:
            self.ex("INSERT INTO log(ts,kind,payload) VALUES(?,?,?)", (time.time(), kind, payload[:400]))
        except Exception:
            pass

    def checkpoint(self):
        with self.lock:
            try:
                self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                self.conn.commit()
            except Exception:
                pass

    def close(self):
        self.checkpoint()
        with self.lock:
            self.conn.close()


_s = None


def init(path: str = None) -> Store:
    global _s
    from config import DB_PATH
    _s = Store(path or DB_PATH)
    return _s


def db() -> Store:
    assert _s is not None, "db.init() صدا زده نشده"
    return _s


def now() -> float:
    return time.time()


def jload(text, default=None):
    try:
        return json.loads(text) if text else default
    except Exception:
        return default


def jdump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def local_hour(tz_key: str = "Asia/Tehran") -> int:
    """ساعت محلی بدون وابستگی به کتابخانه — از offset ثابت تهران (+3:30)."""
    import datetime as dt
    off = dt.timedelta(hours=3, minutes=30) if tz_key == "Asia/Tehran" else dt.timedelta()
    return (dt.datetime.utcnow() + off).hour


def local_day(tz_key: str = "Asia/Tehran") -> str:
    import datetime as dt
    off = dt.timedelta(hours=3, minutes=30) if tz_key == "Asia/Tehran" else dt.timedelta()
    return (dt.datetime.utcnow() + off).strftime("%Y-%m-%d")


def local_now(tz_key: str = "Asia/Tehran"):
    import datetime as dt
    off = dt.timedelta(hours=3, minutes=30) if tz_key == "Asia/Tehran" else dt.timedelta()
    return dt.datetime.utcnow() + off


def weekday_local() -> int:
    """۰ = شنبه (سبک تقویم بازی)."""
    d = local_now().weekday()          # py: 0=Monday
    return (d + 1) % 7                 # shanbe=0
