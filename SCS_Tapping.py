# 📦 Import Library
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import requests
import json

# ✅ Telegram Settings
TELEGRAM_TOKEN = "7229880312:AAEkXptoNBQ4_5lONUhVqlzoSoeOs88-sxI"  # เปลี่ยนเป็น token ใหม่
TELEGRAM_CHAT_ID = "-4818928611"  # เปลี่ยนเป็น chat id ใหม่

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
service_account_info = st.secrets["GOOGLE_SHEETS_CREDENTIALS"]  # ใช้ข้อมูลจาก secrets.toml
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
client = gspread.authorize(creds)

# 📗 Sheets
sheet_id = "11zriIOYlG7FIz2PhWp0wxVdXA_5RFuxXhX67-UtrUd0"  # ID ของ Google Sheets ที่ต้องการใช้
try:
    sheet = client.open_by_key(sheet_id)
    worksheet = sheet.worksheet("Data")  # ชื่อชีทที่ต้องการ
    st.success("✅ เชื่อมต่อ Google Sheets สำเร็จ!")
except gspread.exceptions.APIError as e:
    st.error(f"⚠️ Error accessing Google Sheets: {e}")
    st.stop()

# 🔁 Load Master Data
def load_master_data():
    try:
        # Employee Data
        emp_data = sheet.worksheet("employee_master").get_all_values()  # ใช้ get_all_values()
        emp_master = [row[0] for row in emp_data[1:]]  # สมมติว่า "ชื่อพนักงาน" อยู่ในคอลัมน์แรก
        emp_password_map = {row[0]: str(row[1]).strip() for row in emp_data[1:]}  # "รหัส" อยู่ในคอลัมน์ที่ 2
        emp_level_map = {row[0]: str(row[2]).strip() for row in emp_data[1:]}  # "ระดับ" อยู่ในคอลัมน์ที่ 3
        
        # Part Data
        part_master = sheet.worksheet("part_code_master").col_values(1)[1:]

        # Reason Data
        reason_sheet = sheet.worksheet("Reason NG")
        reason_list = reason_sheet.col_values(reason_sheet.find("Reason").col)[1:]

        # Machines Data
        machines_data = sheet.worksheet("machines").get_all_values()  # ใช้ get_all_values()
        machines_list = [row[0] for row in machines_data[1:]]  # สมมติว่า "machines_name" อยู่ในคอลัมน์แรก

        return emp_master, emp_password_map, emp_level_map, part_master, reason_list, machines_list

    except Exception as e:
        st.error(f"⚠️ Error loading master data: {e}")
        return [], {}, {}, [], [], []

emp_master, emp_password_map, emp_level_map, part_master, reason_list, machines_list = load_master_data()

# 🔐 Login Process
if "logged_in_user" not in st.session_state:
    with st.form("login_form"):
        st.subheader("🔐 เข้าสู่ระบบ")
        username = st.selectbox("👤 Username", emp_master)
        password = st.text_input("🔑 Password", type="password")
        submitted = st.form_submit_button("🔓 Login")
        if submitted:
            if emp_password_map.get(username) == password:
                st.session_state.logged_in_user = username
                st.session_state.user_level = emp_level_map.get(username, "")
                st.rerun()
            else:
                st.error("❌ รหัสผ่านไม่ถูกต้อง")
    st.stop()

user = st.session_state.logged_in_user
user_level = st.session_state.user_level
st.set_page_config(page_title="Taping Process", layout="wide")
st.title(f"🔧 Taping Process - สวัสดี {user} ({user_level})")

# 🔐 สิทธิ์เข้าใช้งาน
allowed_modes = []
if user_level == "S1":
    allowed_modes = ["📥 Taping MC", "🧾 Waiting Judgement", "📊 รายงาน"]
elif user_level == "T1":
    allowed_modes = ["🧾 Waiting Judgement"]
elif user_level == "T7":
    allowed_modes = ["📥 Taping MC"]

menu = st.sidebar.selectbox("📌 โหมด", allowed_modes)

# 📥 Taping MC
def check_duplicate(part_code, reason_ng):
    records = worksheet.get_all_values()  # ใช้ get_all_values() แทน get_all_records()
    for record in records:
        if record[3] == part_code and record[9] == reason_ng:
            return True
    return False

if menu == "📥 Taping MC":
    st.subheader("📥 กรอกข้อมูล Taping")
    with st.form("taping_form"):
        part_code = st.selectbox("🔩 รหัสงาน", part_master)
        machine = st.selectbox("🛠 เครื่อง", machines_list)
        lot = st.text_input("📦 Lot Number")
        checked = st.number_input("🔍 จำนวนผลิตทั้งหมด", 0)
        ng = st.number_input("❌ NG", 0)
        reason_ng = st.selectbox("📋 หัวข้องานเสีย", reason_list)
        
        # ตรวจสอบข้อมูลซ้ำ
        if check_duplicate(part_code, reason_ng):
            st.warning("⚠️ ข้อมูลนี้ถูกบันทึกแล้ว กรุณาตรวจสอบอีกครั้ง")
        else:
            total = ng  # ลบฟังก์ชัน "ยังไม่ตรวจ" ออก
            submitted = st.form_submit_button("✅ บันทึกข้อมูล")
            if submitted:
                row = [
                    now_th().strftime("%Y-%m-%d %H:%M:%S"), user, part_code,
                    machine, lot, checked, ng, total,  # ใช้เฉพาะ NG และตรวจ
                    "Taping MC", "", "", "", reason_ng
                ]
                try:
                    worksheet.append_row(row)
                    st.success("✅ บันทึกเรียบร้อย")
                    send_telegram_message(
                        f"📥 <b>New Taping</b>\n"
                        f"👷‍♂️ พนักงาน: {user}\n"
                        f"🔩 รหัสงาน: {part_code}\n"
                        f"🛠 เครื่อง: {machine}\n"
                        f"📦 Lot: {lot}\n"
                        f"❌ NG: {ng}\n"
                        f"📋 หัวข้องานเสีย: {reason_ng}"
                    )
                except Exception as e:
                    st.error(f"⚠️ Error appending data to sheet: {e}")
