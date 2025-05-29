import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import os

st.set_page_config(page_title="Sorting Process App", layout="wide")

DATA_FILE = "sorting_report_updated.xlsx"
EMPLOYEE_FILE = "รายชื่อพนักงานแผนก Final Inspection.xlsx"
PART_FILE = "Master list SCS part name.xlsx"

# ----- Load or Initialize Master Data -----
@st.cache_data

def load_master_data():
    if os.path.exists(EMPLOYEE_FILE):
        df_emp = pd.read_excel(EMPLOYEE_FILE)
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

# ----- Upload Updated Master Files -----
st.sidebar.header("📤 อัปโหลดไฟล์ Master")
emp_upload = st.sidebar.file_uploader("อัปโหลดรายชื่อพนักงาน (Excel)", type="xlsx")
part_upload = st.sidebar.file_uploader("อัปโหลดรหัสงาน (Excel)", type="xlsx")

if emp_upload:
    df_emp = pd.read_excel(emp_upload)
    df_emp.to_excel(EMPLOYEE_FILE, index=False)
    st.sidebar.success("อัปเดตรายชื่อพนักงานแล้ว")
    st.experimental_rerun()

if part_upload:
    df_part = pd.read_excel(part_upload)
    df_part.to_excel(PART_FILE, index=False)
    st.sidebar.success("อัปเดตรหัสงานแล้ว")
    st.experimental_rerun()

# ----- Load Report Data -----
def load_report():
    if os.path.exists(DATA_FILE):
        return pd.read_excel(DATA_FILE)
    else:
        return pd.DataFrame(columns=[
            "Job ID", "Timestamp", "Employee", "Part Code", "Total Checked", "NG", "Un-Tested",
            "Status", "Current Process", "Rework Time", "Leader", "Oil Cleaning Time", "Sender", "Judged By"])

report_df = load_report()

# ----- Generate Next Job ID -----
def generate_job_id():
    now = datetime.now()
    prefix = now.strftime("%y%m")
    existing = report_df[report_df['Job ID'].str.startswith(prefix, na=False)]
    next_num = len(existing) + 1
    return f"{prefix}{next_num:04d}"

# ----- Mode Selection -----
st.title("🛠️ ระบบจัดการงาน Sorting Process")
mode = st.selectbox("เลือกโหมดการทำงาน", ["Sorting MC", "Waiting Judgement", "Oil Cleaning", "WIP Overview"])

if mode == "Sorting MC":
    st.subheader("📋 กรอกข้อมูลจากแผนก Sorting")
    with st.form("sorting_form"):
        col1, col2 = st.columns(2)
        with col1:
            employee = st.selectbox("ชื่อพนักงาน", employees)
            part_code = st.text_input("รหัสงาน", "")
            part_code_dropdown = st.selectbox("เลือกรหัสงานจากรายการ", ["ไม่เลือก"] + part_codes)
            if part_code_dropdown != "ไม่เลือก":
                part_code = part_code_dropdown
            total_checked = st.number_input("จำนวนที่ตรวจ", min_value=0)
            ng = st.number_input("จำนวน NG", min_value=0)
            untested = st.number_input("จำนวนที่ตรวจไม่ทัน (Un-Tested)", min_value=0)
        with col2:
            status = st.selectbox("สถานะเริ่มต้น", ["งาน NG จากเครื่อง"])

        submitted = st.form_submit_button("✅ บันทึกข้อมูล")
        if submitted:
            new_job_id = generate_job_id()
            new_data = pd.DataFrame([{
                "Job ID": new_job_id,
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Employee": employee,
                "Part Code": part_code,
                "Total Checked": total_checked,
                "NG": ng,
                "Un-Tested": untested,
                "Status": status,
                "Current Process": "Waiting Judgement",
                "Rework Time": "", "Leader": "", "Oil Cleaning Time": "", "Sender": "", "Judged By": ""
            }])
            report_df = pd.concat([report_df, new_data], ignore_index=True)
            report_df.to_excel(DATA_FILE, index=False)
            st.success(f"✅ บันทึกแล้ว (Job ID: {new_job_id})")

elif mode == "Waiting Judgement":
    st.subheader("🔎 รอตัดสินใจ Scrap หรือ Rework")
    wj_df = report_df[report_df["Current Process"] == "Waiting Judgement"]
    for _, row in wj_df.iterrows():
        st.markdown(f"**Job ID:** {row['Job ID']} | รหัสงาน: {row['Part Code']} | NG: {row['NG']}")
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"🗑️ Scrap - {row['Job ID']}"):
                report_df.loc[report_df['Job ID'] == row['Job ID'], 'Status'] = "Scrap"
                report_df.loc[report_df['Job ID'] == row['Job ID'], 'Current Process'] = "Done"
                report_df.to_excel(DATA_FILE, index=False)
                st.success(f"บันทึก Scrap สำหรับ Job ID {row['Job ID']}")
                st.experimental_rerun()
        with col2:
            if st.button(f"🔁 Rework - {row['Job ID']}"):
                report_df.loc[report_df['Job ID'] == row['Job ID'], 'Status'] = "Rework"
                report_df.loc[report_df['Job ID'] == row['Job ID'], 'Current Process'] = "Oil Cleaning"
                report_df.loc[report_df['Job ID'] == row['Job ID'], 'Rework Time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                leader = st.selectbox(f"เลือก Leader สำหรับ {row['Job ID']}", leaders, key=row['Job ID'])
                report_df.loc[report_df['Job ID'] == row['Job ID'], 'Leader'] = leader
                report_df.to_excel(DATA_FILE, index=False)
                st.success(f"บันทึก Rework และส่งไป Oil Cleaning สำหรับ Job ID {row['Job ID']}")
                st.experimental_rerun()

elif mode == "Oil Cleaning":
    st.subheader("🧼 งานที่อยู่ในขั้นตอน Oil Cleaning")
    oc_df = report_df[report_df["Current Process"] == "Oil Cleaning"]
    for _, row in oc_df.iterrows():
        st.markdown(f"**Job ID:** {row['Job ID']} | รหัสงาน: {row['Part Code']}")
        if st.button(f"✅ ล้างเสร็จแล้ว - {row['Job ID']}"):
            report_df.loc[report_df['Job ID'] == row['Job ID'], 'Oil Cleaning Time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            report_df.loc[report_df['Job ID'] == row['Job ID'], 'Current Process'] = "Sorting"
            report_df.to_excel(DATA_FILE, index=False)
            st.success(f"บันทึกสถานะล้างเสร็จแล้ว สำหรับ Job ID {row['Job ID']}")
            st.experimental_rerun()

elif mode == "WIP Overview":
    st.subheader("📦 รายงานงานค้าง (WIP)")
    wip_df = report_df[report_df["Current Process"].isin(["Waiting Judgement", "Oil Cleaning"])]
    st.dataframe(wip_df, use_container_width=True)

# ----- Pie Chart Summary -----
st.subheader("📊 สรุปสัดส่วนสถานะงาน")
status_counts = report_df["Status"].value_counts()
fig, ax = plt.subplots()
ax.pie(status_counts, labels=status_counts.index, autopct='%1.1f%%', startangle=90)
ax.axis('equal')
st.pyplot(fig)

# ----- Export Button -----
st.download_button("📥 ดาวน์โหลดรายงานทั้งหมด", data=report_df.to_excel(index=False), file_name="sorting_report_updated.xlsx")
