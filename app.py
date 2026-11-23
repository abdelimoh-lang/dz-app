import os
import re
import hmac
from datetime import datetime
from html import escape
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st

# ==================== 1. إعدادات الصفحة والتصميم ====================
st.set_page_config(
    page_title="منصة التاجر الجزائري الذكية | DZ Ecommerce BI",
    page_icon="🇩🇿",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');

    .stMarkdown, .stMarkdown p, label, .stTextInput input, .stTextArea textarea,
    .stNumberInput input, .stSelectbox, .stMultiSelect, .stRadio, .stAlert,
    .stExpander, .stTabs, h1, h2, h3, h4 {
        font-family: 'Tajawal', sans-serif !important;
        direction: rtl; text-align: right;
    }
    .stApp { background: #f1f2f4; }
    .block-container { padding-top: 2.2rem; max-width: 1280px; }
    section[data-testid="stSidebar"] { background: #ffffff !important; border-left: 1px solid #e7e9ee; }

    .page-title { font-size: 44px; font-weight: 800; color: #0f172a; margin: 0 0 4px 0; line-height: 1.15; }
    .page-sub { font-size: 15px; color: #8a94a6; margin-bottom: 22px; }

    .dz-card, .insight { box-sizing: border-box; }
    .dz-card {
        background: #fff; border-radius: 26px; padding: 22px 24px; height: 100%;
        border: 1px solid #eceef2;
        box-shadow: 0 1px 0 rgba(255,255,255,.9) inset, 0 14px 32px -16px rgba(15,23,42,.18);
    }
    .dz-title { font-size: 20px; font-weight: 700; color: #0f172a; margin-bottom: 14px;
                display: flex; justify-content: space-between; align-items: center; }
    .dz-sub { color: #8a94a6; font-size: 13px; font-weight: 500; }
    .dz-big { font-size: 46px; font-weight: 800; line-height: 1.1; color: #0f172a; }
    .dz-delta { display: inline-block; font-size: 13px; font-weight: 700; padding: 3px 10px;
                border-radius: 99px; background: #dcfce7; color: #15803d; margin-right: 8px; }
    .dz-delta.neg { background: #fee2e2; color: #b91c1c; }
    .dz-gap { height: 16px; }

    .fun-row { display: flex; gap: 10px; align-items: flex-end; direction: rtl; }
    .fun-col { flex: 1; text-align: right; }
    .fun-label { font-size: 12px; color: #9aa3b2; font-weight: 500; }
    .fun-val { font-size: 26px; font-weight: 800; color: #b9c0cd; }
    .fun-col.hi .fun-val { color: #0f172a; }
    .fun-track { height: 160px; display: flex; align-items: flex-end; margin-top: 8px; }
    .fun-bar { width: 100%; border-radius: 12px 12px 0 0;
               background: repeating-linear-gradient(135deg, #2f5bea 0 5px, #dbe6ff 5px 8px); }
    .fun-bar.solid { background: linear-gradient(180deg, #5b86ff, #1d3fd8);
                     box-shadow: 0 10px 26px -8px rgba(37,99,235,.6); }

    .sr { margin-bottom: 16px; }
    .sr-top { display: flex; justify-content: space-between; font-size: 14px; margin-bottom: 7px; color: #0f172a; }
    .sr-top b { font-weight: 800; }
    .sr-track { height: 11px; border-radius: 99px; background: #eef0f4; overflow: hidden; }
    .sr-fill { height: 100%; border-radius: 99px; }

    .dot-row { display: flex; gap: 8px; align-items: flex-end; height: 100px; direction: rtl; margin: 14px 0 6px; }
    .dot-col { display: flex; flex-direction: column-reverse; gap: 4px; align-items: center; flex: 1; }
    .dot { width: 10px; height: 10px; border-radius: 50%; background: #bfe3c8; }
    .dot.on { background: #16a34a; }
    .dot-labs { display: flex; gap: 8px; direction: rtl; }
    .dot-labs span { flex: 1; text-align: center; font-size: 10px; color: #9aa3b2; }
    .peak { display: inline-block; font-size: 12px; background: #fff; border: 1px solid #e7e9ee; border-radius: 99px;
            padding: 3px 12px; box-shadow: 0 6px 16px -8px rgba(15,23,42,.25); color: #334155; }

    .insight { border-radius: 26px; padding: 26px; height: 100%; color: #fff;
               background: linear-gradient(135deg, #f19a6b 0%, #4a78e0 52%, #10285f 100%);
               box-shadow: 0 18px 40px -18px rgba(16,40,95,.6); }
    .insight .pill { display: inline-block; background: rgba(255,255,255,.22); border-radius: 99px;
                     padding: 3px 14px; font-size: 12px; margin-bottom: 18px; }
    .insight .pct { font-size: 60px; font-weight: 800; line-height: 1; }
    .insight .txt { font-size: 16px; font-weight: 700; margin-top: 12px; }
    .insight .sub { font-size: 13px; opacity: .85; margin-top: 6px; }

    .stButton>button {
        width: 100%; background: #111827 !important; color: #fff !important; font-weight: 700 !important;
        border-radius: 999px !important; border: none !important; padding: 10px 22px !important;
        box-shadow: 0 10px 20px -10px rgba(17,24,39,.6); transition: all .2s ease !important;
    }
    .stButton>button:hover { background: #2563eb !important; transform: translateY(-1px); }
    .stDataFrame { border-radius: 18px; overflow: hidden; border: 1px solid #e7e9ee; }
    div[data-testid="stExpander"] { background: #fff; border-radius: 22px; border: 1px solid #eceef2; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ==================== 2. حماية الدخول ====================
def check_password() -> bool:
    """كلمة المرور من st.secrets["APP_PASSWORD"] أو متغير البيئة APP_PASSWORD.
    إن لم تُضبط كلمة مرور يعمل التطبيق بدون حماية مع تحذير."""
    expected = None
    try:
        expected = st.secrets.get("APP_PASSWORD")
    except Exception:
        pass
    expected = expected or os.environ.get("APP_PASSWORD")

    if not expected:
        st.sidebar.warning("⚠️ لا توجد كلمة مرور. اضبط APP_PASSWORD قبل النشر.")
        return True
    if st.session_state.get("auth_ok"):
        return True

    st.markdown("### 🔐 تسجيل الدخول")
    pwd = st.text_input("كلمة المرور", type="password")
    if st.button("دخول"):
        if hmac.compare_digest(pwd, str(expected)):
            st.session_state["auth_ok"] = True
            st.rerun()
        else:
            st.error("كلمة المرور غير صحيحة.")
    return False


if not check_password():
    st.stop()


# ==================== 3. طبقة البيانات (Supabase عبر REST) ====================
# الاتصال بمفتاح الخدمة (service_role) من الخادم فقط. لا تضعه في الكود ولا في GitHub.
INV_COLS = ["اسم المنتج", "الكمية المتوفرة", "سعر الشراء بالجملة (DA)", "سعر البيع المقترح (DA)"]
ORD_COLS = ["رقم", "التاريخ", "الزبون", "الهاتف", "الولاية", "المنتج",
            "المبلغ", "الشحن", "تكلفة الشراء", "حالة التوصيل"]

ST_PENDING = "قيد التوصيل 🚚"
ST_DONE = "تم التوصيل بنجاح ✅"
ST_RETURNED = "راجع / ملغى (Retour) ❌"
STATUSES = [ST_PENDING, ST_DONE, ST_RETURNED]
STATUS_TO_DB = {ST_PENDING: "pending", ST_DONE: "delivered", ST_RETURNED: "returned"}
DB_TO_STATUS = {v: k for k, v in STATUS_TO_DB.items()}


def _secret(name: str):
    value = None
    try:
        value = st.secrets.get(name)
    except Exception:
        pass
    return value or os.environ.get(name)


SUPABASE_URL = (_secret("SUPABASE_URL") or "").rstrip("/")
SUPABASE_KEY = _secret("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("إعدادات Supabase ناقصة. أضف SUPABASE_URL و SUPABASE_SERVICE_KEY في "
             ".streamlit/secrets.toml (أو كمتغيرات بيئة).")
    st.stop()


def _api(method: str, path: str, *, params=None, body=None, prefer: str | None = None):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    resp = requests.request(method, f"{SUPABASE_URL}/rest/v1/{path}", headers=headers,
                            params=params, json=body, timeout=20)
    if not resp.ok:
        raise RuntimeError(f"Supabase {resp.status_code}: {resp.text[:300]}")
    return resp.json() if resp.text else None


def load_inventory() -> pd.DataFrame:
    rows = _api("GET", "dz_products", params={"select": "*", "order": "name.asc"})
    if not rows:
        return pd.DataFrame(columns=INV_COLS)
    df = pd.DataFrame(rows).rename(columns={
        "name": INV_COLS[0], "quantity": INV_COLS[1],
        "buy_price": INV_COLS[2], "sell_price": INV_COLS[3],
    })
    return df[INV_COLS].copy()


def upsert_product(name: str, qty_add: int, buy: int, sell: int) -> None:
    existing = _api("GET", "dz_products", params={"select": "id,quantity", "name": f"eq.{name}"})
    if existing:
        _api("PATCH", "dz_products", params={"id": f"eq.{existing[0]['id']}"},
             body={"quantity": int(existing[0]["quantity"]) + int(qty_add),
                   "buy_price": int(buy), "sell_price": int(sell)})
    else:
        _api("POST", "dz_products",
             body={"name": name, "quantity": int(qty_add),
                   "buy_price": int(buy), "sell_price": int(sell)})


def adjust_stock(product: str, delta: int) -> None:
    """تعديل ذرّي للمخزون عبر دالة قاعدة البيانات."""
    if delta:
        _api("POST", "rpc/dz_adjust_stock", body={"p_name": product, "p_delta": int(delta)})


def load_orders() -> pd.DataFrame:
    rows = _api("GET", "dz_orders", params={"select": "*", "order": "id.desc"})
    if not rows:
        df = pd.DataFrame(columns=ORD_COLS)
        for c in ["رقم", "المبلغ", "الشحن", "تكلفة الشراء"]:
            df[c] = df[c].astype(int)
        return df
    df = pd.DataFrame(rows)
    when = pd.to_datetime(df["created_at"], utc=True).dt.tz_convert("Africa/Algiers")
    out = pd.DataFrame({
        "رقم": df["id"].astype(int),
        "التاريخ": when.dt.strftime("%Y-%m-%d %H:%M"),
        "الزبون": df["customer"],
        "الهاتف": df["phone"].fillna(""),
        "الولاية": df["wilaya"],
        "المنتج": df["product"],
        "المبلغ": df["amount"].astype(int),
        "الشحن": df["shipping"].astype(int),
        "تكلفة الشراء": df["buy_cost"].astype(int),
        "حالة التوصيل": df["status"].map(DB_TO_STATUS).fillna(ST_PENDING),
    })
    return out[ORD_COLS]


def insert_order(customer, phone, wilaya, product, amount, ship, buy_cost, status) -> int:
    rows = _api("POST", "dz_orders", prefer="return=representation", body={
        "customer": customer, "phone": phone, "wilaya": wilaya, "product": product,
        "amount": int(amount), "shipping": int(ship), "buy_cost": int(buy_cost),
        "status": STATUS_TO_DB[status],
    })
    return int(rows[0]["id"])


def update_order_status(order_id: int, status: str) -> None:
    _api("PATCH", "dz_orders", params={"id": f"eq.{int(order_id)}"},
         body={"status": STATUS_TO_DB[status]})


def units_out(status: str) -> int:
    """الراجع يعود للمخزون، وغيره يعتبر خارجاً منه."""
    return 0 if status == ST_RETURNED else 1


# ==================== 4. بيانات الولايات والشحن ====================
# ملاحظة: الولايات 59-69 (الجديدة) تحتاج مراجعة مع القائمة الرسمية.
WILAYAS_69 = [
    "01 - أدرار", "02 - الشلف", "03 - الأغواط", "04 - أم البواقي", "05 - باتنة",
    "06 - بجاية", "07 - بسكرة", "08 - بشار", "09 - البليدة", "10 - البويرة",
    "11 - تمنراست", "12 - تبسة", "13 - تلمسان", "14 - تيارت", "15 - تيزي وزو",
    "16 - الجزائر العاصمة", "17 - الجلفة", "18 - جيجل", "19 - سطيف", "20 - سعيدة",
    "21 - سكيكدة", "22 - سيدي بلعباس", "23 - عنابة", "24 - قالمة", "25 - قسنطينة",
    "26 - المدية", "27 - مستغانم", "28 - المسيلة", "29 - معسكر", "30 - ورقلة",
    "31 - وهران", "32 - البيض", "33 - إليزي", "34 - برج بوعريريج", "35 - بومرداس",
    "36 - الطارف", "37 - تندوف", "38 - تسمسيلت", "39 - الوادي", "40 - خنشلة",
    "41 - سوق أهراس", "42 - تيبازة", "43 - ميلة", "44 - عين الدفلى", "45 - النعامة",
    "46 - عين تموشنت", "47 - غرداية", "48 - غليزان", "49 - تيميمون", "50 - برج باجي مختار",
    "51 - أولاد جلال", "52 - بني عباس", "53 - عين صالح", "54 - عين قزام", "55 - تقرت",
    "56 - جانت", "57 - المغير", "58 - المنيعة", "59 - أفلو (الأغواط)", "60 - بريكة (باتنة)",
    "61 - قصر الشلالة (تيارت)", "62 - عين وسارة (الجلفة)", "63 - مسعد (الجلفة)",
    "64 - العلمة (سطيف)", "65 - بوسعادة (المسيلة)", "66 - شلغوم العيد (ميلة)",
    "67 - العريشة (تلمسان)", "68 - القنطرة (بسكرة)", "69 - بني ونيف (بشار)",
]

SHIP_NORTH_CENTER = {"16", "09", "35", "42"}
SHIP_FAR_SOUTH = {"11", "33", "37", "50", "53", "54", "56"}
SHIP_SOUTH = {"01", "07", "08", "30", "39", "47", "49", "51", "52", "55", "57", "58"}


def wilaya_code(name: str) -> str:
    return name.split(" - ")[0].strip()


def estimate_shipping(wilaya_name: str) -> int:
    code = wilaya_code(wilaya_name)
    if code in SHIP_NORTH_CENTER:
        return 400
    if code in SHIP_FAR_SOUTH:
        return 1000
    if code in SHIP_SOUTH:
        return 800
    return 600


PHONE_RE = re.compile(r"^0[567]\d{8}$")


def clean_phone(raw: str) -> str:
    return re.sub(r"[\s\-\.]", "", raw or "")


# ==== UI helpers ====
def h(html_str: str) -> str:
    """يجعل HTML في سطر واحد حتى لا يفسّره Markdown ككود."""
    return "".join(line.strip() for line in html_str.splitlines())


def metric_card(title: str, value: str, color: str = "#0f172a", bg: str = "#ffffff") -> str:
    return h(f"""
        <div class="dz-card" style="background:{bg};">
            <div class="dz-sub">{escape(title)}</div>
            <div class="dz-big" style="color:{color}; font-size:34px; margin-top:6px;" dir="ltr">{escape(value)}</div>
        </div>""")


def funnel_card(title: str, steps) -> str:
    """steps: [(label, value, highlighted)] - أعمدة مخطّطة تنازلية."""
    mx = max([v for _, v, _ in steps] + [1])
    cols = ""
    for label, v, hi in steps:
        height = max(8, int(v / mx * 150)) if v else 8
        cols += (f'<div class="fun-col {"hi" if hi else ""}"><div class="fun-label">{escape(label)}</div>'
                 f'<div class="fun-val">{v:,}</div><div class="fun-track">'
                 f'<div class="fun-bar {"solid" if hi else ""}" style="height:{height}px"></div></div></div>')
    return h(f'<div class="dz-card"><div class="dz-title">{escape(title)}</div><div class="fun-row">{cols}</div></div>')


def stripe_row(label: str, value_text: str, value: float, total: float, color: str) -> str:
    pct = min(100, int(value / total * 100)) if total else 0
    fill = f"repeating-linear-gradient(135deg,{color} 0 4px,{color}99 4px 8px)"
    return (f'<div class="sr"><div class="sr-top"><span>{escape(label)}</span><b dir="ltr">{escape(value_text)}</b></div>'
            f'<div class="sr-track"><div class="sr-fill" style="width:{pct}%;background:{fill}"></div></div></div>')


def dot_card(title: str, values, labels, peak_text: str, big: str, delta_text: str, delta_up: bool) -> str:
    mx = max(list(values) + [0])
    peak = list(values).index(mx) if mx else -1
    cols = ""
    for i, v in enumerate(values):
        n = round(v / mx * 8) if mx and v else 0
        dots = "".join(f'<span class="dot {"on" if i == peak else ""}"></span>' for _ in range(n))
        cols += f'<div class="dot-col">{dots}</div>'
    labs = "".join(f"<span>{escape(l)}</span>" for l in labels)
    delta = f'<span class="dz-delta {"" if delta_up else "neg"}">{escape(delta_text)}</span>'
    return h(f'<div class="dz-card"><div class="dz-title">{escape(title)}</div>'
             f'<div><span class="dz-big">{escape(big)}</span>{delta}</div>'
             f'<div class="dot-row">{cols}</div><div class="dot-labs">{labs}</div>'
             f'<div style="margin-top:10px"><span class="peak">{escape(peak_text)}</span></div></div>')


def insight_card(pct_text: str, headline: str, sub: str) -> str:
    return h(f'<div class="insight"><span class="pill">💡 رؤى</span><div class="pct">{escape(pct_text)}</div>'
             f'<div class="txt">{escape(headline)}</div><div class="sub">{escape(sub)}</div></div>')


def gap() -> None:
    st.markdown('<div class="dz-gap"></div>', unsafe_allow_html=True)
# ==== end UI helpers ====


def flash(msg: str) -> None:
    st.session_state["flash"] = msg


# ==================== 5. الهيدر والتنقل ====================
st.markdown(h("""
    <div class="page-title">منصة التاجر الجزائري</div>
    <div class="page-sub">لوحة تحكم لإدارة المبيعات والمخزون وتحليل أداء متجرك</div>
"""), unsafe_allow_html=True)

if "flash" in st.session_state:
    st.toast(st.session_state.pop("flash"), icon="✅")

st.sidebar.markdown("### ⚙️ أدوات التحكم")
SECTIONS = [
    "🏭 إدارة المخزون",
    "📦 تتبع المبيعات والولايات",
    "📊 التحليلات والرسوم البيانية",
    "💰 حاسبة الأرباح الذكية",
    "🔥 كاشف المنتجات والتريند",
    "📝 مولّد الإعلانات",
]
section = st.sidebar.radio("اختر القسم:", SECTIONS)

if st.session_state.get("auth_ok"):
    if st.sidebar.button("تسجيل الخروج"):
        st.session_state.pop("auth_ok", None)
        st.rerun()


# ==================== 6. الأقسام ====================

# --- المخزون ---
def page_inventory():
    st.subheader("🏭 إدارة السلع والمخزون")

    with st.expander("➕ إضافة منتج جديد إلى المخزون", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            name = st.text_input("اسم المنتج")
        with c2:
            qty = st.number_input("الكمية المشتراة", value=10, min_value=1)
        with c3:
            buy = st.number_input("سعر الشراء للقطعة (DA)", value=1500, step=100, min_value=0)
        with c4:
            sell = st.number_input("سعر البيع المقترح (DA)", value=3500, step=100, min_value=0)

        if st.button("حفظ المنتج في المخزون 💾"):
            name = name.strip()
            if not name:
                st.error("أدخل اسم المنتج.")
            else:
                upsert_product(name, qty, buy, sell)
                flash(f"تمت إضافة {qty} قطعة من {name}.")
                st.rerun()

    st.markdown("---")
    st.subheader("📦 حالة المخزون الحالي")
    inv = load_inventory()
    if inv.empty:
        st.info("المخزون فارغ حالياً. أضف منتجاتك الأولى من النموذج أعلاه.")
        return

    for _, row in inv[inv["الكمية المتوفرة"] <= 5].iterrows():
        if row["الكمية المتوفرة"] <= 0:
            st.error(f"⛔ المنتج **'{row['اسم المنتج']}'** نفد من المخزون!")
        else:
            st.warning(f"⚠️ المنتج **'{row['اسم المنتج']}'** تبقى منه **{row['الكمية المتوفرة']}** قطع فقط!")

    st.dataframe(inv, use_container_width=True)
    value = int((inv["الكمية المتوفرة"] * inv["سعر الشراء بالجملة (DA)"]).sum())
    st.caption(f"💼 قيمة المخزون بسعر الشراء: **{value:,} DA**")


# --- المبيعات ---
def page_sales():
    st.subheader("📦 تسجيل وتتبع الطلبيات")
    inv = load_inventory()

    with st.expander("➕ إضافة طلبية جديدة", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            customer = st.text_input("اسم الزبون")
            phone = st.text_input("رقم الهاتف", placeholder="05XXXXXXXX / 06 / 07")
            if not inv.empty:
                product = st.selectbox("اختر المنتج من المخزون", inv["اسم المنتج"].tolist())
                row = inv[inv["اسم المنتج"] == product].iloc[0]
                stock_left = int(row["الكمية المتوفرة"])
                suggested_price = int(row["سعر البيع المقترح (DA)"])
                buy_cost = int(row["سعر الشراء بالجملة (DA)"])
                st.caption(f"المتوفر: **{stock_left}** قطعة")
            else:
                product = st.text_input("اسم المنتج المباع").strip()
                stock_left, suggested_price, buy_cost = None, 3500, 0
                buy_cost = st.number_input("تكلفة شراء القطعة (DA)", value=0, step=100, min_value=0)
        with col2:
            wilaya = st.selectbox("اختر الولاية (69 ولاية ومقاطعة)", WILAYAS_69)
            # المفتاح يتغير مع الولاية/المنتج فيتحدث الافتراضي تلقائياً
            ship = st.number_input("تكلفة الشحن (DA)", value=estimate_shipping(wilaya),
                                   step=100, min_value=0, key=f"ship_{wilaya}")
            amount = st.number_input("سعر البيع (DA)", value=suggested_price, step=100,
                                     min_value=0, key=f"price_{product}")
        with col3:
            status = st.selectbox("حالة الطلبية", STATUSES)
            st.write("")
            add_btn = st.button("حفظ الطلبية 💾")

        if add_btn:
            phone_clean = clean_phone(phone)
            if not customer.strip() or not product:
                st.error("اسم الزبون والمنتج مطلوبان.")
            elif not PHONE_RE.match(phone_clean):
                st.error("رقم الهاتف غير صحيح (يجب أن يكون 10 أرقام ويبدأ بـ 05 أو 06 أو 07).")
            elif stock_left is not None and units_out(status) and stock_left <= 0:
                st.error("هذا المنتج نفد من المخزون.")
            else:
                new_id = insert_order(customer.strip(), phone_clean, wilaya, product,
                                      amount, ship, buy_cost, status)
                if stock_left is not None:
                    adjust_stock(product, -units_out(status))
                flash(f"تم تسجيل طلبية #{new_id} للزبون {customer.strip()}.")
                st.rerun()

    st.markdown("---")
    orders = load_orders()
    if orders.empty:
        st.info("لا توجد مبيعات مسجلة حتى الآن.")
        return

    # ---- تحديث حالة طلبية ----
    st.subheader("🔄 تحديث حالة طلبية")
    labels = {
        int(r["رقم"]): f"#{r['رقم']} - {r['الزبون']} - {r['المنتج']} - {r['حالة التوصيل']}"
        for _, r in orders.sort_values("رقم", ascending=False).iterrows()
    }
    u1, u2, u3 = st.columns([3, 2, 1])
    with u1:
        order_id = st.selectbox("الطلبية", list(labels.keys()), format_func=lambda k: labels[k])
    with u2:
        new_status = st.selectbox("الحالة الجديدة", STATUSES, key="new_status")
    with u3:
        st.write("")
        st.write("")
        upd = st.button("تحديث ✔️")
    if upd:
        idx = orders.index[orders["رقم"] == order_id][0]
        old_status = orders.at[idx, "حالة التوصيل"]
        if old_status == new_status:
            st.info("الحالة لم تتغير.")
        else:
            delta = units_out(old_status) - units_out(new_status)  # +1 يعيد للمخزون
            update_order_status(order_id, new_status)
            adjust_stock(orders.at[idx, "المنتج"], delta)
            flash(f"تم تحديث الطلبية #{order_id}.")
            st.rerun()

    # ---- السجل والبحث ----
    st.markdown("---")
    st.subheader("📋 سجل الطلبيات والبحث المتقدم")
    f1, f2 = st.columns(2)
    with f1:
        status_filter = st.multiselect("تصفية حسب الحالة:", STATUSES, default=STATUSES)
    with f2:
        query = st.text_input("بحث سريع (اسم الزبون أو المنتج أو الهاتف):").strip()

    view = orders[orders["حالة التوصيل"].isin(status_filter)]
    if query:
        view = view[
            view["الزبون"].str.contains(query, case=False, na=False, regex=False)
            | view["المنتج"].str.contains(query, case=False, na=False, regex=False)
            | view["الهاتف"].str.contains(query, case=False, na=False, regex=False)
        ]
    st.dataframe(view.sort_values("رقم", ascending=False), use_container_width=True)
    st.download_button(
        "📥 تصدير السجل كملف Excel (CSV)",
        view.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
        "dz_sales_report.csv", "text/csv",
    )


# --- التحليلات ---
WEEKDAYS_AR = ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]


def page_analytics():
    st.markdown('<div class="page-title" style="font-size:34px">نظرة عامة</div>', unsafe_allow_html=True)
    orders = load_orders()
    if orders.empty:
        st.warning("لا توجد بيانات مبيعات لعرض التحليلات. أضف مبيعات أولاً.")
        return

    done = orders[orders["حالة التوصيل"] == ST_DONE]
    returned = orders[orders["حالة التوصيل"] == ST_RETURNED]
    pending = orders[orders["حالة التوصيل"] == ST_PENDING]
    total, closed = len(orders), len(done) + len(returned)
    success_rate = (len(done) / closed * 100) if closed else 0.0
    revenue = int(done["المبلغ"].sum())
    pending_value = int(pending["المبلغ"].sum())
    lost_ship = int(returned["الشحن"].sum())
    profit = int((done["المبلغ"] - done["تكلفة الشراء"] - done["الشحن"]).sum() - lost_ship)

    dates = pd.to_datetime(orders["التاريخ"], errors="coerce")
    now = pd.Timestamp.now(tz="Africa/Algiers").tz_localize(None)
    last7 = int((dates >= now - pd.Timedelta(days=7)).sum())
    prev7 = int(((dates >= now - pd.Timedelta(days=14)) & (dates < now - pd.Timedelta(days=7))).sum())
    diff = last7 - prev7

    # --- الصف الأول: القمع + الإيرادات ---
    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown(funnel_card("مسار الطلبيات", [
            ("الطلبيات المسجلة", total, False),
            ("قيد التوصيل", len(pending), False),
            ("الراجعة", len(returned), False),
            ("المسلَّمة بنجاح", len(done), True),
        ]), unsafe_allow_html=True)
    with c2:
        rows = (stripe_row("محصَّل (مسلَّم)", f"{revenue:,} DA", revenue, max(revenue + pending_value, 1), "#16a34a")
                + stripe_row("قيد التوصيل (متوقع)", f"{pending_value:,} DA", pending_value, max(revenue + pending_value, 1), "#2563eb")
                + stripe_row("خسارة شحن الراجع", f"{lost_ship:,} DA", lost_ship, max(revenue + pending_value, 1), "#ec4899"))
        st.markdown(h(f'<div class="dz-card"><div class="dz-title">المداخيل</div>'
                      f'<div class="dz-big" style="margin-bottom:18px">{revenue:,} <span class="dz-sub">DA</span></div>{rows}</div>'),
                    unsafe_allow_html=True)
    gap()

    # --- الصف الثاني: الأيام + الولايات + الرؤى ---
    by_day = dates.dt.dayofweek.value_counts().reindex(range(7), fill_value=0).tolist()
    peak_day = WEEKDAYS_AR[by_day.index(max(by_day))] if max(by_day) else "-"
    top_w = orders["الولاية"].value_counts().head(4)
    wil_rows = "".join(stripe_row(w, f"{n} طلبية", n, int(top_w.max()), "#2563eb") for w, n in top_w.items())

    if closed == 0:
        headline, sub = "لا توجد طلبيات محسومة بعد", "حدّث حالة الطلبيات لتظهر نسبة التوصيل."
    else:
        headline = ("نسبة توصيل ممتازة" if success_rate >= 75 else "نسبة توصيل متوسطة" if success_rate >= 55
                    else "نسبة التوصيل منخفضة، راجع الولايات والمنتجات")
        if len(returned):
            worst = returned["الولاية"].value_counts().index[0]
            sub = f"أكثر ولاية رتوراً: {worst} ({int(returned['الولاية'].value_counts().iloc[0])})"
        else:
            sub = "لا توجد طلبيات راجعة حتى الآن."

    d1, d2, d3 = st.columns(3)
    with d1:
        st.markdown(dot_card("الطلبيات حسب اليوم", by_day, ["إثن", "ثلا", "أرب", "خمي", "جمع", "سبت", "أحد"],
                             f"الذروة: {peak_day}", f"{total}",
                             f"{diff:+d} عن الأسبوع الماضي", diff >= 0), unsafe_allow_html=True)
    with d2:
        st.markdown(h(f'<div class="dz-card"><div class="dz-title">أكثر الولايات طلباً</div>{wil_rows}</div>'),
                    unsafe_allow_html=True)
    with d3:
        st.markdown(insight_card(f"{success_rate:.0f}%", headline, sub), unsafe_allow_html=True)
    gap()

    # --- الصف الثالث: الربح + المنتجات ---
    e1, e2 = st.columns([1, 2])
    with e1:
        st.markdown(metric_card("الربح الفعلي (قبل الإعلانات)", f"{profit:,} DA",
                                "#16a34a" if profit >= 0 else "#dc2626"), unsafe_allow_html=True)
    with e2:
        if done.empty:
            st.info("لا توجد طلبيات مسلَّمة بعد لعرض أفضل المنتجات.")
        else:
            top = done.groupby("المنتج").agg(
                الطلبيات=("رقم", "count"), المداخيل=("المبلغ", "sum")
            ).sort_values("المداخيل", ascending=False)
            st.dataframe(top, use_container_width=True)


# --- حاسبة الأرباح ---
def page_calculator():
    st.subheader("💰 حاسبة الربح الصافي (بعد احتساب الرتور)")
    c1, c2 = st.columns(2)
    with c1:
        buy = st.number_input("سعر شراء السلعة (DA)", value=2000, min_value=0)
        sell = st.number_input("سعر البيع للزبون (DA)", value=4500, min_value=0)
        ship = st.number_input("تكلفة الشحن على التاجر (DA)", value=600, min_value=0)
    with c2:
        ads = st.number_input("تكلفة الإعلانات لكل طلبية (DA)", value=500, min_value=0)
        ret_cost = st.number_input("خسارة الطلبية الراجعة (DA)", value=ship, min_value=0,
                                   help="عادة تكلفة الشحن (ذهاب وإياب) + أي ضرر على السلعة. السلعة نفسها تعود للمخزون.")
        rate = st.slider("نسبة التوصيل الناجحة (%)", 0, 100, 70) / 100

    margin = sell - buy - ship  # ربح الطلبية المسلَّمة
    profit = rate * margin - (1 - rate) * ret_cost - ads
    be_den = margin + ret_cost
    breakeven = (ads + ret_cost) / be_den * 100 if be_den > 0 else None

    st.markdown("<br>", unsafe_allow_html=True)
    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown(metric_card("صافي الربح المتوقع لكل طلبية", f"{int(profit):,} DA",
                                "#16a34a" if profit > 0 else "#dc2626",
                                "#f0fdf4" if profit > 0 else "#fef2f2"), unsafe_allow_html=True)
    with k2:
        st.markdown(metric_card("ربح الطلبية المسلَّمة", f"{int(margin):,} DA"), unsafe_allow_html=True)
    with k3:
        be_txt = f"{breakeven:.0f}%" if breakeven is not None and breakeven <= 100 else "غير ممكن"
        st.markdown(metric_card("نسبة التوصيل لتغطية التكاليف", be_txt, "#2563eb"), unsafe_allow_html=True)


# --- كاشف المنتجات ---
def page_market():
    st.subheader("🔎 كاشف السوق الجزائرية")
    q = st.text_input("أدخل اسم المنتج للبحث عن أسعار المنافسين:").strip()
    if q:
        e = quote(q)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.link_button("ابحث في واد كنيس 🇩🇿", f"https://www.ouedkniss.com/s/1?keywords={e}",
                           use_container_width=True)
        with c2:
            st.link_button("ابحث في Facebook Marketplace 🛒",
                           f"https://www.facebook.com/marketplace/search/?query={e}",
                           use_container_width=True)
        with c3:
            st.link_button("مؤشر الطلب في Google Trends 📈",
                           f"https://trends.google.com/trends/explore?q={e}&geo=DZ",
                           use_container_width=True)


# --- مولّد الإعلانات ---
def page_ads():
    st.subheader("✍️ مولّد المحتوى الإعلاني")
    st.caption("يعتمد حالياً على قوالب جاهزة. يمكن ربطه بـ Claude API لاحقاً لتوليد نصوص حقيقية.")
    name = st.text_input("اسم المنتج:").strip()
    features = st.text_area("أهم المميزات (كل ميزة في سطر):")
    if st.button("توليد الإعلان 🔥"):
        if not name:
            st.error("أدخل اسم المنتج.")
            return
        lines = [ln.strip() for ln in features.splitlines() if ln.strip()]
        bullets = "\n".join(f"✅ {ln}" for ln in lines) or "✅ جودة عالية"
        t1, t2 = st.tabs(["📢 فصحى احترافية", "🇩🇿 بالدرجة الجزائرية"])
        with t1:
            st.code(
                f"🌟 جديدنا المميز: {name} 🌟\n\nأبرز المواصفات:\n{bullets}\n\n"
                "🚚 التوصيل متوفر لـ 69 ولاية والدفع عند الاستلام.\n"
                "📩 لطلب المنتج، أرسل رسالة فوراً!", language="text")
        with t2:
            st.code(
                f"يا خاوتي جبتلكم حاجة فور بزاف! 😍 {name}\n\nعلاه لازم تشريه؟\n{bullets}\n\n"
                "🚛 التوصيل متوفر كامل الولايات والدفع كي توصلك السلعة ليديك!\n"
                "سارع بطلب منتجك الآن قبل نفاذ الكمية 🔥", language="text")


PAGES = dict(zip(SECTIONS, [
    page_inventory, page_sales, page_analytics, page_calculator, page_market, page_ads,
]))
PAGES[section]()
