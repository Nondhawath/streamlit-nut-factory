import streamlit as st
import pandas as pd
import datetime
import os
from io import BytesIO

st.set_page_config(page_title="Nut Sorting Process", layout="wide")
st.title("📦 ระบบจัดการงาน Sorting โรงงานน๊อต")

# กำหนดไฟล์รายงานหลัก
REPORT_FILE = "sorting_report.xlsx"
EMP_FILE = "employee_list.xlsx"
PART_FILE = "part_code_list.xlsx"

# โหลด/จำค่าไฟล์ล่าสุด
if EMP_FILE in os.listdir():
    employee_df = pd.read_excel(EMP_FILE)
else:
    employee_df = pd.read_excel("/mnt/data/รายชื่อพนักงานแผนก Final Inspection.xlsx")
    employee_df.to_excel(EMP_FILE, index=False)

if PART_FILE in os.listdir():
    part_df = pd.read_excel(PART_FILE)
else:
    part_df = pd.read_excel("/mnt/data/Master list SCS part name.xlsx")
    part_df.to_excel(PART_FILE, index=False)

# โหลดรายงานเดิมหรือสร้างใหม่
if os.path.exists(REPORT_FILE):
    report_df = pd.read_excel(REPORT_FILE)
else:
    report_df = pd.DataFrame()

# ===== ฟังก์ชันสร้าง Job ID =====
def generate_job_id():
    now = datetime.datetime.now()
    prefix = now.strftime("%y%m")  # เช่น 2505
    if not report_df.empty and 'Job ID' in report_df.columns:
        report_df['Job ID'] = report_df['Job ID'].astype(str)
        existing = report_df[report_df['Job ID'].str.startswith(prefix)]
        if not existing.empty:
            last_seq = max([int(jid[-4:]) for jid in existing['Job ID'] if jid[-4:].isdigit()])
        else:
            last_seq = 0
    else:
        last_seq = 0
    return f"{prefix}{last_seq + 1:04d}"

# ====== Sidebar: Upload อัปเดตข้อมูล ======
st.sidebar.header("📂 อัปโหลดไฟล์ข้อมูลใหม่")
emp_upload = st.sidebar.file_uploader("อัปโหลดรายชื่อพนักงาน (Excel)", type="xlsx")
if emp_upload:
    df = pd.read_excel(emp_upload)
    if 'ชื่อ' in df.columns:
        df.to_excel(EMP_FILE, index=False)
        st.sidebar.success("อัปเดตรายชื่อพนักงานแล้ว กรุณารีเฟรชหน้า")

part_upload = st.sidebar.file_uploader("อัปโหลดรหัสงาน (Excel)", type="xlsx")
if part_upload:
    df = pd.read_excel(part_upload)
    if 'รหัส' in df.columns:
        df.to_excel(PART_FILE, index=False)
        st.sidebar.success("อัปเดตรหัสงานแล้ว กรุณารีเฟรชหน้า")

# ====== Main Layout ======
mode = st.selectbox("เลือกโหมดกระบวนการ", ["Sorting MC", "Waiting Judgement", "Oil Cleaning"])

