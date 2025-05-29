import streamlit as st
import pandas as pd
import os
import datetime
from io import BytesIO

st.set_page_config(page_title="Sorting Process Tracker", layout="wide")
st.title("🛠️ ระบบติดตามกระบวนการ Sorting & Rework")

# กำหนด path ถาวรสำหรับไฟล์พนักงานและรหัสงาน
emp_path = "/mnt/data/employee_list.xlsx"
part_path = "/mnt/data/part_codes.xlsx"
report_path = "/mnt/data/sorting_report.xlsx"

# ===== Upload ไฟล์พนักงานและรหัสงาน (ครั้งแรกหรือต้องการอัปเดต) =====
with st.expander("📥 อัปโหลดรายชื่อพนักงานและรหัสงาน"):
    uploaded_emp = st.file_uploader("อัปโหลดรายชื่อพนักงาน (Excel)", type=["xlsx"], key="emp")
    if uploaded_emp:
        with open(emp_path, "wb") as f:
            f.write(uploaded_emp.getbuffer())
        st.success("✅ อัปโหลดรายชื่อพนักงานเรียบร้อยแล้ว")

    uploaded_part = st.file_uploader("อัปโหลดรหัสงาน (Excel)", type=["xlsx"], key="part")
    if uploaded_part:
        with open(part_path, "wb") as f:
            f.write(uploaded_part.getbuffer())
        st.success("✅ อัปโหลดรหัสงานเรียบร้อยแล้ว")

# ===== โหลดข้อมูลพนักงานและรหัสงาน =====
if os.path.exists(emp_path):
    df_emp = pd.read_excel(emp_path)
    employees = df_emp.iloc[:, 0].dropna().unique().tolist()
else:
    employees = []

if os.path.exists(part_path):
    df_part = pd.read_excel(part_path)
    part_codes = df_part.iloc[:, 0].dropna().unique().tolist()
else:
    part_codes = []

# ===== โหลดหรือสร้าง Report =====
if os.path.exists(report_path):
    report_df = pd.read_excel(report_path)
else:
    report_df = pd.DataFrame(columns=[
        "Job ID", "วันที่", "เวลา", "รหัสงาน", "จำนวนตรวจ", "จำนวน NG", "จำนวนยังไม่ตรวจ",
        "ผู้บันทึก", "สถานะ", "ผู้ตัดสิน", "เวลาตัดสิน", "เวลาล้างเสร็จ"])

# ===== Function สร้าง Job ID =====
def generate_job_id():
    now = datetime.datetime.now()
    prefix = now.strftime("%y%m")
    if "Job ID" in report_df.columns:
        existing = report_df[report_df["Job ID"].astype(str).str.startswith(prefix)]
    else:
        existing = pd.DataFrame()
    next_num = len(existing) + 1
    return f"{prefix}{next_num:04d}"

# ===== แบบฟอร์มบันทึก Sorting MC =====
st.subheader("📝 บันทึกข้อมูลกระบวนการ Sorting MC")
with st.form("sorting_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        part_code = st.selectbox("เลือกรหัสงาน", part_codes)
    with col2:
        total_checked = st.number_input("จำนวนที่ตรวจ", min_value=0, step=1)
    with col3:
        total_ng = st.number_input("จำนวน NG", min_value=0, max_value=total_checked, step=1)

    total_unchecked = total_checked - total_ng
    st.markdown(f"**จำนวนยังไม่ตรวจ:** {total_unchecked}")

    operator = st.selectbox("ชื่อผู้บันทึก", employees)

    submitted = st.form_submit_button("✅ บันทึกงาน")
    if submitted:
        now = datetime.datetime.now()
        job_id = generate_job_id()
        new_row = {
            "Job ID": job_id,
            "วันที่": now.date(),
            "เวลา": now.strftime("%H:%M:%S"),
            "รหัสงาน": part_code,
            "จำนวนตรวจ": total_checked,
            "จำนวน NG": total_ng,
            "จำนวนยังไม่ตรวจ": total_unchecked,
            "ผู้บันทึก": operator,
            "สถานะ": "Waiting Judgement",
            "ผู้ตัดสิน": "",
            "เวลาตัดสิน": "",
            "เวลาล้างเสร็จ": ""
        }
        report_df = pd.concat([report_df, pd.DataFrame([new_row])], ignore_index=True)
        report_df.to_excel(report_path, index=False)
        st.success(f"✅ บันทึกข้อมูลเรียบร้อยแล้ว | Job ID: {job_id}")

# ===== โหมด Waiting Judgement =====
st.subheader("🔍 โหมด Waiting Judgement")
waiting_df = report_df[report_df["สถานะ"] == "Waiting Judgement"]
for i, row in waiting_df.iterrows():
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    with col1:
        st.write(f"Job ID: {row['Job ID']}")
    with col2:
        st.write(f"รหัสงาน: {row['รหัสงาน']}")
    with col3:
        st.write(f"จำนวน: {row['จำนวนตรวจ']}")
    with col4:
        judge_name = st.selectbox(f"ผู้ตัดสิน {row['Job ID']}", employees, key=f"judge_{i}")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("📛 Scrap", key=f"scrap_{i}"):
                report_df.at[i, "สถานะ"] = "Scrap"
                report_df.at[i, "ผู้ตัดสิน"] = judge_name
                report_df.at[i, "เวลาตัดสิน"] = datetime.datetime.now().strftime("%H:%M:%S")
                report_df.to_excel(report_path, index=False)
                st.experimental_rerun()
        with col_btn2:
            if st.button("🔁 Rework", key=f"rework_{i}"):
                report_df.at[i, "สถานะ"] = "Oil Cleaning"
                report_df.at[i, "ผู้ตัดสิน"] = judge_name
                report_df.at[i, "เวลาตัดสิน"] = datetime.datetime.now().strftime("%H:%M:%S")
                report_df.to_excel(report_path, index=False)
                st.experimental_rerun()

# ===== โหมด Oil Cleaning =====
st.subheader("🧼 โหมด Oil Cleaning")
oil_df = report_df[report_df["สถานะ"] == "Oil Cleaning"]
for i, row in oil_df.iterrows():
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        st.write(f"Job ID: {row['Job ID']}")
    with col2:
        st.write(f"รหัสงาน: {row['รหัสงาน']}")
    with col3:
        if st.button("✅ ล้างเสร็จแล้ว", key=f"cleaned_{i}"):
            report_df.at[i, "สถานะ"] = "Lavage Completed"
            report_df.at[i, "เวลาล้างเสร็จ"] = datetime.datetime.now().strftime("%H:%M:%S")
            report_df.to_excel(report_path, index=False)
            st.experimental_rerun()

# ===== WIP =====
st.subheader("📊 สถานะงานที่ยังไม่เสร็จ (WIP)")
wip_df = report_df[~report_df["สถานะ"].isin(["Scrap", "Lavage Completed"])]
st.dataframe(wip_df, use_container_width=True)

# ===== ดาวน์โหลดรายงาน =====
st.subheader("📁 ดาวน์โหลดรายงานทั้งหมด")
output = BytesIO()
report_df.to_excel(output, index=False)
st.download_button(
    label="📥 ดาวน์โหลดรายงาน Excel",
    data=output.getvalue(),
    file_name="sorting_report_updated.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
