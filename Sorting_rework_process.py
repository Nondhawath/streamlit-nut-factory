# ส่งโค้ดหลักของ Sorting_rework_process.py ที่อัปเดตล่าสุดและพร้อมใช้งาน
from datetime import datetime
import pandas as pd
import streamlit as st
import os
import io
from PIL import Image

# กำหนด path สำหรับจัดเก็บไฟล์
DATA_DIR = "data"
IMAGE_FOLDER = os.path.join(DATA_DIR, "images")
REPORT_PATH = os.path.join(DATA_DIR, "report.xlsx")
EMP_PATH = os.path.join(DATA_DIR, "employee_master.xlsx")
PART_PATH = os.path.join(DATA_DIR, "part_code_master.xlsx")

os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# ฟังก์ชันโหลดและบันทึก Master
def load_master_data():
    emp_df = pd.read_excel(EMP_PATH) if os.path.exists(EMP_PATH) else pd.DataFrame()
    part_df = pd.read_excel(PART_PATH) if os.path.exists(PART_PATH) else pd.DataFrame()
    return emp_df, part_df

def save_master_file(uploaded_file, path):
    df = pd.read_excel(uploaded_file)
    df.to_excel(path, index=False)

# โหลด Master
emp_df, part_df = load_master_data()

# โหลด Report
if os.path.exists(REPORT_PATH):
    report_df = pd.read_excel(REPORT_PATH)
else:
    report_df = pd.DataFrame(columns=["วันที่", "Job ID", "ชื่อพนักงาน", "รหัสงาน", "จำนวน NG", "จำนวนยังไม่ตรวจ",
                                      "จำนวนทั้งหมด", "สถานะ", "เวลา Scrap/Rework", "เวลา Lavage", "รูปภาพ"])

# สร้าง Job ID อัตโนมัติ
def generate_job_id():
    now = datetime.now()
    prefix = now.strftime("%y%m")
    existing = report_df[report_df['Job ID'].astype(str).str.startswith(prefix)]
    last_seq = max([int(str(jid)[-4:]) for jid in existing['Job ID'] if str(jid)[-4:].isdigit()], default=0)
    return f"{prefix}{last_seq + 1:04d}"

# UI
st.set_page_config(page_title="Sorting Process", layout="wide")
st.title("🔧 ระบบบันทึกข้อมูล Sorting Process โรงงานน๊อต")

menu = st.sidebar.selectbox("📌 เลือกโหมด", ["📥 Sorting MC", "🧾 Waiting Judgement", "💧 Oil Cleaning", "📊 รายงาน", "🛠 Upload Master"])

if menu == "📥 Sorting MC":
    st.subheader("📥 กรอกข้อมูล Sorting")
    with st.form("sorting_form"):
        job_id = generate_job_id()
        st.markdown(f"**🆔 Job ID:** `{job_id}`")

        employee = st.selectbox("👷‍♂️ เลือกชื่อพนักงาน", emp_df['ชื่อพนักงาน'].unique() if not emp_df.empty else [])
        part_code = st.selectbox("🔩 เลือกรหัสงาน", part_df['รหัสงาน'].unique() if not part_df.empty else [])
        qty_ng = st.number_input("❌ จำนวน NG", min_value=0)
        qty_pending = st.number_input("⏳ จำนวนที่ยังไม่ตรวจ", min_value=0)
        total = qty_ng + qty_pending
        image = st.file_uploader("📸 อัปโหลดรูปภาพ", type=["png", "jpg", "jpeg"])
        submitted = st.form_submit_button("✅ บันทึกข้อมูล")
        
        if submitted:
            image_path = ""
            if image:
                image_path = os.path.join(IMAGE_FOLDER, f"{job_id}.jpg")
                with open(image_path, "wb") as f:
                    f.write(image.read())
            new_row = {
                "วันที่": datetime.now().date(),
                "Job ID": job_id,
                "ชื่อพนักงาน": employee,
                "รหัสงาน": part_code,
                "จำนวน NG": qty_ng,
                "จำนวนยังไม่ตรวจ": qty_pending,
                "จำนวนทั้งหมด": total,
                "สถานะ": "Sorting MC",
                "เวลา Scrap/Rework": "",
                "เวลา Lavage": "",
                "รูปภาพ": image_path
            }
            report_df = pd.concat([report_df, pd.DataFrame([new_row])], ignore_index=True)
            report_df.to_excel(REPORT_PATH, index=False)
            st.success("✅ บันทึกข้อมูลเรียบร้อยแล้ว")

