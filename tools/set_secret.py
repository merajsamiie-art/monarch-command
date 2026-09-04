#!/usr/bin/env python3
"""🔐 گذاشتنِ یک راز در مخزنِ گیت‌هاب (برای دیپلوی روی Actions).

    python3 tools/set_secret.py BOT_TOKEN "123456:AAAA…"
    python3 tools/set_secret.py --repo merajsamiie-art/monarch-command ADMIN_IDS 8694290031

رمزِ دسترسی از ``GITHUB_TOKEN`` یا ``GH_PAT`` خوانده می‌شود (هرگز در مخزن
ذخیره نشو). نیازمند کتابخانۀ ``pynacl`` (در requirements.txt هست).
"""
import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request

DEFAULT_REPO = os.getenv("MC_REPO", "merajsamiie-art/monarch-command")


def api(path, token, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request("https://api.github.com" + path, method=method, data=data,
                                 headers={"Authorization": f"token {token}", "User-Agent": "monarch",
                                          "Accept": "application/vnd.github+json",
                                          **({"Content-Type": "application/json"} if data else {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw.strip() else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", help="نامِ راز، مثل BOT_TOKEN")
    ap.add_argument("value", nargs="?", default="", help="مقدار (اگر خالی بود از env خوانده می‌شود)")
    ap.add_argument("--repo", default=DEFAULT_REPO)
    a = ap.parse_args()
    tok = os.getenv("GITHUB_TOKEN") or os.getenv("GH_PAT")
    if not tok:
        sys.exit("❌ GITHUB_TOKEN / GH_PAT تنظیم نشده.")
    val = a.value or os.getenv(a.name, "")
    if not val:
        sys.exit(f"❌ مقداری برای «{a.name}» داده نشد.")
    key = api(f"/repos/{a.repo}/actions/secrets/public-key", tok)
    from nacl.bindings import crypto_box_SEALBYTES, crypto_box_seal
    from nacl.encoding import RawEncoder
    from nacl.public import PublicKey
    pub = PublicKey(base64.b64decode(key["key"]), encoder=RawEncoder)
    sealed = base64.b64encode(crypto_box_seal(val.encode(), pub)).decode()
    api(f"/repos/{a.repo}/actions/secrets/{a.name}", tok, "PUT",
        {"encrypted_value": sealed, "key_id": key["key_id"]})
    names = [s["name"] for s in api(f"/repos/{a.repo}/actions/secrets", tok).get("secrets", [])]
    print(f"✓ «{a.name}» نوشته شد · رازهای مخزن: {', '.join(sorted(names))}")
    for k in ("value",):                                  # پاک‌سازیِ جای‌پا در حافظۀ env
        os.environ.pop(a.name, None)


if __name__ == "__main__":
    main()
