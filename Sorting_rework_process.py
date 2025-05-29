from datetime import datetime
import pandas as pd
import streamlit as st
import os
from PIL import Image

# 📁 กำหนด path สำหรับจัดเก็บไฟล์
DATA_DIR = "data"
IMAGE_FOLDER = os.path.join(DATA_DIR, "images")
REPORT_PATH = os.path.join(DATA_DIR, "report.xlsx")
EMP_PATH = os.path.join(DATA_DIR, "employee_master.xlsx")
PART_PATH = os.path.join(DATA_DIR, "part_code_master.xlsx")

# 🛡 สร้างโฟลเดอร์หากยังไม่มี
try:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(IMAGE_FOLDER, exist_ok=True)
except PermissionError:
    st.error("❌ ไม่มีสิทธิ์ในการสร้างโฟลเดอร์ กรุณาตรวจสอบสิทธิ์การเข้าถึง")
except Exception as e:
    st.error(f"❌ ไม่สามารถสร้างโฟลเดอร์จัดเก็บข้อมูล: {e}")

# 📄 โหลดไฟล์ Master
def load_master_data():
    try:
        emp_df = pd.read_excel(EMP_PATH, engine="openpyxl")
    except:
        emp_df = pd.DataFrame(columns=["ชื่อพนักงาน"])
    
    try:
        part_df = pd.read_excel(PART_PATH, engine="openpyxl")
    except:
        part_df = pd.DataFrame(columns=["รหัสงาน"])

    return emp_df, part_df

# 💾 บันทึกไฟล์ Master
def save_master_file(uploaded_file, path):
    try:
        df = pd.read_excel(uploaded_file, engine="openpyxl")
        df.to_excel(path, index=False, engine="openpyxl")
    except Exception as e:
        st.error(f"❌ ไม่สามารถบันทึกไฟล์: {e}")

# 🔁 โหลด Master และ Report
emp_df, part_df = load_master_data()
if os.path.exists(REPORT_PATH):
    try:
        report_df = pd.read_excel(REPORT_PATH, engine="openpyxl")
    except:
        report_df = pd.DataFrame(columns=[
            "วันที่", "Job ID", "ชื่อพนักงาน", "รหัสงาน", "จำนวน NG", "จำนวนยังไม่ตรวจ",
            "จำนวนทั้งหมด", "สถานะ", "เวลา Scrap/Rework", "เวลา Lavage", "รูปภาพ"
        ])
else:
    report_df = pd.DataFrame(columns=[
        "วันที่", "Job ID", "ชื่อพนักงาน", "รหัสงาน", "จำนวน NG", "จำนวนยังไม่ตรวจ",
        "จำนวนทั้งหมด", "สถานะ", "เวลา Scrap/Rework", "เวลา Lavage", "รูปภาพ"
    ])

# 🆔 สร้าง Job ID อัตโนมัติ
def generate_job_id():
    now = datetime.now()
    prefix = now.strftime("%y%m")
    existing = report_df[report_df['Job ID'].astype(str).str.startswith(prefix)]
    try:
        last_seq = max([int(str(jid)[-4:]) for jid in existing['Job ID'] if str(jid)[-4:].isdigit()], default=0)
    except:
        last_seq = 0
    return f"{prefix}{last_seq + 1:04d}"

# 🖥 เริ่มต้น UI
st.set_page_config(page_title="Sorting Process", layout="wide")
st.title("🔧 ระบบบันทึกข้อมูล Sorting Process โรงงานน๊อต")

menu = st.sidebar.selectbox("📌 เลือกโหมด", [
    "📥 Sorting MC", "🧾 Waiting Judgement", "💧 Oil Cleaning", "📊 รายงาน", "🛠 Upload Master"
])

# 📥 โหมด 1: Sorting MC
if menu == "📥 Sorting MC":
    st.subheader("📥 กรอกข้อมูล Sorting")
    with st.form("sorting_form"):
        job_id = generate_job_id()
        st.markdown(f"**🆔 Job ID:** `{job_id}`")

        emp_list = emp_df['ชื่อพนักงาน'].dropna().unique() if 'ชื่อพนักงาน' in emp_df.columns else []
        part_list = part_df['รหัสงาน'].dropna().unique() if 'รหัสงาน' in part_df.columns else []

        employee = st.selectbox("👷‍♂️ เลือกชื่อพนักงาน", emp_list)
        part_code = st.selectbox("🔩 เลือกรหัสงาน", part_list)
        qty_ng = st.number_input("❌ จำนวน NG", min_value=0)
        qty_pending = st.number_input("⏳ จำนวนที่ยังไม่ตรวจ", min_value=0)
        total = qty_ng + qty_pending
        image = st.file_uploader("📸 อัปโหลดรูปภาพ", type=["png", "jpg", "jpeg"])

        submitted = st.form_submit_button("✅ บันทึกข้อมูล")
        if submitted:
            image_path = ""
            if image:
                try:
                    image_path = os.path.join(IMAGE_FOLDER, f"{job_id}.jpg")
                    with open(image_path, "wb") as f:
                        f.write(image.read())
                except Exception as e:
                    st.error(f"❌ ไม่สามารถบันทึกรูปภาพ: {e}")
                    image_path = ""

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
            report_df.to_excel(REPORT_PATH, index=False, engine="openpyxl")
            st.success("✅ บันทึกข้อมูลเรียบร้อยแล้ว")

# 🧾 โหมด 2: Judgement
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
                    report_df.to_excel(REPORT_PATH, index=False, engine="openpyxl")
                    st.rerun()
            with col3:
                if st.button("🗑 Scrap", key=f"scrap_{row['Job ID']}"):
                    report_df.at[idx, "สถานะ"] = "Scrap"
                    report_df.at[idx, "เวลา Scrap/Rework"] = datetime.now()
                    report_df.to_excel(REPORT_PATH, index=False, engine="openpyxl")
                    st.rerun()
    else:
        st.warning("🔒 กรุณาใส่รหัสผ่านให้ถูกต้อง")

# 💧 โหมด 3: Oil Cleaning
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
                report_df.to_excel(REPORT_PATH, index=False, engine="openpyxl")
                st.rerun()

# 📊 โหมด 4: รายงาน
elif menu == "📊 รายงาน":
    st.subheader("📊 สรุปและรายงานงานทั้งหมด")
    view = st.selectbox("เลือกช่วงเวลา", ["ทั้งหมด", "รายวัน", "รายสัปดาห์", "รายเดือน", "รายปี"])
    now = datetime.now()
    df = report_df.copy()

    if view == "รายวัน":
        df = df[df["วันที่"] == now.date()]
    elif view == "รายสัปดาห์":
        df = df[df["วันที่"] >= now.date() - pd.Timedelta(days=7)]
    elif view == "รายเดือน":
        df = df[df["วันที่"].apply(lambda d: pd.to_datetime(d).month == now.month and pd.to_datetime(d).year == now.year)]
    elif view == "รายปี":
        df = df[df["วันที่"].apply(lambda d: pd.to_datetime(d).year == now.year)]

    st.dataframe(df)

    scrap_summary = df[df["สถานะ"] == "Scrap"].groupby("รหัสงาน")["จำนวนทั้งหมด"].sum().reset_index()
    st.markdown("📌 **สรุปงาน Scrap แยกตามรหัสงาน**")
    st.dataframe(scrap_summary)

# 🛠 โหมด 5: Upload Master
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
            st.rerun()
