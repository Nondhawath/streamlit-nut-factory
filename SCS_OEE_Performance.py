import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
from datetime import datetime, timedelta

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
    part_code = st.selectbox("🔩 รหัสงาน", part_master)  # เลือกรหัสงานจาก part_code_master
    weights = []
    
    # กรอกข้อมูลน้ำหนัก n1 ถึง n32
    for i in range(1, 33):
        # ใช้ number_input เพื่อให้กรอกเป็นจำนวนเต็ม 4 หลัก
        weight = st.number_input(f"⚖️ น้ำหนักชิ้นงาน (n{i})", min_value=0, max_value=9999, step=1, key=f"n{i}")
        weights.append(weight)
    
    timestamp = now_th().strftime("%Y-%m-%d %H:%M:%S")

    # กำหนดปุ่มให้กดได้เฉพาะเมื่อกรอกครบ
    submit_button = st.form_submit_button("✅ บันทึกข้อมูล")

    if submit_button:
        # ค้นหาบรรทัดที่มีรหัสงานเดียวกันในชีท Data
        data = worksheet.get_all_records()
        job_row = None
        for idx, row in enumerate(data):
            if row["รหัสงาน"] == part_code:
                job_row = idx + 2  # +2 เนื่องจากแถวข้อมูลเริ่มต้นที่แถวที่ 2 (แถวแรกเป็นหัวตาราง)
                break

        if job_row:
            # อัปเดตข้อมูลน้ำหนัก n1 ถึง n32 ใน Google Sheets
            for col_idx, weight in enumerate(weights, start=1):
                worksheet.update_cell(job_row, col_idx + 1, weight)  # +1 เนื่องจากคอลัมน์แรกเป็นรหัสงาน
            st.success(f"✅ บันทึกน้ำหนักชิ้นงานเรียบร้อยแล้วใน n1 ถึง n32")
        else:
            # หากไม่พบรหัสงานในระบบ ให้เพิ่มข้อมูลลงในแถวใหม่
            new_row = [part_code] + weights
            worksheet.append_row(new_row)  # เพิ่มข้อมูลในแถวใหม่
            st.success(f"✅ เพิ่มข้อมูลรหัสงานใหม่ {part_code} และบันทึกน้ำหนักเรียบร้อยแล้วใน n1 ถึง n32")
