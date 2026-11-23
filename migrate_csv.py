"""ترحيل ملفات CSV القديمة إلى Supabase (مرة واحدة).

التشغيل:
    SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python migrate_csv.py
يتجاوز الملفات غير الموجودة. شغّله مرة واحدة فقط وإلا تتكرر الطلبيات.
"""
import os
import sys

import pandas as pd
import requests

URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
KEY = os.environ.get("SUPABASE_SERVICE_KEY")
if not URL or not KEY:
    sys.exit("اضبط SUPABASE_URL و SUPABASE_SERVICE_KEY أولاً.")

HEADERS = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
STATUS = {"قيد التوصيل 🚚": "pending", "تم التوصيل بنجاح ✅": "delivered",
          "راجع / ملغى (Retour) ❌": "returned"}


def post(table, rows):
    if not rows:
        return
    r = requests.post(f"{URL}/rest/v1/{table}", headers=HEADERS, json=rows, timeout=30)
    if not r.ok:
        sys.exit(f"فشل {table}: {r.status_code} {r.text[:300]}")


if os.path.exists("inventory_data.csv"):
    inv = pd.read_csv("inventory_data.csv", encoding="utf-8-sig")
    rows = [{"name": str(r["اسم المنتج"]).strip(),
             "quantity": int(r["الكمية المتوفرة"]),
             "buy_price": int(r["سعر الشراء بالجملة (DA)"]),
             "sell_price": int(r["سعر البيع المقترح (DA)"])} for _, r in inv.iterrows()]
    post("dz_products", rows)
    print(f"منتجات: {len(rows)}")

if os.path.exists("sales_data.csv"):
    s = pd.read_csv("sales_data.csv", encoding="utf-8-sig", dtype=str)
    rows = []
    for _, r in s.iterrows():
        def num(col):
            return int(float(r[col])) if col in s.columns and pd.notna(r.get(col)) else 0
        rows.append({
            "created_at": pd.to_datetime(r["التاريخ"]).tz_localize("Africa/Algiers").isoformat(),
            "customer": r["الزبون"],
            "phone": r["الهاتف"] if "الهاتف" in s.columns and pd.notna(r.get("الهاتف")) else "",
            "wilaya": r["الولاية"], "product": r["المنتج"],
            "amount": num("المبلغ"), "shipping": num("الشحن"), "buy_cost": num("تكلفة الشراء"),
            "status": STATUS.get(r["حالة التوصيل"], "pending"),
        })
    post("dz_orders", rows)
    print(f"طلبيات: {len(rows)}")