elif menu == "🧾 Waiting Judgement":
    password = st.text_input("🔐 ใส่รหัสเพื่อเข้าสู่โหมด Judgement", type="password")
    if password == "Admin1":
        st.subheader("🔍 รอตัดสินใจ: Rework หรือ Scrap")
        pending_jobs = report_df[report_df["สถานะ"] == "Sorting MC"]
        for idx, row in pending_jobs.iterrows():
            col1, col2, col3 = st.columns([2, 2, 2])
            with col1:
                st.markdown(f"🆔 **{row['Job ID']}** - รหัส: {row['รหัสงาน']}")
                st.markdown(f"❌ NG: {row['จำนวน NG']} / ⏳ ยังไม่ตรวจ: {row['จำนวนยังไม่ตรวจ']}")
                if row['รูปภาพ'] and os.path.exists(row['รูปภาพ']):
                    st.image(row['รูปภาพ'], width=200)
            with col2:
                if st.button("♻️ Rework", key=f"rework_{row['Job ID']}"):
                    report_df.at[idx, "สถานะ"] = "Rework"
                    report_df.at[idx, "เวลา Scrap/Rework"] = datetime.now()
                    report_df.to_excel(REPORT_PATH, index=False)
                    st.experimental_rerun()
            with col3:
                if st.button("🗑 Scrap", key=f"scrap_{row['Job ID']}"):
                    report_df.at[idx, "สถานะ"] = "Scrap"
                    report_df.at[idx, "เวลา Scrap/Rework"] = datetime.now()
                    report_df.to_excel(REPORT_PATH, index=False)
                    st.experimental_rerun()
    else:
        st.warning("🔒 กรุณาใส่รหัสผ่านให้ถูกต้อง")

elif menu == "💧 Oil Cleaning":
    st.subheader("💧 งานรอเข้ากระบวนการล้าง")
    jobs = report_df[report_df["สถานะ"] == "Rework"]
    for idx, row in jobs.iterrows():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"🆔 {row['Job ID']} - {row['รหัสงาน']} ({row['ชื่อพนักงาน']})")
        with col2:
            if st.button("✅ ล้างเสร็จแล้ว", key=f"done_{row['Job ID']}"):
                report_df.at[idx, "สถานะ"] = "Lavage"
                report_df.at[idx, "เวลา Lavage"] = datetime.now()
                report_df.to_excel(REPORT_PATH, index=False)
                st.experimental_rerun()

elif menu == "📊 รายงาน":
    st.subheader("📊 สรุปและรายงานงานทั้งหมด")
    view = st.selectbox("เลือกช่วงเวลา", ["ทั้งหมด", "รายวัน", "รายสัปดาห์", "รายเดือน", "รายปี"])
    now = datetime.now()
    df = report_df.copy()

    if view == "รายวัน":
        df = df[df["วันที่"] == now.date()]
    elif view == "รายสัปดาห์":
        df = df[df["วันที่"] >= now - pd.Timedelta(days=7)]
    elif view == "รายเดือน":
        df = df[df["วันที่"].apply(lambda d: d.month == now.month and d.year == now.year)]
    elif view == "รายปี":
        df = df[df["วันที่"].apply(lambda d: d.year == now.year)]

    st.dataframe(df)

    scrap_summary = df[df["สถานะ"] == "Scrap"].groupby("รหัสงาน")["จำนวนทั้งหมด"].sum().reset_index()
    st.markdown("📌 **สรุปงาน Scrap แยกตามรหัสงาน**")
    st.dataframe(scrap_summary)

elif menu == "🛠 Upload Master":
    password = st.text_input("🔐 ใส่รหัส Sup เพื่ออัปโหลด Master", type="password")
    if password == "Sup":
        st.subheader("🛠 อัปโหลด Master Data")
        emp_upload = st.file_uploader("👥 อัปโหลดรายชื่อพนักงาน", type="xlsx", key="emp")
        part_upload = st.file_uploader("🧾 อัปโหลดรหัสงาน", type="xlsx", key="part")
        if st.button("📤 อัปโหลด"):
            if emp_upload:
                save_master_file(emp_upload, EMP_PATH)
            if part_upload:
                save_master_file(part_upload, PART_PATH)
            st.success("✅ อัปโหลดและบันทึก Master สำเร็จแล้ว")
            st.experimental_rerun()
