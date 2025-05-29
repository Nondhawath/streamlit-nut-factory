import streamlit as st
import pandas as pd
import os
from datetime import datetime
from io import BytesIO

# ---------- เตรียมโฟลเดอร์สำหรับเก็บไฟล์ ----------
os.makedirs("data", exist_ok=True)
emp_path = "data/employee.xlsx"
part_path = "data/part_codes.xlsx"
report_path = "data/sorting_report.xlsx"

# ---------- โหลดไฟล์ Master ถ้ามี หรือใช้ไฟล์อัปโหลด ----------
uploaded_emp = st.file_uploader("📄 อัปโหลดไฟล์รายชื่อพนักงาน", type=["xlsx"])
if uploaded_emp is not None:
    with open(emp_path, "wb") as f:
        f.write(uploaded_emp.getbuffer())

uploaded_part = st.file_uploader("📄 อัปโหลดไฟล์รหัสงาน", type=["xlsx"])
if uploaded_part is not None:
    with open(part_path, "wb") as f:
        f.write(uploaded_part.getbuffer())

# ---------- โหลดข้อมูลพนักงานและรหัสงาน ----------
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

# ---------- โหลดรายงานหรือสร้างใหม่ ----------
if os.path.exists(report_path):
    report_df = pd.read_excel(report_path)
else:
    report_df = pd.DataFrame(columns=[
        "วันที่", "เวลา", "Job ID", "ชื่อพนักงาน", "รหัสงาน",
        "จำนวนที่ตรวจ", "จำนวน NG", "จำนวนที่ยังไม่ตรวจ",
        "สถานะ", "Judgement โดย"
    ])

# ---------- ฟังก์ชันสร้าง Job ID ----------
def generate_job_id():
    now = datetime.now()
    prefix = now.strftime("%y%m")
    if not report_df.empty and report_df['Job ID'].astype(str).str.startswith(prefix).any():
        existing = report_df[report_df['Job ID'].astype(str).str.startswith(prefix)]
        last_seq = max([int(jid[-4:]) for jid in existing['Job ID']])
        next_seq = last_seq + 1
    else:
        next_seq = 1
    return f"{prefix}{next_seq:04d}"

# ---------- หน้า UI หลัก ----------
st.title("📋 ระบบบันทึกงานโรงงานน๊อต - Sorting Process")
mode = st.selectbox("เลือกโหมดการทำงาน", ["Sorting MC", "Waiting Judgement", "Oil Cleaning"])

# ---------- Sorting MC ----------
if mode == "Sorting MC":
    st.header("🧾 บันทึกข้อมูลงานใหม่")
    with st.form("sorting_form"):
        emp = st.selectbox("👤 ชื่อพนักงาน", employees)
        part = st.selectbox("🔢 รหัสงาน", part_codes)
        qty_checked = st.number_input("✅ จำนวนที่ตรวจ", 0)
        qty_ng = st.number_input("❌ จำนวน NG", 0)
        qty_pending = st.number_input("⏳ จำนวนที่ยังไม่ตรวจ", 0)
        status = st.selectbox("📌 สถานะ", ["Waiting Judgement"])
        submit = st.form_submit_button("📤 บันทึกข้อมูล")

        if submit:
            now = datetime.now()
            job_id = generate_job_id()
            new_row = pd.DataFrame([{ 
                "วันที่": now.date(),
                "เวลา": now.strftime("%H:%M:%S"),
                "Job ID": job_id,
                "ชื่อพนักงาน": emp,
                "รหัสงาน": part,
                "จำนวนที่ตรวจ": qty_checked,
                "จำนวน NG": qty_ng,
                "จำนวนที่ยังไม่ตรวจ": qty_pending,
                "สถานะ": status,
                "Judgement โดย": ""
            }])
            report_df = pd.concat([report_df, new_row], ignore_index=True)
            report_df.to_excel(report_path, index=False)
            st.success(f"✅ บันทึกเรียบร้อยแล้ว: Job ID {job_id}")

# ---------- Waiting Judgement ----------
elif mode == "Waiting Judgement":
    st.header("🧪 ตรวจสอบและตัดสินใจงานที่รอ Judgement")
    waiting_df = report_df[report_df['สถานะ'] == "Waiting Judgement"]
    if waiting_df.empty:
        st.info("🎉 ไม่มีงานที่รอ Judgement")
    else:
        for idx, row in waiting_df.iterrows():
            st.markdown(f"**🆔 Job ID:** {row['Job ID']} | 🔢 รหัสงาน: {row['รหัสงาน']} | ✅ ตรวจแล้ว: {row['จำนวนที่ตรวจ']} | ❌ NG: {row['จำนวน NG']}")
            col1, col2, col3 = st.columns([1,1,2])
            with col1:
                if st.button(f"🟥 Scrap {row['Job ID']}"):
                    report_df.at[idx, 'สถานะ'] = 'Scrap'
                    report_df.at[idx, 'Judgement โดย'] = st.selectbox("👤 ชื่อผู้ตัดสิน", employees, key=f"judge_{idx}")
                    report_df.to_excel(report_path, index=False)
                    st.experimental_rerun()
            with col2:
                if st.button(f"🟩 Rework {row['Job ID']}"):
                    report_df.at[idx, 'สถานะ'] = 'Oil Cleaning'
                    report_df.at[idx, 'Judgement โดย'] = st.selectbox("👤 ชื่อผู้ตัดสิน", employees, key=f"judge2_{idx}")
                    report_df.to_excel(report_path, index=False)
                    st.experimental_rerun()

# ---------- Oil Cleaning ----------
elif mode == "Oil Cleaning":
    st.header("🧼 งานที่อยู่ในขั้นตอน Oil Cleaning")
    oil_df = report_df[report_df['สถานะ'] == "Oil Cleaning"]
    if oil_df.empty:
        st.info("✨ ไม่มีงานในขั้นตอน Oil Cleaning")
    else:
        for idx, row in oil_df.iterrows():
            st.markdown(f"**🆔 Job ID:** {row['Job ID']} | 🔢 รหัสงาน: {row['รหัสงาน']} | 👤 โดย: {row['Judgement โดย']}")
            if st.button(f"✅ ล้างเสร็จแล้ว {row['Job ID']}"):
                report_df.at[idx, 'สถานะ'] = 'Cleaned'
                report_df.to_excel(report_path, index=False)
                st.experimental_rerun()

# ---------- WIP ----------
st.header("📦 งานที่ยังไม่เสร็จ (WIP)")
wip_df = report_df[~report_df['สถานะ'].isin(['Scrap', 'Cleaned'])]
st.dataframe(wip_df)

# ---------- ดาวน์โหลดรายงาน ----------
with BytesIO() as b:
    report_df.to_excel(b, index=False)
    st.download_button("📥 ดาวน์โหลดรายงาน Excel", data=b.getvalue(), file_name="sorting_report.xlsx")
