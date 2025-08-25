# app.py  (塗料 / 工業地坪 Catalog)
import streamlit as st
import pandas as pd
from io import BytesIO
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
import os, math, datetime as dt

# =====================
# 基本設定 & 多語字典
# =====================
st.set_page_config(page_title="Coatings & Flooring Catalog", layout="wide")

TEXT = {
    "lang": {"中文": "語言 / Language", "English": "Language / 語言"},
    "title": {"中文": "For 意慧女士 | 塗料｜工業地坪 產品型錄 Demo", "English": "Coatings & Industrial Flooring Catalog Demo"},
    "caption": {
        "中文": "Excel 駆動：搜尋/篩選、批次更新（Upsert）、PDF 匯出、與中英文切換。",
        "English": "Excel-driven: search/filter, batch upsert, PDF export, with bilingual UI."
    },
    "filters": {"中文": "篩選條件", "English": "Filters"},
    "search": {"中文": "關鍵字（系列/型號/說明/性能）", "English": "Search (Series/Model/Spec/Performance)"},
    "series": {"中文": "系列", "English": "Series"},
    "resin": {"中文": "成分", "English": "Composition"},
    "thick": {"中文": "厚度", "English": "Thickness"},
    "method": {"中文": "施工方式", "English": "Application Method"},
    "env": {"中文": "適用環境", "English": "Applications"},
    "cert": {"中文": "認證", "English": "Certifications"},
    "color": {"中文": "顏色", "English": "Color"},
    "more": {"中文": "更多選項", "English": "More Options"},
    "view": {"中文": "顯示模式", "English": "View Mode"},
    "view_all": {"中文": "全部產品", "English": "All Products"},
    "view_new": {"中文": "僅顯示新增的", "English": "Only New"},
    "view_upd": {"中文": "僅顯示更新過的", "English": "Only Updated"},
    "list": {"中文": "產品列表（{n} 筆）", "English": "Product List ({n} items)"},
    "model": {"中文": "型號", "English": "Model"},
    "spec": {"中文": "規格說明", "English": "Specification"},
    "perf": {"中文": "性能指標", "English": "Performance"},
    "img_fail": {"中文": "測試", "English": "TEST"},
    "export": {"中文": "輸出 PDF", "English": "Export PDF"},
    "export_desc": {"中文": "將目前篩選後的清單輸出為產品型錄 PDF。", "English": "Export the filtered list as a catalog PDF."},
    "gen_pdf": {"中文": "產生 PDF", "English": "Generate PDF"},
    "dl_pdf": {"中文": "下載 產品型錄.pdf", "English": "Download Catalog.pdf"},
    "pdf_h1": {"中文": "塗料 / 工業地坪 產品型錄", "English": "Coatings & Industrial Flooring Catalog"},
    "pdf_h2": {"中文": "（內容由 Excel 匯入，可即時更新）", "English": "(Content imported from Excel, updates in real time)"},
    "no_img": {"中文": "無圖片", "English": "No Image"},
    "upsert": {"中文": "批次更新 / 新增 (Upsert)", "English": "Batch Update / Insert (Upsert)"},
    "up_exp": {"中文": "上傳更新檔 → 預覽差異 → 套用", "English": "Upload Update File → Preview Diff → Apply"},
    "up_ul": {
        "中文": "上傳更新 Excel（需欄位：系列、型號、顏色、成分、厚度、施工方式、性能指標、適用環境、認證、規格說明、圖片路徑）",
        "English": "Upload update Excel (columns required: Series, Model, Color, Composition, Thickness, Method, Performance, Applications, Certifications, Spec, ImagePath)"
    },
    "miss": {"中文": "更新檔缺少欄位：", "English": "Missing columns in update file: "},
    "diff": {"中文": "🆕 新增：{a} 筆，✏️ 變更：{b} 筆，✅ 相同：{c} 筆",
             "English": "🆕 New: {a}  | ✏️ Updated: {b}  | ✅ Unchanged: {c}"},
    "apply": {"中文": "套用更新", "English": "Apply Update"},
    "bak": {"中文": "已自動備份：", "English": "Backup created: "},
    "ok": {"中文": "更新完成！重新整理頁面即可查看最新清單。", "English": "Update completed! Refresh to see the latest list."},
    "notfound": {"中文": "找不到 {f}，已自動建立樣板。", "English": "Cannot find {f}. A sample sheet has been created."}
}
def T(k, lang): return TEXT[k][lang]

