# 📦 Import Library
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# ⏰ Timezone
def now_th():
    return datetime.utcnow() + timedelta(hours=7)

# 🔐 Google Sheet Auth
SCOPE = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
service_account_info = st.secrets["gcp_service_account"]  # ดึงข้อมูลจาก secrets.toml
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
client = gspread.authorize(creds)

# 📗 Sheets
sheet_id = "1lYyHPN7Gdz628lw5s1JVkhNqnS5oHd5oSavUSgL_8cU"  # เปลี่ยนเป็น ID ของ Google Sheet ที่คุณใช้
try:
    sheet = client.open_by_key(sheet_id)
    worksheet = sheet.worksheet("Data")  # เลือกชีทที่ชื่อว่า Data
    part_code_sheet = sheet.worksheet("part_code_master")  # เลือกชีทที่ชื่อว่า part_code_master
except gspread.exceptions.APIError as e:
    st.error(f"⚠️ Error accessing Google Sheets: {e}")
    st.stop()

# 🔁 Load Master Data
def load_master_data():
    try:
        # Part Data (รหัสงาน)
        part_master = part_code_sheet.col_values(1)[1:]  # อ่านคอลัมน์รหัสงานจากชีท part_code_master
        return part_master
    except Exception as e:
        st.error(f"⚠️ Error loading master data: {e}")
        return []

part_master = load_master_data()

# 📦 บันทึกน้ำหนักชิ้นงาน
st.set_page_config(page_title="บันทึกน้ำหนักชิ้นงาน", layout="wide")
st.title(f"📦 บันทึกน้ำหนักชิ้นงาน")

st.subheader("📦 กรอกข้อมูลน้ำหนักชิ้นงาน")

with st.form("weight_form"):
    part_code = st.selectbox("🔩 รหัสงาน", part_master)
    weight = st.number_input("⚖️ น้ำหนักชิ้นงาน (n = 32)", min_value=0.0, step=0.1)
    timestamp = now_th().strftime("%Y-%m-%d %H:%M:%S")

    # กำหนดปุ่มให้กดได้เฉพาะเมื่อกรอกครบ
    submit_button = st.form_submit_button("✅ บันทึกข้อมูล")

    if submit_button and weight > 0:
        # ค้นหาบรรทัดที่มีรหัสงานเดียวกัน
        data = worksheet.get_all_records()
        job_row = None
        for idx, row in enumerate(data):
            if row["รหัสงาน"] == part_code:
                job_row = idx + 2  # +2 เนื่องจากแถวข้อมูลเริ่มต้นที่แถวที่ 2 (แถวแรกเป็นหัวตาราง)
                break

        if job_row:
            # หา first empty column ที่ n1 ถึง n30
            for col_idx in range(1, 31):  # n1 ถึง n30
                if not worksheet.cell(job_row, col_idx + 1).value:  # ถ้าค่าในเซลล์ว่าง
                    worksheet.update_cell(job_row, col_idx + 1, weight)
                    st.success(f"✅ บันทึกน้ำหนักชิ้นงาน {weight} kg เรียบร้อยแล้วใน n{col_idx}")
                    break
            else:
                st.warning("⚠️ ไม่มีที่ว่างในคอลัมน์ n1 ถึง n30 สำหรับการบันทึกข้อมูล")
        else:
            st.warning("⚠️ ไม่พบรหัสงานในระบบ")
