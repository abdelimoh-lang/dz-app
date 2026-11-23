import os
import re
import hmac
from datetime import datetime
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
        direction: rtl;
        text-align: right;
    }
    .stApp { background-color: #f8fafc; }

    .header-box {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        padding: 24px; border-radius: 16px; color: white; margin-bottom: 25px;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,.1); border-right: 6px solid #10b981;
    }
    .header-title { font-size: 28px; font-weight: 800; margin: 0; color: #fff; }
    .header-subtitle { font-size: 15px; color: #94a3b8; margin-top: 5px; }

    .metric-card {
        background: #fff; border-radius: 14px; padding: 20px; text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,.05); border: 1px solid #e2e8f0;
        transition: transform .2s ease, box-shadow .2s ease;
    }
    .metric-card:hover { transform: translateY(-3px); box-shadow: 0 10px 15px -3px rgba(0,0,0,.1); }
    .metric-title { font-size: 14px; color: #64748b; font-weight: 600; margin-bottom: 8px; }
    .metric-value { font-size: 26px; font-weight: 800; color: #0f172a; }

    .stButton>button {
        width: 100%; background-color: #10b981 !important; color: white !important;
        font-weight: 700 !important; border-radius: 10px !important; border: none !important;
        padding: 10px 20px !important; transition: all .3s ease !important;
    }
    .stButton>button:hover { background-color: #059669 !important; transform: translateY(-1px); }
    section[data-testid="stSidebar"] { background-color: #fff !important; border-left: 1px solid #e2e8f0; }
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


def metric_card(title: str, value: str, color: str = "#0f172a", bg: str = "#ffffff") -> str:
    return f"""
        <div class="metric-card" style="background:{bg};">
            <div class="metric-title">{title}</div>
            <div class="metric-value" style="color:{color};">{value}</div>
        </div>"""


def flash(msg: str) -> None:
    st.session_state["flash"] = msg


# ==================== 5. الهيدر والتنقل ====================
st.markdown("""
    <div class="header-box">
        <div class="header-title">🇩🇿 منصة ذكاء الأعمال للتجار الجزائريين</div>
        <div class="header-subtitle">لوحة تحكم كاملة لإدارة المبيعات، المخزون، وتحليل السوق الجزائري</div>
    </div>
""", unsafe_allow_html=True)

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
def page_analytics():
    st.subheader("📊 لوحة الأداء والرسوم البيانية")
    orders = load_orders()
    if orders.empty:
        st.warning("لا توجد بيانات مبيعات لعرض التحليلات. أضف مبيعات أولاً.")
        return

    done = orders[orders["حالة التوصيل"] == ST_DONE]
    returned = orders[orders["حالة التوصيل"] == ST_RETURNED]
    total = len(orders)
    closed = len(done) + len(returned)  # الطلبيات المحسومة فقط
    success_rate = (len(done) / closed * 100) if closed else 0.0
    revenue = int(done["المبلغ"].sum())
    # الربح الفعلي: المسلَّم = بيع - شراء - شحن ، والراجع = خسارة الشحن (قبل الإعلانات)
    profit = int((done["المبلغ"] - done["تكلفة الشراء"] - done["الشحن"]).sum() - returned["الشحن"].sum())

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(metric_card("إجمالي الطلبيات", str(total)), unsafe_allow_html=True)
    with m2:
        st.markdown(metric_card("نسبة التوصيل الناجحة", f"{success_rate:.1f}%", "#10b981"), unsafe_allow_html=True)
    with m3:
        st.markdown(metric_card("المداخيل المحصلة", f"{revenue:,} DA", "#2563eb"), unsafe_allow_html=True)
    with m4:
        st.markdown(metric_card("الربح الفعلي (قبل الإعلانات)", f"{profit:,} DA",
                                "#16a34a" if profit >= 0 else "#dc2626"), unsafe_allow_html=True)
    st.caption("نسبة التوصيل تحسب على الطلبيات المحسومة فقط (مسلَّمة أو راجعة)، دون الطلبيات قيد التوصيل.")

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🗺️ أكثر الولايات شراءً")
        st.bar_chart(orders["الولاية"].value_counts())
    with c2:
        st.subheader("🚚 توزيع حالات التوصيل")
        st.bar_chart(orders["حالة التوصيل"].value_counts())

    st.subheader("🏆 أفضل المنتجات (المسلَّمة)")
    if done.empty:
        st.info("لا توجد طلبيات مسلَّمة بعد.")
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