if mode == "Sorting MC":
    with st.form("sorting_form"):
        job_id = generate_job_id()
        st.markdown(f"### 🆔 Job ID: `{job_id}`")
        date = st.date_input("📅 วันที่", value=datetime.date.today())
        employee = st.selectbox("👷‍♂️ ผู้ตรวจสอบ", employee_df['ชื่อ'].dropna().unique())
        part_code = st.selectbox("🔢 รหัสงาน", part_df['รหัส'].dropna().unique())
        qty_checked = st.number_input("✅ จำนวนที่ตรวจ", min_value=0)
        qty_ng = st.number_input("❌ จำนวน NG", min_value=0)
        qty_pending = st.number_input("⏳ จำนวนที่ยังไม่ตรวจ", min_value=0)
        status = st.selectbox("📌 สถานะเบื้องต้น", ["รอตัดสินใจ"])
        submitted = st.form_submit_button("💾 บันทึกข้อมูล")
        if submitted:
            new_row = pd.DataFrame([{
                "Job ID": job_id,
                "วันที่": date,
                "ผู้ตรวจสอบ": employee,
                "รหัสงาน": part_code,
                "ตรวจแล้ว": qty_checked,
                "NG": qty_ng,
                "ยังไม่ตรวจ": qty_pending,
                "สถานะ": status,
                "เวลาบันทึก": datetime.datetime.now(),
            }])
            report_df = pd.concat([report_df, new_row], ignore_index=True)
            report_df.to_excel(REPORT_FILE, index=False)
            st.success(f"✅ บันทึกงานสำเร็จ: {job_id}")

elif mode == "Waiting Judgement":
    st.markdown("## 🔍 งานที่รอตัดสินใจ (Rework / Scrap)")
    waiting_df = report_df[report_df['สถานะ'] == 'รอตัดสินใจ'] if not report_df.empty else pd.DataFrame()
    for _, row in waiting_df.iterrows():
        col1, col2, col3 = st.columns([3, 2, 3])
        with col1:
            st.write(f"**Job ID:** {row['Job ID']} | **รหัส:** {row['รหัสงาน']} | **NG:** {row['NG']}")
        with col2:
            judgement_by = st.selectbox(f"ตัดสินใจโดย ({row['Job ID']})", employee_df['ชื่อ'], key=row['Job ID'])
        with col3:
            colA, colB = st.columns(2)
            if colA.button("🔁 Rework", key="rework_"+row['Job ID']):
                report_df.loc[report_df['Job ID'] == row['Job ID'], 'สถานะ'] = 'Oil Cleaning'
                report_df.loc[report_df['Job ID'] == row['Job ID'], 'Judgement By'] = judgement_by
                report_df.to_excel(REPORT_FILE, index=False)
                st.experimental_rerun()
            if colB.button("🗑️ Scrap", key="scrap_"+row['Job ID']):
                report_df.loc[report_df['Job ID'] == row['Job ID'], 'สถานะ'] = 'Scrap'
                report_df.loc[report_df['Job ID'] == row['Job ID'], 'Judgement By'] = judgement_by
                report_df.to_excel(REPORT_FILE, index=False)
                st.experimental_rerun()

elif mode == "Oil Cleaning":
    st.markdown("## 🧼 งานที่อยู่ในกระบวนการล้าง")
    oil_df = report_df[report_df['สถานะ'] == 'Oil Cleaning'] if not report_df.empty else pd.DataFrame()
    for _, row in oil_df.iterrows():
        col1, col2 = st.columns([6, 2])
        with col1:
            st.write(f"**Job ID:** {row['Job ID']} | **รหัส:** {row['รหัสงาน']} | **จาก:** {row['ผู้ตรวจสอบ']}")
        with col2:
            if st.button("✅ ล้างเสร็จแล้ว", key="lavage_"+row['Job ID']):
                report_df.loc[report_df['Job ID'] == row['Job ID'], 'สถานะ'] = 'Lavage Done'
                report_df.to_excel(REPORT_FILE, index=False)
                st.experimental_rerun()

# ====== แสดง WIP และดาวน์โหลดรายงาน ======
st.markdown("## 📊 สถานะงาน (WIP)")
if not report_df.empty:
    wip_df = report_df[~report_df['สถานะ'].isin(['Scrap', 'Lavage Done'])]
    st.dataframe(wip_df)

    excel_bytes = BytesIO()
    report_df.to_excel(excel_bytes, index=False)
    st.download_button("📥 ดาวน์โหลดรายงาน Excel", data=excel_bytes.getvalue(), file_name="sorting_report_updated.xlsx")
else:
    st.info("ยังไม่มีข้อมูลในระบบ")
