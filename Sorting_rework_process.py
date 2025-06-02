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
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        requests.post(url, data=payload)
    except Exception as e:
        st.warning(f"⚠️ ไม่สามารถส่งข้อความ Telegram ได้: {e}")

# ⏰ ใช้เวลาประเทศไทย
def now_th():
    return datetime.utcnow() + timedelta(hours=7)

# 🔐 เชื่อม Google Sheets
SCOPE = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(
    st.secrets["GOOGLE_SHEETS_CREDENTIALS"], scopes=SCOPE)
client = gspread.authorize(creds)

SHEET_URL = "https://docs.google.com/spreadsheets/d/1GM-es30UBsqFCxBVQbBxht6IntIkL6troc5c2PWD3JA"
sheet = client.open_by_url(SHEET_URL)
worksheet = sheet.worksheet("Data")

# 📁 โหลด Master
try:
    emp_ws = sheet.worksheet("employee_master")
    emp_data = emp_ws.get_all_records()
    emp_names = [e["ชื่อพนักงาน"] for e in emp_data]
    emp_passwords = {e["ชื่อพนักงาน"]: str(e["รหัส"]) for e in emp_data}
except:
    emp_names = []
    emp_passwords = {}

try:
    part_master = sheet.worksheet("part_code_master").col_values(1)[1:]
except:
    part_master = []

# 🔐 Login
if "login_success" not in st.session_state:
    st.session_state.login_success = False

if not st.session_state.login_success:
    st.title("🔒 เข้าสู่ระบบ")
    username = st.selectbox("👤 Username", emp_names)
    password = st.text_input("🔑 Password", type="password")
    if st.button("🔓 Login"):
        if username in emp_passwords and password == emp_passwords[username]:
            st.session_state.login_success = True
            st.session_state.username = username
            st.success("✅ เข้าสู่ระบบสำเร็จ")
            st.rerun()
        else:
            st.error("❌ รหัสผ่านไม่ถูกต้อง")
    st.stop()

# 🆔 สร้าง Job ID
def generate_job_id():
    records = worksheet.get_all_records()
    prefix = now_th().strftime("%y%m")
    filtered = [r for r in records if str(r.get("Job ID", "")).startswith(prefix)]
    if filtered:
        try:
            last_seq = max([int(r["Job ID"][-4:]) for r in filtered if str(r["Job ID"][-4:]).isdigit()])
        except:
            last_seq = 0
    else:
        last_seq = 0
    return f"{prefix}{last_seq + 1:04d}"

# 🌐 UI
st.set_page_config(page_title="Sorting Process", layout="wide")
st.title("🔧 ระบบบันทึกข้อมูล Sorting Process - SCS")
menu = st.sidebar.selectbox("📌 เลือกโหมด", [
    "📥 Sorting MC", "🧾 Waiting Judgement", "💧 Oil Cleaning", "📊 รายงาน", "🛠 Upload Master"
])

# 📥 Sorting MC
if menu == "📥 Sorting MC":
    st.subheader("📥 กรอกข้อมูล Sorting")
    with st.form("sorting_form"):
        job_id = generate_job_id()
        st.markdown(f"**🆔 Job ID:** `{job_id}`")
        part_code = st.selectbox("🔩 เลือกรหัสงาน", part_master)
        machine = st.selectbox("🛠 เลือกชื่อเครื่อง", [f"SM{i:02}" for i in range(1, 31)])
        lot_number = st.text_input("📦 Lot Number")
        qty_checked = st.number_input("🔍 จำนวนที่ตรวจสอบทั้งหมดของ Lot", min_value=0)
        qty_ng = st.number_input("❌ จำนวน NG", min_value=0)
        qty_pending = st.number_input("⏳ จำนวนที่ยังไม่ตรวจ", min_value=0)
        total = qty_ng + qty_pending
        submitted = st.form_submit_button("✅ บันทึกข้อมูล")
        if submitted:
            new_row = [
                now_th().strftime("%Y-%m-%d %H:%M:%S"), job_id, st.session_state.username, part_code,
                machine, lot_number, qty_checked, qty_ng, qty_pending, total,
                "Sorting MC", "", "", ""
            ]
            worksheet.append_row(new_row)
            st.success("✅ บันทึกข้อมูลเรียบร้อยแล้ว")
            send_telegram_message(
                f"📥 <b>New Sorting</b>\n"
                f"🆔 Job ID: <code>{job_id}</code>\n"
                f"👷‍♂️ พนักงาน: {st.session_state.username}\n"
                f"🔩 รหัสงาน: {part_code}\n"
                f"📦 Lot: {lot_number}\n"
                f"🛠 เครื่อง: {machine}\n"
                f"❌ NG: {qty_ng} | ⏳ ยังไม่ตรวจ: {qty_pending}"
            )

