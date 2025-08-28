import streamlit as st
import pandas as pd
from io import StringIO
from datetime import datetime

st.set_page_config(page_title="Streamlit 商業原型（投資人版＋型錄生成）", page_icon="⚡", layout="wide")

# =========================
# 假資料 & 商業邏輯（共用）
# =========================
KPI_ROWS = [
    {"metric": "交期達成率", "value": 95, "delta": "+2%"},
    {"metric": "一次合格率", "value": 98, "delta": "+1%"},
    {"metric": "整體毛利率", "value": 31, "delta": "+3%"},
]
TREND = pd.DataFrame({
    "month": pd.date_range("2024-01-01", periods=8, freq="M"),
    "on_time_rate": [88, 90, 92, 91, 93, 94, 95, 96],
})
PRICE_RULES = pd.DataFrame([
    {"product":"A100", "base_price":1000, "addon_fast":150, "addon_premium":200, "lead_days":7},
    {"product":"B200", "base_price":1800, "addon_fast":200, "addon_premium":300, "lead_days":10},
    {"product":"C300", "base_price":2500, "addon_fast":250, "addon_premium":500, "lead_days":14},
])

@st.cache_data(show_spinner=False)
def list_products():
    return PRICE_RULES["product"].tolist()

def calc_quote(product:str, qty:int, use_fast:bool, use_premium:bool, discount:int):
    row = PRICE_RULES[PRICE_RULES["product"]==product].iloc[0]
    unit = row["base_price"] + (row["addon_fast"] if use_fast else 0) + (row["addon_premium"] if use_premium else 0)
    subtotal = unit * qty
    discount_amt = subtotal * (discount/100)
    total = subtotal - discount_amt
    lead = row["lead_days"] - (2 if use_fast else 0) + (1 if use_premium else 0)  # 示意規則
    est_margin = 0.28 + (0.03 if use_premium else 0) - (0.01 if discount>=10 else 0)
    return {
        "unit": unit,
        "subtotal": subtotal,
        "discount_amt": discount_amt,
        "total": total,
        "lead": max(1, lead),
        "margin": est_margin
    }

def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buff = StringIO()
    df.to_csv(buff, index=False)
    return buff.getvalue().encode("utf-8")

def make_catalog_markdown(df: pd.DataFrame, currency: str) -> bytes:
    """把產品表轉成簡單 Markdown 型錄（每品一段）。"""
    lines = ["# 產品型錄", f"_生成時間：{datetime.now().isoformat(timespec='seconds')}_", ""]
    for _, r in df.iterrows():
        attrs = (str(r.get("key_features","")) or "").split(";")
        bullets = "\n".join([f"- {a.strip()}" for a in attrs if a.strip()][:5])
        img = str(r.get("image_url","")).strip()
        if img:
            lines.append(f"![{r['name']}]({img})")
        lines += [
            f"## {r['sku']}｜{r['name']}",
            f"**售價**：{currency} {r['price_selling']}",
            bullets if bullets else "- （待補關鍵賣點）",
            "",
            str(r.get("description","")).strip(),
            ""
        ]
    return "\n".join(lines).encode("utf-8")

# =========================
# 側邊欄（選單切換）
# =========================
# 側邊欄（選單切換）
st.sidebar.title("功能")
menu = st.sidebar.selectbox("選單", ["儀表板＋報價", "資料整合／型錄自動化"], index=0)