# 語言選擇
lang = st.sidebar.selectbox(T("lang", "中文"), ["中文", "English"], index=0)
st.title(T("title", lang))
st.caption(T("caption", lang))

# =====================
# 基礎設定
# =====================
DEFAULT_EXCEL = "coatings_example.xlsx"
REQ = ["系列","型號","顏色","成分","厚度","施工方式","性能指標","適用環境","認證","規格說明","圖片路徑"]

def load_excel(p): return pd.read_excel(p).fillna("")
def save_excel(df, p): df.to_excel(p, index=False)
def backup_excel(p):
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = p.replace(".xlsx", f"_{ts}.xlsx")
    os.replace(p, bak); return bak
def normalize_key(s): return str(s).strip().lower()

# 若不存在就自動建立
def ensure_excel(p):
    if os.path.exists(p):
        return load_excel(p)
    os.makedirs("images", exist_ok=True)
    sample = pd.DataFrame([
        ["環氧樹脂","EPX-1000","綠色","Epoxy","2mm","自流平","抗壓≥80MPa; 耐酸/鹼; 耐磨耗","停車場, 工廠","RoHS","標準耐磨型地坪","images/epx_1000.png"],
        ["PU 耐磨","PU-2000","灰色","PU","3mm","鏝抹","耐磨耗<0.03g; 耐油污","食品加工, 醫療","REACH","耐磨耐化學型","images/pu_2000.png"],
        ["導電防靜電","ESD-3000","黑色","Epoxy","2mm","滾塗","表面電阻 10^6 Ω; 抗塵","電子廠, 無塵室","抗菌報告","導電防靜電地坪","images/esd_3000.png"],
        ["快速固化","MMA-4000","藍色","MMA","4mm","自流平","低溫施工; 2小時通車","冷凍庫, 室外","—","甲基丙烯酸甲酯快速固化","images/mma_4000.png"],
    ], columns=REQ)
    save_excel(sample, p)
    st.info(T("notfound", lang).format(f=p))
    return sample

df = ensure_excel(DEFAULT_EXCEL)

# 初始化 upsert 狀態
if "upsert_new" not in st.session_state: st.session_state.upsert_new = []
if "upsert_update" not in st.session_state: st.session_state.upsert_update = []

# =====================
# 側邊欄：搜尋 + 篩選 + 顯示模式
# =====================
with st.sidebar:
    st.header(T("filters", lang))
    q = st.text_input(T("search", lang))

    def ms(col, label_key):
        if col in df.columns and not df.empty:
            opts = sorted([x for x in df[col].astype(str).unique().tolist() if x])
            return st.multiselect(T(label_key, lang), opts)
        return []

    ser_f = ms("系列", "series")
    res_f = ms("成分", "resin")
    thk_f = ms("厚度", "thick")
    mtd_f = ms("施工方式", "method")
    env_f = ms("適用環境", "env")
    crt_f = ms("認證", "cert")
    col_f = ms("顏色", "color")

    st.markdown("---")
    view_opt = [T("view_all", lang), T("view_new", lang), T("view_upd", lang)]
    view_mode = st.selectbox(T("view", lang), view_opt, index=0)

# 基礎篩選
filtered = df.copy()
if not df.empty and q:
    ql = q.lower()
    filtered = filtered[filtered.apply(lambda r: ql in (" ".join(r.astype(str).values)).lower(), axis=1)]
