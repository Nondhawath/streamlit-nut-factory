import streamlit as st
import pandas as pd
import datetime
import os
from io import BytesIO

st.set_page_config(page_title="📋 ระบบติดตามงานโรงงานน๊อต", layout="wide")

REPORT_PATH = "/mnt/data/sorting_report.xlsx"
EMP_PATH = "/mnt/data/employee_list.xlsx"
PART_PATH = "/mnt/data/part_code_list.xlsx"
IMAGE_FOLDER = "uploaded_images"
if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

# โหลดข้อมูลรายชื่อพนักงานและรหัสงาน (ถ้ามีไฟล์)
if os.path.exists(EMP_PATH):
    df_emp = pd.read_excel(EMP_PATH)
else:
    df_emp = pd.DataFrame(columns=["ชื่อ"])

if os.path.exists(PART_PATH):
    df_part = pd.read_excel(PART_PATH)
else:
    df_part = pd.DataFrame(columns=["รหัส"])

# โหลดข้อมูลรายงาน
if os.path.exists(REPORT_PATH):
    report_df = pd.read_excel(REPORT_PATH)
else:
    report_df = pd.DataFrame(columns=["วันที่", "ชื่อ", "รหัสงาน", "จำนวน NG", "จำนวนที่ยังไม่ตรวจ", "จำนวนทั้งหมด", "สถานะ", "Job ID", "รูปภาพ"])

# ฟังก์ชันสำหรับรัน Job ID อัตโนมัติ
def generate_job_id():
    today = datetime.date.today()
    prefix = today.strftime("%y%m")
    existing = report_df[report_df['Job ID'].astype(str).str.startswith(prefix)] if not report_df.empty else pd.DataFrame()
    if existing.empty:
        return prefix + "0001"
    last_seq = max([int(str(jid)[-4:]) for jid in existing['Job ID']])
    return prefix + str(last_seq + 1).zfill(4)

# แสดงหัวเรื่อง
st.title("📦 ระบบติดตามงาน Sorting Process")
mode = st.sidebar.selectbox("🔧 เลือกโหมด", ["🔍 Sorting MC", "🕐 Waiting Judgement", "🧼 Oil Cleaning", "📁 อัปโหลดไฟล์ Master", "📊 รายงานสรุป"])

# โหมด: อัปโหลดไฟล์รายชื่อและรหัสงาน
if mode == "📁 อัปโหลดไฟล์ Master":
    password = st.text_input("🔐 กรุณาใส่รหัสผ่าน (Sup)", type="password")
    if password == "Sup":
        st.subheader("📌 อัปโหลดรายชื่อพนักงาน")
        emp_upload = st.file_uploader("Upload รายชื่อพนักงาน", type=["xlsx"])
        if emp_upload:
            df_emp = pd.read_excel(emp_upload)
            df_emp.to_excel(EMP_PATH, index=False)
            st.success("✅ อัปเดตรายชื่อพนักงานเรียบร้อย")

        st.subheader("📌 อัปโหลดรหัสงาน")
        part_upload = st.file_uploader("Upload รหัสงาน", type=["xlsx"])
        if part_upload:
            df_part = pd.read_excel(part_upload)
            df_part.to_excel(PART_PATH, index=False)
            st.success("✅ อัปเดตรหัสงานเรียบร้อย")
    else:
        st.warning("🚫 ใส่รหัสผ่านให้ถูกต้อง")

# โหมด: Sorting MC
elif mode == "🔍 Sorting MC":
    with st.form("sorting_form"):
        st.subheader("📥 บันทึกข้อมูลการตรวจสอบ (Sorting)")
        name = st.selectbox("👤 ชื่อผู้ตรวจสอบ", df_emp['ชื่อ'].dropna().unique())
        part_code = st.selectbox("🧾 รหัสงาน", df_part['รหัส'].dropna().unique())
        qty_ng = st.number_input("❌ จำนวน NG", min_value=0)
        qty_pending = st.number_input("⏳ จำนวนที่ยังไม่ตรวจ", min_value=0)
        image = st.file_uploader("📸 อัปโหลดรูปภาพ", type=["png", "jpg", "jpeg"])

        if st.form_submit_button("📤 บันทึกข้อมูล"):
            job_id = generate_job_id()
            total_qty = qty_ng + qty_pending
            image_path = ""
            if image:
                image_path = f"{IMAGE_FOLDER}/{job_id}.png"
                with open(image_path, "wb") as f:
                    f.write(image.getbuffer())

            new_data = pd.DataFrame([{
                "วันที่": datetime.datetime.now(),
                "ชื่อ": name,
                "รหัสงาน": part_code,
                "จำนวน NG": qty_ng,
                "จำนวนที่ยังไม่ตรวจ": qty_pending,
                "จำนวนทั้งหมด": total_qty,
                "สถานะ": "Waiting Judgement",
                "Job ID": job_id,
                "รูปภาพ": image_path
            }])
            report_df = pd.concat([report_df, new_data], ignore_index=True)
            report_df.to_excel(REPORT_PATH, index=False)
            st.success(f"✅ บันทึกข้อมูลเรียบร้อย: Job ID = {job_id}")

