# 📦 Import Library
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import requests

# ✅ Telegram Settings
TELEGRAM_TOKEN = "7617656983:AAGqI7jQvEtKZw_tD11cQneH57WvYWl9r_s"
TELEGRAM_CHAT_ID = "-4944715716"

def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
        requests.post(url, data=payload)
    except Exception as e:
        st.warning(f"⚠️ Telegram Error: {e}")

# ⏰ Timezone
def now_th():
    return datetime.utcnow() + timedelta(hours=7)

# 🔐 Google Sheet Auth
SCOPE = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
service_account_info = st.secrets["GOOGLE_SHEETS_CREDENTIALS"]  # เป็น dict อยู่แล้ว
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
client = gspread.authorize(creds)

# 📗 Sheets
sheet_id = "1lYyHPN7Gdz628lw5s1JVkhNqnS5oHd5oSavUSgL_8cU"
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

# 🆔 สร้าง Job ID ปลอดภัย
def generate_job_id():
    try:
        records = worksheet.get_all_records()
    except gspread.exceptions.APIError as e:
        st.error(f"⚠️ API Error: {e}")
        return None

    prefix = now_th().strftime("%y%m")
    filtered = [
        r for r in records
        if isinstance(r.get("Job ID"), str) and r["Job ID"].startswith(prefix) and r["Job ID"][-4:].isdigit()
    ]
    last_seq = max([int(r["Job ID"][-4:]) for r in filtered], default=0)
    return f"{prefix}{last_seq + 1:04d}"

# 🔐 Login Process
if "logged_in_user" not in st.session_state:
    with st.form("login_form"):
        st.subheader("🔐 เข้าสู่ระบบ")
        username = st.text_input("👤 Username")
        password = st.text_input("🔑 Password", type="password")
        submitted = st.form_submit_button("🔓 Login")
        if submitted:
            # ตรวจสอบรหัสผ่าน
            if username == "admin" and password == "admin":  # ตัวอย่างการตรวจสอบ
                st.session_state.logged_in_user = username
                st.rerun()
            else:
                st.error("❌ รหัสผ่านไม่ถูกต้อง")
    st.stop()

user = st.session_state.logged_in_user
st.set_page_config(page_title="บันทึกน้ำหนักชิ้นงาน", layout="wide")
st.title(f"📦 บันทึกน้ำหนักชิ้นงาน - สวัสดี {user}")

# 📥 บันทึกน้ำหนักชิ้นงาน
st.subheader("📦 กรอกข้อมูลน้ำหนักชิ้นงาน")

with st.form("weight_form"):
    job_id = generate_job_id()
    if job_id is None:
        st.error("⚠️ ไม่สามารถสร้าง Job ID ได้")
        st.stop()

    st.markdown(f"**🆔 Job ID:** `{job_id}`")
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
                    send_telegram_message(
                        f"📦 <b>New Weight Record</b>\n"
                        f"🆔 Job ID: <code>{job_id}</code>\n"
                        f"👷‍♂️ พนักงาน: {user}\n"
                        f"🔩 รหัสงาน: {part_code}\n"
                        f"⚖️ น้ำหนักชิ้นงาน: {weight} kg\n"
                        f"⏰ เวลาบันทึก: {timestamp}"
                    )
                    break
            else:
                st.warning("⚠️ ไม่มีที่ว่างในคอลัมน์ n1 ถึง n30 สำหรับการบันทึกข้อมูล")
        else:
            st.warning("⚠️ ไม่พบรหัสงานในระบบ")