def apply_val(col, vals):
    global filtered
    if vals and col in filtered.columns:
        filtered = filtered[filtered[col].astype(str).isin(vals)]
for col, vals in [
    ("系列", ser_f), ("成分", res_f), ("厚度", thk_f), ("施工方式", mtd_f),
    ("適用環境", env_f), ("認證", crt_f), ("顏色", col_f)
]: apply_val(col, vals)

# 顯示模式（接 Upsert）
if view_mode == T("view_new", lang) and st.session_state.upsert_new:
    filtered = filtered[filtered["型號"].isin(st.session_state.upsert_new)]
elif view_mode == T("view_upd", lang) and st.session_state.upsert_update:
    filtered = filtered[filtered["型號"].isin(st.session_state.upsert_update)]

st.subheader(T("list", lang).format(n=len(filtered)))

# =====================
# 卡片式展示
# =====================
cols_per_row = 3
rows = math.ceil(len(filtered) / cols_per_row) if len(filtered) else 0
records = filtered.to_dict(orient="records") if len(filtered) else []

def label_pair(key, val):
    if lang == "中文":
        return f"**{key}**：{val}"
    mapping = {"系列":"Series","型號":"Model","顏色":"Color","成分":"Composition","厚度":"Thickness",
               "施工方式":"Method","性能指標":"Performance","適用環境":"Applications","認證":"Certifications",
               "規格說明":"Specification"}
    return f"**{mapping.get(key, key)}**: {val}"

for i in range(rows):
    row_cards = records[i*cols_per_row:(i+1)*cols_per_row]
    cols = st.columns(cols_per_row)
    for col, item in zip(cols, row_cards):
        with col:
            img_path = str(item.get("圖片路徑", ""))
            try:
                st.image(img_path, use_container_width=True)
            except Exception:
                st.image(Image.new("RGB",(600,400),(230,230,230)),
                         use_container_width=True, caption=T("img_fail", lang))

            for f in ["系列","型號","顏色","成分","厚度","施工方式","性能指標","適用環境","認證","規格說明"]:
                v = str(item.get(f, "")).strip()
                if v:
                    st.markdown(label_pair(f, v), unsafe_allow_html=True)

st.divider()

# =====================
# PDF 匯出（多語）
# =====================
def make_catalog_pdf(items, lang_sel):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    margin = 15*mm

    def header():
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, H - margin + 2*mm, TEXT["pdf_h1"][lang_sel])
        c.setFont("Helvetica", 9)
        c.drawString(margin, H - margin - 3*mm, TEXT["pdf_h2"][lang_sel])
        c.line(margin, H - margin - 5*mm, W - margin, H - margin - 5*mm)

    header()
    y = H - margin - 12*mm
    img_max_w, img_max_h = 70*mm, 42*mm
    line_gap = 6*mm

    cap = {
        "中文": {"Series":"系列","Model":"型號","Color":"顏色","Composition":"成分","Thickness":"厚度",
                 "Method":"施工方式","Performance":"性能指標","Applications":"適用環境","Cert":"認證","Spec":"規格說明"},
        "English": {"Series":"Series","Model":"Model","Color":"Color","Composition":"Composition","Thickness":"Thickness",
                    "Method":"Method","Performance":"Performance","Applications":"Applications","Cert":"Certifications","Spec":"Specification"}
    }[lang_sel]

    for it in items:
        if y < margin + img_max_h + 32*mm:
            c.showPage(); header(); y = H - margin - 12*mm

        # 圖片
        img_path = str(it.get("圖片路徑",""))
        img_reader = None
        if os.path.exists(img_path):
            try:
                img_reader = ImageReader(img_path)
                iw, ih = Image.open(img_path).size
                s = min(img_max_w/iw, img_max_h/ih)
                dw, dh = iw*s, ih*s
                c.drawImage(img_reader, margin, y - dh, width=dw, height=dh, preserveAspectRatio=True, mask='auto')
            except Exception:
                img_reader = None
        if not img_reader:
            c.rect(margin, y - img_max_h, img_max_w, img_max_h)
            c.setFont("Helvetica", 8)
            c.drawCentredString(margin + img_max_w/2, y - img_max_h/2, TEXT["no_img"][lang_sel])

        # 文字
        tx = margin + img_max_w + 10*mm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(tx, y, f"{cap['Model']}: {it.get('型號','')}")
        c.setFont("Helvetica", 10)
        liney = y - 14

        def draw(label, key):
            nonlocal liney
            val = str(it.get(key, "")).strip()
            if val:
                c.drawString(tx, liney, f"{label}: {val}")
                liney -= 12

        draw(cap["Series"], "系列")
        draw(cap["Color"], "顏色")
        draw(cap["Composition"], "成分")
        draw(cap["Thickness"], "厚度")
        draw(cap["Method"], "施工方式")
        draw(cap["Performance"], "性能指標")
        draw(cap["Applications"], "適用環境")
        draw(cap["Cert"], "認證")
        draw(cap["Spec"], "規格說明")

        y = liney - line_gap

    c.save(); buf.seek(0); return buf