# ============= 子頁 1：儀表板＋報價 =============
if menu == "儀表板＋報價":
    st.title("⚡ Streamlit 商業原型（投資人版：一頁三區塊）")
    st.caption("看得到價值、摸得到功能、想得到擴張。")
    st.toast("供應商 A 出現交期風險，已切換快速產線（示意）", icon="⚠️")

    # 區塊 1：KPI
    st.subheader("1) KPI 快照")
    c1, c2, c3 = st.columns(3)
    for col, row in zip([c1,c2,c3], KPI_ROWS):
        col.metric(row["metric"], row["value"], row["delta"])
    st.line_chart(TREND.set_index("month"), y="on_time_rate", height=240)
    with st.expander("這代表什麼？", expanded=False):
        st.markdown(
            "- 即時把分散的 Excel/DB 數據變成決策畫面\n"
            "- `st.metric` 與 `st.line_chart` 幾行就能完成\n"
            "- 這就是我們**交付速度**的來源"
        )
    st.divider()

    # 區塊 2：報價引擎
    st.subheader("2) 關鍵流程：報價引擎（核心邏輯 + 交付輸出）")
    with st.form("quote", clear_on_submit=False):
        left, right = st.columns(2)
        with left:
            product = st.selectbox("產品型號", list_products(), index=0)
            qty = st.number_input("數量", value=100, min_value=1, step=10)
            discount = st.slider("折扣（%）", 0, 30, value=5)
        with right:
            use_fast = st.checkbox("快速交期（+費用，-2 天）", value=True)
            use_premium = st.checkbox("高階版（+功能，毛利↑）", value=False)
            customer = st.text_input("客戶名稱", value="範例股份有限公司")
        submitted = st.form_submit_button("計算報價")

    if submitted:
        with st.spinner("計算中…"):
            res = calc_quote(product, qty, use_fast, use_premium, discount)

        m1, m2, m3 = st.columns(3)
        m1.metric("單價", f"${res['unit']:.0f}")
        m2.metric("總價(未稅)", f"${res['total']:.0f}", delta=f"-{res['discount_amt']:.0f} 折扣")
        m3.metric("交期(天)", res["lead"])
        st.progress(int(res["margin"]*100), text=f"毛利率估：{res['margin']*100:.1f}%")

        df_quote = pd.DataFrame([{
            "date": datetime.now().date().isoformat(),
            "customer": customer,
            "product": product,
            "qty": qty,
            "unit_price": int(res["unit"]),
            "subtotal": int(res["subtotal"]),
            "discount_pct": discount,
            "discount_amt": int(res["discount_amt"]),
            "total": int(res["total"]),
            "lead_days": res["lead"]
        }])
        st.dataframe(df_quote, use_container_width=True, height=120)
        st.download_button(
            "下載報價（CSV）",
            data=df_to_csv_bytes(df_quote),
            file_name=f"quote_{customer}.csv",
            mime="text/csv",
            use_container_width=True
        )

    st.divider()
    st.subheader("3) 落地與擴張（能不能長大？）")
    with st.expander("技術路線（投資人關心的三件事）", expanded=True):
        st.markdown(
            """
- **權限/SSO**：反向代理或 Auth0；密鑰以 `secrets.toml` 管理
- **資料庫**：Postgres/MySQL/Snowflake；`st.cache_data` 快取昂貴查詢
- **長任務**：Celery / Cloud Tasks；前端 `st.status` + 輪詢顯示進度
            """
        )
    st.caption("※ Demo 數據與規則，用於展示從『流程 → 產品化』的速度與可擴性。")

