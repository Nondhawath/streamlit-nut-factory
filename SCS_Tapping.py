# 📦 Import Library
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import requests
import json

# ✅ Telegram Settings
TELEGRAM_TOKEN = "7229880312:AAEkXptoNBQ4_5lONUhVqlzoSoeOs88-sxI"
TELEGRAM_CHAT_ID = "-4818928611"

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
sheet_id = "11zriIOYlG7FIz2PhWp0wxVdXA_5RFuxXhX67-UtrUd0"  # ลิงค์ใหม่
try:
    sheet = client.open_by_key(sheet_id)
    worksheet = sheet.worksheet("Tapping_report")  # เปลี่ยนชื่อชีทใหม่
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
st.set_page_config(page_title="Tapping Process", layout="wide")
st.title(f"🔧 Tapping Process - สวัสดี {user} ({user_level})")

# 🔐 สิทธิ์เข้าใช้งาน
allowed_modes = []
if user_level == "S1":
    allowed_modes = ["📥 Tapping MC", "📊 รายงาน", "🛠 Upload Master"]
elif user_level == "T1":
    allowed_modes = ["📊 รายงาน"]
elif user_level == "T7":
    allowed_modes = ["📥 Tapping MC"]
elif user_level == "T8":
    allowed_modes = ["📊 รายงาน"]

menu = st.sidebar.selectbox("📌 โหมด", allowed_modes)

# 📥 Tapping MC
if menu == "📥 Tapping MC":
    st.subheader("📥 กรอกข้อมูล Tapping")

    with st.form("tapping_form"):
        job_id = generate_job_id()
        if job_id is None:
            st.error("⚠️ ไม่สามารถสร้าง Job ID ได้")
            st.stop()

        st.markdown(f"**🆔 Job ID:** `{job_id}`")
        part_code = st.selectbox("🔩 รหัสงาน", part_master)
        machine = st.selectbox("🛠 ชื่อเครื่อง", machines_list)
        lot = st.text_input("📦 Lot Number")
        woc = st.text_input("📄 WOC")
        vehicle_number = st.text_input("🚚 หมายเลขTAG")
        checked = st.number_input("🔍 จำนวนที่ตรวจสอบทั้งหมดของ Lot", 0)
        ng = st.number_input("❌ จำนวน NG", 0)
        pending = st.number_input("⏳ จำนวนยังไม่ตรวจ", 0)
        reason_ng = st.selectbox("📋 หัวข้องานเสีย", reason_list)

        total = ng + pending

        # ตรวจสอบว่า WOC และ Lot Number ถูกกรอก
        if not woc:
            st.error("⚠️ กรุณาบันทึกหมายเลข WOC")
        if not lot:
            st.error("⚠️ กรุณาบันทึกหมายเลข Lot")

        # กำหนดปุ่มให้กดได้เฉพาะเมื่อกรอกครบ
        submit_button = st.form_submit_button("✅ บันทึกข้อมูล")

        # หาก WOC หรือ Lot ยังไม่กรอก จะไม่ให้กดปุ่มบันทึก
        if submit_button and woc and lot:
            row = [
                now_th().strftime("%Y-%m-%d %H:%M:%S"),  # วันที่
                job_id,                                  # Job ID
                user,                                    # ชื่อพนักงาน
                part_code,                               # รหัสงาน
                machine,                                 # ชื่อเครื่อง
                lot,                                     # Lot Number
                checked,                                 # จำนวนที่ตรวจสอบทั้งหมดของ Lot
                ng,                                      # จำนวน NG
                pending,                                 # จำนวนยังไม่ตรวจ
                total,                                   # จำนวนทั้งหมด
                "Tapping MC",                            # สถานะ
                woc,                                     # WOC
                vehicle_number,                          # หมายเลขTAG
                "",                                      # เวลา Scrap/Recheck
                "",                                      # เวลา Cleaned
                "",                                      # ผู้ล้าง
                reason_ng                                # หัวข้องานเสีย
            ]

            try:
                worksheet.append_row(row)
                st.success("✅ บันทึกเรียบร้อย")
                send_telegram_message(
                    f"📥 <b>New Tapping</b>\n"
                    f"🆔 Job ID: <code>{job_id}</code>\n"
                    f"👷‍♂️ พนักงาน: {user}\n"
                    f"🔩 รหัสงาน: {part_code}\n"
                    f"🛠 เครื่อง: {machine}\n"
                    f"📦 Lot: {lot}\n"
                    f"📄 WOC: {woc}\n"
                    f"🚚 หมายเลขTAG: {vehicle_number}\n"
                    f"❌ NG: {ng} | ⏳ ยังไม่ตรวจ: {pending}\n"
                    f"📋 หัวข้องานเสีย: {reason_ng}"
                )
            except Exception as e:
                st.error(f"⚠️ Error appending data to sheet: {e}")

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

# 🛠 Upload Master
elif menu == "🛠 Upload Master":
    password = st.text_input("🔐 รหัส Sup", type="password")
    if password == "Sup":
        st.subheader("🛠 อัปโหลด Master")
        emp_txt = st.text_area("👥 ชื่อพนักงาน (ชื่อ,รหัส,ระดับ)", height=150)
        part_txt = st.text_area("🧾 รหัสงาน", height=150)
        if st.button("📤 อัปโหลด"):
            if emp_txt:
                emp_lines = [e.strip().split(",") for e in emp_txt.strip().split("\n") if len(e.strip().split(",")) == 3]
                emp_values = [["ชื่อพนักงาน", "รหัส", "ระดับ"]] + emp_lines
                sheet.values_update("employee_master!A1", {"valueInputOption": "RAW"}, {"values": emp_values})
            if part_txt:
                part_lines = [[p.strip()] for p in part_txt.strip().split("\n") if p.strip()]
                sheet.values_update("part_code_master!A1", {"valueInputOption": "RAW"}, {"values": [["รหัสงาน"]] + part_lines})
            st.success("✅ อัปโหลด Master สำเร็จแล้ว")
            st.rerun()