st.subheader(T("export", lang))
st.write(T("export_desc", lang))
if st.button(T("gen_pdf", lang)):
    pdf = make_catalog_pdf(filtered.to_dict(orient="records"), lang)
    st.download_button(T("dl_pdf", lang), data=pdf,
                       file_name=("產品型錄.pdf" if lang=="中文" else "Catalog.pdf"),
                       mime="application/pdf")

st.divider()

# =====================
# 批次更新 / 新增 (Upsert)
# =====================
st.subheader(T("upsert", lang))
with st.expander(T("up_exp", lang), expanded=False):
    up = st.file_uploader(T("up_ul", lang), type=["xlsx"])
    if up:
        df_up = pd.read_excel(up).fillna("")
        miss = set(REQ) - set(df_up.columns)
        if miss:
            st.error(T("miss", lang) + "、".join(miss))
        else:
            # 唯一鍵：系列+型號
            if not df.empty:
                df["_key"] = (df["系列"].astype(str) + "|" + df["型號"].astype(str)).map(normalize_key)
            else:
                df["_key"] = []
            df_up["_key"] = (df_up["系列"].astype(str) + "|" + df_up["型號"].astype(str)).map(normalize_key)

            key_m = set(df["_key"].tolist()) if len(df) else set()
            key_u = set(df_up["_key"].tolist())

            to_insert = key_u - key_m
            to_check  = key_u & key_m

            updates, same = [], []
            for k in to_check:
                row_m = df.loc[df["_key"]==k, REQ].iloc[0]
                row_u = df_up.loc[df_up["_key"]==k, REQ].iloc[0]
                if any(str(row_m[c]) != str(row_u[c]) for c in REQ):
                    updates.append(k)
                else:
                    same.append(k)

            st.write(T("diff", lang).format(a=len(to_insert), b=len(updates), c=len(same)))
            st.session_state.upsert_new = df_up[df_up["_key"].isin(to_insert)]["型號"].tolist()
            st.session_state.upsert_update = df_up[df_up["_key"].isin(updates)]["型號"].tolist()

            if st.button(T("apply", lang), type="primary"):
                if os.path.exists(DEFAULT_EXCEL):
                    bak = backup_excel(DEFAULT_EXCEL)
                    st.info(T("bak", lang) + bak)

                if len(df):
                    base = df.set_index("_key")
                else:
                    base = pd.DataFrame(columns=REQ + ["_key"]).set_index("_key")

                for _, r in df_up.iterrows():
                    base.loc[r["_key"], REQ] = r[REQ]

                out = base.reset_index()[REQ].fillna("")
                out.sort_values(by=["系列","型號"], inplace=True)
                save_excel(out, DEFAULT_EXCEL)
                st.success(T("ok", lang))
