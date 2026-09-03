"""کمک‌مشترک ابزارها: اضافه کردن monarch/ به sys.path و خواندن .env در صورت وجود."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "monarch"))
envp = os.path.join(ROOT, ".env")
if os.path.exists(envp):
    for line in open(envp, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
os.environ.setdefault("MC_DB_PATH", os.path.join(ROOT, "monarch.db"))