# โหมด: Judgement
elif mode == "🕐 Waiting Judgement":
    password = st.text_input("🔐 ใส่รหัสผ่านเพื่อเข้าสู่ Judgement", type="password")
    if password == "Admin1":
        st.subheader("🕵️‍♂️ Judgement")
        judgement_name = st.selectbox("👤 ผู้ตัดสิน", df_emp['ชื่อ'].dropna().unique())
        waiting_jobs = report_df[report_df["สถานะ"] == "Waiting Judgement"]
        for idx, row in waiting_jobs.iterrows():
            st.markdown(f"**🧾 รหัสงาน:** {row['รหัสงาน']} | **📅 วันที่:** {row['วันที่']} | **Job ID:** {row['Job ID']} | ❌ NG: {row['จำนวน NG']} | ⏳ ยังไม่ตรวจ: {row['จำนวนที่ยังไม่ตรวจ']}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"💀 Scrap - {row['Job ID']}"):
                    report_df.at[idx, "สถานะ"] = "Scrap"
                    report_df.to_excel(REPORT_PATH, index=False)
                    st.success("📛 บันทึกสถานะ Scrap แล้ว")
            with col2:
                if st.button(f"🔁 Rework - {row['Job ID']}"):
                    report_df.at[idx, "สถานะ"] = "Oil Cleaning"
                    report_df.to_excel(REPORT_PATH, index=False)
                    st.success("🔃 ส่งต่อไปล้างน้ำมันแล้ว")

# โหมด: Oil Cleaning
elif mode == "🧼 Oil Cleaning":
    st.subheader("🧴 Oil Cleaning Process")
    oil_jobs = report_df[report_df["สถานะ"] == "Oil Cleaning"]
    for idx, row in oil_jobs.iterrows():
        st.markdown(f"🧾 รหัสงาน: {row['รหัสงาน']} | 📅 วันที่: {row['วันที่']} | Job ID: {row['Job ID']}")
        if st.button(f"✅ ล้างเสร็จแล้ว - {row['Job ID']}"):
            report_df.at[idx, "สถานะ"] = "Sorting MC"
            report_df.to_excel(REPORT_PATH, index=False)
            st.success("✅ งานกลับไป Sorting MC แล้ว")

# โหมด: รายงาน
elif mode == "📊 รายงานสรุป":
    st.subheader("📊 สรุปสถานะงานและยอดรวม")

    period = st.selectbox("📅 เลือกช่วงเวลา", ["รายวัน", "รายสัปดาห์", "รายเดือน", "รายปี"])
    today = datetime.date.today()
    if period == "รายวัน":
        filtered_df = report_df[pd.to_datetime(report_df['วันที่']).dt.date == today]
    elif period == "รายสัปดาห์":
        start = today - datetime.timedelta(days=today.weekday())
        end = start + datetime.timedelta(days=6)
        filtered_df = report_df[(pd.to_datetime(report_df['วันที่']).dt.date >= start) & (pd.to_datetime(report_df['วันที่']).dt.date <= end)]
    elif period == "รายเดือน":
        filtered_df = report_df[pd.to_datetime(report_df['วันที่']).dt.month == today.month]
    else:
        filtered_df = report_df[pd.to_datetime(report_df['วันที่']).dt.year == today.year]

    st.dataframe(filtered_df)

    st.markdown("### ♻️ WIP ของแต่ละกระบวนการ")
    for status in ["Waiting Judgement", "Oil Cleaning", "Sorting MC"]:
        total = report_df[report_df["สถานะ"] == status]["จำนวนทั้งหมด"].sum()
        st.metric(label=status, value=int(total))

    st.markdown("### 💀 ยอดรวม Scrap (รวมรหัสงานเดียวกัน)")
    scrap_summary = report_df[report_df["สถานะ"] == "Scrap"].groupby("รหัสงาน")["จำนวนทั้งหมด"].sum().reset_index()
    st.dataframe(scrap_summary)

    # ดาวน์โหลดรายงาน
    to_download = BytesIO()
    report_df.to_excel(to_download, index=False)
    st.download_button("📥 ดาวน์โหลดรายงาน Excel", data=to_download.getvalue(), file_name="sorting_report.xlsx")