# 🧾 Waiting Judgement
elif menu == "🧾 Waiting Judgement":
    df = pd.DataFrame(worksheet.get_all_records())
    df = df[df["สถานะ"] == "Sorting MC"]
    st.subheader("🔍 เลือกตัดสินใจ (Recheck / Scrap)")
    for idx, row in df.iterrows():
        st.markdown(f"🆔 <b>{row['Job ID']}</b> | รหัส: {row['รหัสงาน']} | NG: {row['จำนวน NG']} | ยังไม่ตรวจ: {row['จำนวนยังไม่ตรวจ']}", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        if col1.button(f"♻️ Recheck", key=f"recheck_{row['Job ID']}"):
            worksheet.update_cell(idx + 2, 11, "Recheck")
            worksheet.update_cell(idx + 2, 12, now_th().strftime("%Y-%m-%d %H:%M:%S"))
            send_telegram_message(f"♻️ <b>Recheck</b>: Job ID <code>{row['Job ID']}</code>")
            st.rerun()
        if col2.button(f"🗑 Scrap", key=f"scrap_{row['Job ID']}"):
            worksheet.update_cell(idx + 2, 11, "Scrap")
            worksheet.update_cell(idx + 2, 12, now_th().strftime("%Y-%m-%d %H:%M:%S"))
            send_telegram_message(f"🗑 <b>Scrap</b>: Job ID <code>{row['Job ID']}</code>")
            st.rerun()

# 💧 Oil Cleaning
elif menu == "💧 Oil Cleaning":
    st.subheader("💧 งานที่รอการล้าง")
    df = pd.DataFrame(worksheet.get_all_records())
    df = df[df["สถานะ"] == "Recheck"]
    for idx, row in df.iterrows():
        st.markdown(f"🆔 <b>{row['Job ID']}</b> | {row['รหัสงาน']} | ทั้งหมด: {row['จำนวนทั้งหมด']}", unsafe_allow_html=True)
        if st.button(f"✅ ล้างเสร็จแล้ว - {row['Job ID']}", key=f"cleaned_{row['Job ID']}"):
            worksheet.update_cell(idx + 2, 11, "Cleaned")
            worksheet.update_cell(idx + 2, 13, now_th().strftime("%Y-%m-%d %H:%M:%S"))
            worksheet.update_cell(idx + 2, 14, st.session_state.username)
            send_telegram_message(
                f"💧 <b>ล้างเสร็จแล้ว</b>\n"
                f"🆔 Job ID: <code>{row['Job ID']}</code>\n"
                f"🔩 รหัสงาน: {row['รหัสงาน']}\n"
                f"🔢 จำนวนทั้งหมด: {row['จำนวนทั้งหมด']}\n"
                f"👷‍♂️ ผู้ล้าง: {st.session_state.username}"
            )
            st.success("✅ ล้างเสร็จแล้ว")
            st.rerun()

# 📊 รายงาน
elif menu == "📊 รายงาน":
    df = pd.DataFrame(worksheet.get_all_records())
    view = st.selectbox("📅 เลือกช่วงเวลา", ["ทั้งหมด", "รายวัน", "รายสัปดาห์", "รายเดือน", "รายปี"])
    now = now_th()
    df["วันที่"] = pd.to_datetime(df["วันที่"], errors="coerce")
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
    st.subheader("🛠 อัปโหลด Master")
    password = st.text_input("🔐 รหัส Sup", type="password")
    if password == "Sup":
        emp_txt = st.text_area("👥 รายชื่อพนักงาน (ชื่อ|รหัส)", height=150)
        part_txt = st.text_area("🧾 รหัสงาน", height=150)
        if st.button("📤 อัปโหลด"):
            if emp_txt:
                rows = [["ชื่อพนักงาน", "รหัส"]] + [line.strip().split("|") for line in emp_txt.strip().split("\n") if "|" in line]
                sheet.values_update("employee_master!A1", {"valueInputOption": "RAW"}, {"values": rows})
            if part_txt:
                part_values = [["รหัสงาน"]] + [[p] for p in part_txt.strip().split("\n") if p.strip()]
                sheet.values_update("part_code_master!A1", {"valueInputOption": "RAW"}, {"values": part_values})
            st.success("✅ อัปโหลดสำเร็จแล้ว")
            st.rerun()
