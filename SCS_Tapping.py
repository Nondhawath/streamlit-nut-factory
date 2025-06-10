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
except gspread.exceptions.APIError as e:
    st.error(f"⚠️ Error accessing Google Sheets: {e}")
    st.stop()

# 🔁 Load Master Data
def load_master_data():
    try:
        # Employee Data
        emp_data = sheet.worksheet("employee_master").get_all_records()
        emp_master = [row["ชื่อพนักงาน"] for row in emp_data]
        emp_password_map = {row["ชื่อพนักงาน"]: str(row["รหัส"]).strip() for row in emp_data}
        emp_level_map = {row["ชื่อพนักงาน"]: str(row["ระดับ"]).strip() for row in emp_data}
        
        # Part Data
        part_master = sheet.worksheet("part_code_master").col_values(1)[1:]

        # Reason Data
        reason_sheet = sheet.worksheet("Reason NG")
        reason_list = reason_sheet.col_values(reason_sheet.find("Reason").col)[1:]

        # Machines Data
        machines_data = sheet.worksheet("machines").get_all_records()
        machines_list = [row["machines_name"] for row in machines_data]

        return emp_master, emp_password_map, emp_level_map, part_master, reason_list, machines_list

    except Exception as e:
        st.error(f"⚠️ Error loading master data: {e}")
        return [], {}, {}, [], [], []

emp_master, emp_password_map, emp_level_map, part_master, reason_list, machines_list = load_master_data()

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
    records = worksheet.get_all_records()
    for record in records:
        if record["Job ID"] == job_id and record["รหัสงาน"] == part_code and record["หัวข้องานเสีย"] == reason_ng:
            return True
    return False

if menu == "📥 Taping MC":
    st.subheader("📥 กรอกข้อมูล Taping")
    with st.form("taping_form"):
        job_id = generate_job_id()
        if job_id is None:
            st.error("⚠️ ไม่สามารถสร้าง Job ID ได้")
            st.stop()
        
        part_code = st.selectbox("🔩 รหัสงาน", part_master)
        machine = st.selectbox("🛠 เครื่อง", machines_list)
        lot = st.text_input("📦 Lot Number")
        checked = st.number_input("🔍 จำนวนตรวจทั้งหมด", 0)
        ng = st.number_input("❌ NG", 0)
        pending = st.number_input("⏳ ยังไม่ตรวจ", 0)
        reason_ng = st.selectbox("📋 หัวข้องานเสีย", reason_list)
        
        # ตรวจสอบข้อมูลซ้ำ
        if check_duplicate(job_id, part_code, reason_ng):
            st.warning("⚠️ ข้อมูลนี้ถูกบันทึกแล้ว กรุณาตรวจสอบอีกครั้ง")
        else:
            total = ng + pending
            submitted = st.form_submit_button("✅ บันทึกข้อมูล")
            if submitted:
                row = [
                    now_th().strftime("%Y-%m-%d %H:%M:%S"), job_id, user, part_code,
                    machine, lot, checked, ng, pending, total,
                    "Taping MC", "", "", "", reason_ng
                ]
                try:
                    worksheet.append_row(row)
                    st.success("✅ บันทึกเรียบร้อย")
                    send_telegram_message(
                        f"📥 <b>New Taping</b>\n"
                        f"🆔 Job ID: <code>{job_id}</code>\n"
                        f"👷‍♂️ พนักงาน: {user}\n"
                        f"🔩 รหัสงาน: {part_code}\n"
                        f"🛠 เครื่อง: {machine}\n"
                        f"📦 Lot: {lot}\n"
                        f"❌ NG: {ng} | ⏳ ยังไม่ตรวจ: {pending}\n"
                        f"📋 หัวข้องานเสีย: {reason_ng}"
                    )
                except Exception as e:
                    st.error(f"⚠️ Error appending data to sheet: {e}")

# 🧾 Waiting Judgement
elif menu == "🧾 Waiting Judgement":
    st.subheader("🔍 รอตัดสินใจ Recheck / Scrap")
    df = pd.DataFrame(worksheet.get_all_records())

    if "สถานะ" not in df.columns or "วันที่" not in df.columns:
        st.warning("⚠️ ไม่มีข้อมูลสถานะหรือวันที่ใน Google Sheet")
        st.stop()

    df = df[df["สถานะ"] == "Taping MC"]

    df["วันที่"] = pd.to_datetime(df["วันที่"], errors="coerce")
    df = df.sort_values(by="วันที่", ascending=False)

    for idx, row in df.iterrows():
        timestamp = row.get("วันที่", "")
        st.markdown(
            f"🆔 <b>{row['Job ID']}</b> | รหัส: {row['รหัสงาน']} | NG: {row['จำนวน NG']} | ยังไม่ตรวจ: {row['จำนวนยังไม่ตรวจ']} "
            f"| 📋 หัวข้องานเสีย: {row.get('หัวข้องานเสีย', '-')} | ⏰ เวลา: {timestamp}",
            unsafe_allow_html=True
        )

        col1, col2 = st.columns(2)
        if col1.button(f"♻️ Recheck - {row['Job ID']}", key=f"recheck_{row['Job ID']}_{idx}"):
            worksheet.update_cell(idx + 2, 11, "Recheck")
            worksheet.update_cell(idx + 2, 12, now_th().strftime("%Y-%m-%d %H:%M:%S"))
            worksheet.update_cell(idx + 2, 14, user)
            send_telegram_message(
                f"♻️ <b>Recheck</b>\n"
                f"🆔 Job ID: <code>{row['Job ID']}</code>\n"
                f"🔩 รหัสงาน: {row['รหัสงาน']}\n"
                f"📋 หัวข้องานเสีย: {row['หัวข้องานเสีย']}\n"
                f"♻️ จำนวนทั้งหมด: {row['จำนวนทั้งหมด']}\n"
                f"👷‍♂️ โดย: {user}"
            )
            st.rerun()

        if col2.button(f"🗑 Scrap - {row['Job ID']}", key=f"scrap_{idx}"):
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
    df = pd.DataFrame(worksheet.get_all_records())
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
