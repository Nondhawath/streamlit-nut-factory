import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import os
from io import BytesIO

st.set_page_config(page_title="Sorting Process App", layout="wide")

DATA_FILE = "sorting_report_updated.xlsx"
EMP_FILE = "รายชื่อพนักงานแผนก Final Inspection.xlsx"
PART_FILE = "Master list SCS part name.xlsx"

# ----- Load or Initialize Master Data -----
@st.cache_data
def load_master_data():
    if os.path.exists(EMP_FILE):
        df_emp = pd.read_excel(EMP_FILE)
    else:
        df_emp = pd.DataFrame(columns=["ชื่อ", "ตำแหน่ง"])

    if os.path.exists(PART_FILE):
        df_part = pd.read_excel(PART_FILE)
    else:
        df_part = pd.DataFrame(columns=["รหัส"])

    return df_emp, df_part

df_emp, df_part = load_master_data()
employees = df_emp['ชื่อ'].dropna().unique().tolist()
leaders = df_emp[df_emp['ตำแหน่ง'].str.contains("Leader", na=False)]['ชื่อ'].unique().tolist()
part_codes = df_part['รหัส'].dropna().unique().tolist()

# ----- Upload Master Update -----
st.sidebar.header("📤 อัปโหลดรายชื่อพนักงาน / รหัสงาน")
emp_upload = st.sidebar.file_uploader("อัปโหลดรายชื่อพนักงาน (Excel)", type="xlsx", key="emp")
if emp_upload:
    with open(EMP_FILE, "wb") as f:
        f.write(emp_upload.read())
    st.sidebar.success("✅ อัปเดตรายชื่อพนักงานเรียบร้อยแล้ว")

part_upload = st.sidebar.file_uploader("อัปโหลดรหัสงาน (Excel)", type="xlsx", key="part")
if part_upload:
    with open(PART_FILE, "wb") as f:
        f.write(part_upload.read())
    st.sidebar.success("✅ อัปเดตรหัสงานเรียบร้อยแล้ว")

# ----- Load Existing Report or Create New -----
def load_report():
    if os.path.exists(DATA_FILE):
        return pd.read_excel(DATA_FILE)
    else:
        return pd.DataFrame(columns=[
            "Job ID", "Timestamp", "Employee", "Part Code", "Total Checked", "NG", "Un-Tested",
            "Status", "Current Process", "Leader", "Oil Cleaning Time", "Judgement Time"])

report_df = load_report()

# ----- Job ID Generator -----
def generate_job_id():
    now = datetime.now()
    prefix = now.strftime("%y%m")
    existing = report_df[report_df['Job ID'].str.startswith(prefix)] if not report_df.empty else pd.DataFrame()
    next_id = str(len(existing) + 1).zfill(4)
    return prefix + next_id

# ----- Mode Selection -----
mode = st.sidebar.selectbox("เลือกโหมด", ["Sorting MC", "Waiting Judgement", "Oil Cleaning"])

# ----- Sorting MC Mode -----
if mode == "Sorting MC":
    st.header("🛠️ Sorting MC - กรอกผลการตรวจสอบ")
    with st.form("sorting_form"):
        col1, col2 = st.columns(2)
        with col1:
            employee = st.selectbox("ชื่อพนักงาน", employees)
            part_code = st.text_input("รหัสงาน (พิมพ์หรือเลือก)", "")
            part_dropdown = st.selectbox("เลือกรหัสงานจากรายการ", ["ไม่เลือก"] + part_codes)
            if part_dropdown != "ไม่เลือก":
                part_code = part_dropdown
            total_checked = st.number_input("จำนวนที่ตรวจ", min_value=0)
            ng = st.number_input("จำนวน NG", min_value=0)
            untested = st.number_input("จำนวนที่ตรวจไม่ทัน", min_value=0)
        with col2:
            status = "งาน NG จากเครื่อง"
            job_id = generate_job_id()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        submitted = st.form_submit_button("✅ บันทึกข้อมูล")
        if submitted:
            new_data = pd.DataFrame([{
                "Job ID": job_id,
                "Timestamp": now,
                "Employee": employee,
                "Part Code": part_code,
                "Total Checked": total_checked,
                "NG": ng,
                "Un-Tested": untested,
                "Status": status,
                "Current Process": "Waiting Judgement",
                "Leader": "",
                "Oil Cleaning Time": "",
                "Judgement Time": ""
            }])
            report_df = pd.concat([report_df, new_data], ignore_index=True)
            report_df.to_excel(DATA_FILE, index=False)
            st.success(f"✅ บันทึกข้อมูล Job ID: {job_id} เรียบร้อยแล้ว")