# ============= 子頁 2：資料整合／型錄自動化 =============
elif menu == "資料整合／型錄自動化":
    st.title("📚 資料讀取整合 ＆ 型錄自動化生成（示例）")
    st.caption("把 Excel/CSV 里的產品表，1 分鐘生成『價格＋賣點』型錄供銷售使用。")

    # 資料來源：上傳或貼上
    st.subheader("A. 匯入資料")
    col_u1, col_u2 = st.columns([2,1])
    with col_u1:
        up = st.file_uploader("上傳 CSV（UTF-8）", type=["csv"])
        st.caption("欄位建議：sku, name, description, base_price, key_features（以分號 ; 分隔）, image_url（可選）")
    with col_u2:
        if st.button("下載範例 CSV"):
            sample = pd.DataFrame([
                {"sku":"TX-100", "name":"機能紡織布A", "description":"透氣、耐磨，適用戶外機能服。",
                 "base_price": 280, "key_features":"透氣;快乾;耐磨", "image_url":""},
                {"sku":"TX-220", "name":"抗菌銀離子布", "description":"長效抗菌，貼身衣物適用。",
                 "base_price": 360, "key_features":"抗菌;親膚;可水洗", "image_url":""},
            ])
            st.download_button("範例 CSV 下載", data=df_to_csv_bytes(sample),
                               file_name="catalog_sample.csv", mime="text/csv")

    df_raw = None
    if up:
        try:
            df_raw = pd.read_csv(up)
        except Exception as e:
            st.error(f"CSV 讀取失敗：{e}")

    st.subheader("B. 規則與整合（售價計算 / 欄位校驗）")
    c1, c2, c3 = st.columns(3)
    with c1:
        markup_pct = st.slider("加價率（%）", 0, 100, 25)
    with c2:
        currency = st.selectbox("幣別", ["NT$", "USD$", "RMB¥"], index=0)
    with c3:
        round_to = st.selectbox("售價進位", ["1", "10", "50", "100"], index=1)

    # 若沒有上傳，用內建範例
    if df_raw is None:
        st.info("未上傳檔案，使用內建範例。")
        df_raw = pd.DataFrame([
            {"sku":"TX-100", "name":"機能紡織布A", "description":"透氣、耐磨，適用戶外機能服。",
             "base_price": 280, "key_features":"透氣;快乾;耐磨", "image_url":""},
            {"sku":"TX-220", "name":"抗菌銀離子布", "description":"長效抗菌，貼身衣物適用。",
             "base_price": 360, "key_features":"抗菌;親膚;可水洗", "image_url":""},
        ])

    # 欄位檢查
    required_cols = ["sku","name","base_price"]
    missing = [c for c in required_cols if c not in df_raw.columns]
    if missing:
        st.error(f"缺少必要欄位：{missing}")
    else:
        # 計算售價
        df = df_raw.copy()
        df["base_price"] = pd.to_numeric(df["base_price"], errors="coerce").fillna(0)
        df["price_selling"] = (df["base_price"] * (1 + markup_pct/100.0)).round(0)
        step = int(round_to)
        if step > 1:
            df["price_selling"] = (df["price_selling"] / step).round(0) * step

        # 洗出前三個賣點
        def top3_feats(x):
            parts = str(x).split(";")
            return "; ".join([p.strip() for p in parts if p.strip()][:3])
        df["top_features"] = df["key_features"].apply(top3_feats) if "key_features" in df.columns else ""

        # 展示整合後資料
        st.subheader("C. 預覽整合後資料")
        view = df[["sku","name","price_selling","top_features"] + 
                  ([c for c in ["description","image_url"] if c in df.columns])]
        st.dataframe(view.rename(columns={"price_selling":"售價", "top_features":"關鍵賣點"}),
                     use_container_width=True, height=240)

        # 下載：CSV / Markdown 型錄
        st.subheader("D. 生成與下載")
        cdl1, cdl2 = st.columns(2)
        with cdl1:
            st.download_button("下載整合後資料（CSV）",
                               data=df_to_csv_bytes(view),
                               file_name="catalog_integrated.csv",
                               mime="text/csv",
                               use_container_width=True)
        with cdl2:
            md_bytes = make_catalog_markdown(
                df.assign(price_selling=df["price_selling"].astype(int)),
                currency=currency
            )
            st.download_button("下載 Markdown 型錄（.md）",
                               data=md_bytes,
                               file_name="catalog.md",
                               mime="text/markdown",
                               use_container_width=True)

        with st.expander("這頁面展示了什麼整合能力？", expanded=False):
            st.markdown(
                "- **資料讀取**：CSV 上傳（也可改為資料庫/Google Sheet）\n"
                "- **規則引擎**：依加價率與進位規則計算售價\n"
                "- **特徵萃取**：把 `key_features` 轉成前 3 個賣點\n"
                "- **輸出**：一鍵下載整合 CSV，或輸出 Markdown 型錄"
            )

# ============ 底部說明 ============
st.sidebar.markdown("---")
st.sidebar.caption("Demo 數據僅供展示流程 → 產品化的速度與可擴性。")
