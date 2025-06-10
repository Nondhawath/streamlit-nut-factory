from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import requests
import json

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
sheet_id = "1GM-es30UBsqFCxBVQbBxht6IntIkL6troc5c2PWD3JA"  # ID ของ Google Sheets ที่ต้องการใช้
try:
    sheet = client.open_by_key(sheet_id)
    worksheet = sheet.worksheet("Data")
    st.success("✅ เชื่อมต่อ Google Sheets สำเร็จ!")
except gspread.exceptions.APIError as e:
    st.error(f"⚠️ Error accessing Google Sheets: {e}")
    st.stop()

# ตรวจสอบว่าแถวแรกมีคอลัมน์หรือไม่ ถ้าไม่มีให้สร้างคอลัมน์ใหม่
def check_and_create_columns():
    first_row = worksheet.row_values(1)  # อ่านแถวแรก
    if not first_row:  # ถ้าแถวแรกไม่มีข้อมูล
        columns = ["วันที่", "พนักงาน", "รหัสงาน", "เครื่อง", "Lot Number", 
                   "จำนวนผลิตทั้งหมด", "จำนวน NG", "หัวข้องานเสีย", "สถานะ"]
        worksheet.append_row(columns)  # เพิ่มแถวคอลัมน์ใหม่
        st.success("✅ สร้างชื่อคอลัมน์ใน Google Sheets เรียบร้อยแล้ว!")

check_and_create_columns()  # ตรวจสอบและสร้างคอลัมน์

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

# 🆔 สร้าง Job ID ปลอดภัย
def generate_job_id():
    try:
        records = worksheet.get_all_values()  # ใช้ get_all_values() แทน get_all_records()
        prefix = now_th().strftime("%y%m")
        filtered = [
            r for r in records
            if isinstance(r[1], str) and r[1].startswith(prefix) and r[1][-4:].isdigit()  # ใช้ index ที่ถูกต้อง
        ]
        last_seq = max([int(r[1][-4:]) for r in filtered], default=0)
        return f"{prefix}{last_seq + 1:04d}"

    except gspread.exceptions.GSpreadException as e:
        st.error(f"⚠️ Gspread Error: {e}")
        return None

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
def check_duplicate(job_id, part_code, reason_ng):
    """ ตรวจสอบข้อมูลซ้ำใน Google Sheets โดยเช็คจาก Job ID, รหัสงาน และหัวข้องานเสีย """
    records = worksheet.get_all_values()  # ใช้ get_all_values() แทน get_all_records()
    for record in records:
        if len(record) > 8 and record[1] == job_id and record[3] == part_code and record[8] == reason_ng:
            return True  # พบข้อมูลซ้ำ
    return False  # ไม่มีข้อมูลซ้ำ

if menu == "📥 Taping MC":
    st.subheader("📥 กรอกข้อมูล Taping")
    with st.form("taping_form"):
        job_id = generate_job_id()  # สร้าง Job ID ใหม่
        if job_id is None:
            st.error("⚠️ ไม่สามารถสร้าง Job ID ได้")
            st.stop()
        
        part_code = st.selectbox("🔩 รหัสงาน", part_master)
        machine = st.selectbox("🛠 เครื่อง", machines_list)
        lot = st.text_input("📦 Lot Number")
        checked = st.number_input("🔍 จำนวนผลิตทั้งหมด", 0)
        ng = st.number_input("❌ NG", 0)
        reason_ng = st.selectbox("📋 หัวข้องานเสีย", reason_list)
        
        # ตรวจสอบข้อมูลซ้ำก่อนบันทึก
        if check_duplicate(job_id, part_code, reason_ng):
            st.warning("⚠️ ข้อมูลนี้ถูกบันทึกแล้ว กรุณาตรวจสอบอีกครั้ง")
        else:
            total = ng  # ใช้เฉพาะ NG และตรวจ
            submitted = st.form_submit_button("✅ บันทึกข้อมูล")
            if submitted:
                row = [
                    now_th().strftime("%Y-%m-%d %H:%M:%S"), job_id, user, part_code,
                    machine, lot, checked, ng, total,  # ใช้เฉพาะ NG และตรวจ
                    "Taping MC", "", "", "", reason_ng
                ]
                try:
                    worksheet.append_row(row)  # บันทึกข้อมูลในแถวใหม่
                    st.success("✅ บันทึกเรียบร้อย")
                    send_telegram_message(
                        f"📥 <b>New Taping</b>\n"
                        f"🆔 Job ID: <code>{job_id}</code>\n"
                        f"👷‍♂️ พนักงาน: {user}\n"
                        f"🔩 รหัสงาน: {part_code}\n"
                        f"🛠 เครื่อง: {machine}\n"
                        f"📦 Lot: {lot}\n"
                        f"❌ NG: {ng}\n"
                        f"📋 หัวข้องานเสีย: {reason_ng}"
                    )
                except Exception as e:
                    st.error(f"⚠️ Error appending data to sheet: {e}")