# ----- Waiting Judgement Mode -----
elif mode == "Waiting Judgement":
    st.header("🧠 Waiting Judgement - ตัดสินใจ Scrap หรือ Rework")
    pending_df = report_df[report_df['Current Process'] == "Waiting Judgement"]
    if pending_df.empty:
        st.info("📭 ไม่มีงานค้างรอตัดสินใจ")
    else:
        for _, row in pending_df.iterrows():
            with st.expander(f"🔍 Job ID: {row['Job ID']} | Part Code: {row['Part Code']} | NG: {row['NG']}"):
                leader = st.selectbox("เลือก Leader ผู้ตัดสินใจ", leaders, key=f"leader_{row['Job ID']}")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("❌ Scrap", key=f"scrap_{row['Job ID']}"):
                        report_df.loc[report_df['Job ID'] == row['Job ID'], ['Status', 'Current Process', 'Leader', 'Judgement Time']] = \
                            ["Scrap", "Finished", leader, datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                        report_df.to_excel(DATA_FILE, index=False)
                        st.success("📦 งานถูกบันทึกเป็น Scrap")
                        st.experimental_rerun()
                with col2:
                    if st.button("🔁 Rework", key=f"rework_{row['Job ID']}"):
                        report_df.loc[report_df['Job ID'] == row['Job ID'], ['Status', 'Current Process', 'Leader', 'Judgement Time']] = \
                            ["Rework", "Oil Cleaning", leader, datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                        report_df.to_excel(DATA_FILE, index=False)
                        st.success("♻️ งานส่งต่อไป Oil Cleaning")
                        st.experimental_rerun()

# ----- Oil Cleaning Mode -----
elif mode == "Oil Cleaning":
    st.header("🧼 Oil Cleaning - บันทึกงานล้างเสร็จ")
    cleaning_df = report_df[report_df['Current Process'] == "Oil Cleaning"]
    if cleaning_df.empty:
        st.info("📭 ไม่มีงานในขั้นตอน Oil Cleaning")
    else:
        for _, row in cleaning_df.iterrows():
            with st.expander(f"🧴 Job ID: {row['Job ID']} | Part Code: {row['Part Code']}"):
                if st.button("✅ ล้างเสร็จแล้ว", key=f"done_{row['Job ID']}"):
                    report_df.loc[report_df['Job ID'] == row['Job ID'], ['Status', 'Current Process', 'Oil Cleaning Time']] = \
                        ["Washed", "Finished", datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                    report_df.to_excel(DATA_FILE, index=False)
                    st.success("💧 งานถูกบันทึกว่าล้างเสร็จแล้ว")
                    st.experimental_rerun()

# ----- WIP Dashboard -----
st.header("📦 WIP ของแต่ละกระบวนการ")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("🕹️ Waiting Judgement", report_df[report_df['Current Process'] == "Waiting Judgement"].shape[0])
with col2:
    st.metric("🔁 Oil Cleaning", report_df[report_df['Current Process'] == "Oil Cleaning"].shape[0])
with col3:
    st.metric("✅ งานเสร็จทั้งหมด", report_df[report_df['Current Process'] == "Finished"].shape[0])

# ----- Export Section -----
st.subheader("📥 ดาวน์โหลดรายงาน")
excel_buffer = BytesIO()
report_df.to_excel(excel_buffer, index=False)
st.download_button(
    label="📥 ดาวน์โหลดรายงาน Excel",
    data=excel_buffer.getvalue(),
    file_name="sorting_report_updated.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
