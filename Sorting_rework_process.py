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
except Exception as e:
    st.error(f"ไม่สามารถสร้างโฟลเดอร์จัดเก็บข้อมูล: {e}")

# 📄 โหลดไฟล์ Master

def load_master_data():
    try:
        emp_df = pd.read_excel(EMP_PATH)
    except:
        emp_df = pd.DataFrame(columns=["ชื่อพนักงาน"])

    try:
        part_df = pd.read_excel(PART_PATH)
    except:
        part_df = pd.DataFrame(columns=["รหัสงาน"])

    return emp_df, part_df

# 💾 บันทึกไฟล์ Master

def save_master_file(uploaded_file, path):
    try:
        df = pd.read_excel(uploaded_file)
        df.to_excel(path, index=False)
    except Exception as e:
        st.error(f"ไม่สามารถบันทึกไฟล์: {e}")

# 🔁 โหลด Master และ Report
emp_df, part_df = load_master_data()
if os.path.exists(REPORT_PATH):
    report_df = pd.read_excel(REPORT_PATH)
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
    last_seq = max([int(str(jid)[-4:]) for jid in existing['Job ID'] if str(jid)[-4:].isdigit()], default=0)
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
                except PermissionError:
                    st.error("⚠️ ไม่สามารถบันทึกรูปภาพได้: ไม่มีสิทธิ์ในการเขียนไฟล์")
                    image_path = ""
                except Exception as e:
                    st.error(f"⚠️ เกิดข้อผิดพลาดในการบันทึกรูปภาพ: {e}")
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
            report_df.to_excel(REPORT_PATH, index=False)
            st.success("✅ บันทึกข้อมูลเรียบร้อยแล้ว")