# 🧾 Waiting Judgement
elif menu == "🧾 Waiting Judgement":
    st.subheader("🔍 รอตัดสินใจ Scrap")
    try:
        df = pd.DataFrame(worksheet.get_all_values())  # ใช้ get_all_values() แทน get_all_records()
        if df.empty:
            st.warning("⚠️ ไม่มีข้อมูลใน Google Sheets")
            st.stop()
    except gspread.exceptions.GSpreadException as e:
        st.error(f"⚠️ Gspread Error: {e}")
        st.stop()

    df["วันที่"] = pd.to_datetime(df["วันที่"], errors="coerce")
    df = df[df["สถานะ"] == "Taping MC"]
    df = df.sort_values(by="วันที่", ascending=False)

    for idx, row in df.iterrows():
        timestamp = row.get("วันที่", "")
        st.markdown(
            f"🆔 <b>{row['Job ID']}</b> | รหัส: {row['รหัสงาน']} | NG: {row['จำนวน NG']} | 📋 หัวข้องานเสีย: {row.get('หัวข้องานเสีย', '-')} | ⏰ เวลา: {timestamp}",
            unsafe_allow_html=True
        )

        col1 = st.columns(1)
        if col1[0].button(f"🗑 Scrap - {row['Job ID']}", key=f"scrap_{idx}"):
            worksheet.update_cell(idx + 2, 11, "Scrap")
            worksheet.update_cell(idx + 2, 12, now_th().strftime("%Y-%m-%d %H:%M:%S"))
            worksheet.update_cell(idx + 2, 14, user)
            send_telegram_message(
                f"🗑 <b>Scrap</b>\n"
                f"🆔 Job ID: <code>{row['Job ID']}</code>\n"
                f"🔩 รหัสงาน: {row['รหัสงาน']}\n"
                f"📋 หัวข้องานเสีย: {row['หัวข้องานเสีย']}\n"
                f"❌ จำนวนทั้งหมด: {row['จำนวนทั้งหมด']}\n"
                f"👷‍♂️ โดย: {user}"
            )
            st.rerun()

# 📊 รายงาน
elif menu == "📊 รายงาน":
    df = pd.DataFrame(worksheet.get_all_values())  # ใช้ get_all_values() แทน get_all_records()
    df["วันที่"] = pd.to_datetime(df["วันที่"], errors="coerce")
    view = st.selectbox("🗓 ช่วงเวลา", ["ทั้งหมด", "รายวัน", "รายสัปดาห์", "รายเดือน", "รายปี"])
    now = now_th()
    if view == "รายวัน":
        df = df[df["วันที่"].dt.date == now.date()]
    elif view == "รายสัปดาห์":
        df = df[df["วันที่"] >= now - pd.Timedelta(days=7)]
    elif view == "รายเดือน":
        df = df[df["วันที่"].dt.month == now.month]
    elif view == "รายปี":
        df = df[df["วันที่"].dt.year == now.year]
    st.dataframe(df)
    scrap_sum = df[df["สถานะ"] == "Scrap"].groupby("รหัสงาน")["จำนวนทั้งหมด"].sum().reset_index()
    st.markdown("📌 สรุป Scrap แยกรหัสงาน")
    st.dataframe(scrap_sum)
