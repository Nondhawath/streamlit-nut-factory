import streamlit as st
import pandas as pd
import os
import datetime

st.set_page_config(page_title="Sorting Rework Process", layout="wide")

# Paths to store master data
EMP_FILE = "employee_list.xlsx"
PART_FILE = "part_code_list.xlsx"
REPORT_FILE = "sorting_report.xlsx"

# Load or initialize employee and part code data
def load_master_data():
    if os.path.exists(EMP_FILE):
        emp_df = pd.read_excel(EMP_FILE)
    else:
        emp_df = pd.DataFrame(columns=["ชื่อ"])

    if os.path.exists(PART_FILE):
        part_df = pd.read_excel(PART_FILE)
    else:
        part_df = pd.DataFrame(columns=["รหัส"])

    return emp_df, part_df

# Save uploaded master data
uploaded_emp = st.sidebar.file_uploader("อัปโหลดรายชื่อพนักงาน", type=[".xlsx"])
if uploaded_emp:
    emp_df = pd.read_excel(uploaded_emp)
    emp_df.to_excel(EMP_FILE, index=False)
    st.sidebar.success("บันทึกรายชื่อพนักงานแล้ว")

uploaded_part = st.sidebar.file_uploader("อัปโหลดรหัสงาน", type=[".xlsx"])
if uploaded_part:
    part_df = pd.read_excel(uploaded_part)
    part_df.to_excel(PART_FILE, index=False)
    st.sidebar.success("บันทึกรหัสงานแล้ว")

# Load data again
employee_df, part_df = load_master_data()

# Generate job ID
def generate_job_id():
    if os.path.exists(REPORT_FILE):
        report_df = pd.read_excel(REPORT_FILE)
    else:
        report_df = pd.DataFrame(columns=["Job ID"])

    now = datetime.datetime.now()
    prefix = f"{now.year % 100:02}{now.month:02}"
    existing = report_df[report_df['Job ID'].astype(str).str.startswith(prefix)] if not report_df.empty else pd.DataFrame()
    last_seq = max([int(str(jid)[-4:]) for jid in existing['Job ID'] if str(jid).startswith(prefix)] + [0])
    return f"{prefix}{last_seq + 1:04}"

# Load report data
if os.path.exists(REPORT_FILE):
    report_df = pd.read_excel(REPORT_FILE)
else:
    report_df = pd.DataFrame()

# Sidebar: Select Mode
mode = st.sidebar.selectbox("เลือกโหมด", ["🔍 Sorting MC", "🧪 Waiting Judgement", "🧼 Oil Cleaning", "📦 WIP Report"])

if mode == "🔍 Sorting MC":
    st.header("🔍 Sorting MC")
    with st.form("sorting_form"):
        job_id = generate_job_id()
        st.markdown(f"**Job ID:** `{job_id}`")
        name = st.selectbox("👤 ชื่อพนักงาน", employee_df['ชื่อ'].dropna().unique())
        part_code = st.selectbox("🔢 รหัสงาน", part_df['รหัส'].dropna().unique())
        qty_checked = st.number_input("✅ จำนวนที่ตรวจแล้ว", min_value=0)
        qty_ng = st.number_input("❌ จำนวน NG", min_value=0)
        qty_pending = st.number_input("⏳ จำนวนที่ยังไม่ตรวจ", min_value=0)
        status = st.selectbox("📌 สถานะ", ["รอตัดสินใจ", "Scrap", "Rework"])
        submitted = st.form_submit_button("บันทึกข้อมูล")

        if submitted:
            new_entry = pd.DataFrame([{
                "Job ID": job_id,
                "ชื่อ": name,
                "รหัส": part_code,
                "ตรวจแล้ว": qty_checked,
                "NG": qty_ng,
                "ยังไม่ตรวจ": qty_pending,
                "สถานะ": status,
                "เวลา": datetime.datetime.now(),
                "กระบวนการ": "Sorting"
            }])
            report_df = pd.concat([report_df, new_entry], ignore_index=True)
            report_df.to_excel(REPORT_FILE, index=False)
            st.success("✅ บันทึกข้อมูลเรียบร้อยแล้ว")

elif mode == "🧪 Waiting Judgement":
    st.header("🧪 Waiting Judgement")
    code = st.text_input("🔐 รหัสเข้าใช้งาน")
    if code != "Admin1":
        st.warning("กรุณาใส่รหัสให้ถูกต้อง")
    else:
        pending_df = report_df[(report_df['สถานะ'] == "รอตัดสินใจ") & (report_df['กระบวนการ'] == "Sorting")]
        for _, row in pending_df.iterrows():
            st.markdown(f"**Job ID:** `{row['Job ID']}` | รหัส: `{row['รหัส']}` | NG: {row['NG']}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"❌ Scrap {row['Job ID']}"):
                    report_df.loc[report_df['Job ID'] == row['Job ID'], ['สถานะ', 'กระบวนการ']] = ["Scrap", "จบงาน"]
            with col2:
                if st.button(f"🔁 Rework {row['Job ID']}"):
                    report_df.loc[report_df['Job ID'] == row['Job ID'], ['สถานะ', 'กระบวนการ']] = ["Rework", "Oil Cleaning"]
        report_df.to_excel(REPORT_FILE, index=False)

elif mode == "🧼 Oil Cleaning":
    st.header("🧼 Oil Cleaning")
    oil_df = report_df[(report_df['กระบวนการ'] == "Oil Cleaning") & (report_df['สถานะ'] == "Rework")]
    for _, row in oil_df.iterrows():
        st.markdown(f"**Job ID:** `{row['Job ID']}` | รหัส: `{row['รหัส']}` | NG: {row['NG']}")
        if st.button(f"✅ ล้างเสร็จแล้ว {row['Job ID']}"):
            report_df.loc[report_df['Job ID'] == row['Job ID'], 'สถานะ'] = "ล้างเสร็จแล้ว"
            report_df.loc[report_df['Job ID'] == row['Job ID'], 'กระบวนการ'] = "จบงาน"
    report_df.to_excel(REPORT_FILE, index=False)

elif mode == "📦 WIP Report":
    st.header("📦 WIP Report")
    wip_df = report_df[report_df['กระบวนการ'] != "จบงาน"]
    st.dataframe(wip_df)

    st.download_button("📥 ดาวน์โหลดรายงาน Excel", data=wip_df.to_csv(index=False), file_name="wip_report.csv")
