# 📦 Import Library
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
import gspread
import requests
import uuid
from google.oauth2.service_account import Credentials

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

# 🌐 เวลาประเทศไทย
def now_th():
    return datetime.utcnow() + timedelta(hours=7)

# 🔐 Auth Google Sheets
SCOPE = ["https://www.googleapis.com/auth/spreadsheets"]
service_account_info = st.secrets["GOOGLE_SHEETS_CREDENTIALS"]
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
client = gspread.authorize(creds)

# 📊 Google Sheet URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1GM-es30UBsqFCxBVQbBxht6IntIkL6troc5c2PWD3JA/edit?usp=sharing"
sheet = client.open_by_url(SHEET_URL)
worksheet = sheet.worksheet("Data")

# 📁 Master Data
try:
    emp_sheet = sheet.worksheet("employee_master")
    emp_data = emp_sheet.get_all_records()
    emp_names = [r["ชื่อพนักงาน"] for r in emp_data if r.get("ชื่อพนักงาน")]
except:
    emp_names = []
    emp_data = []

try:
    part_master = sheet.worksheet("part_code_master").col_values(1)[1:]
except:
    part_master = []

# 🆔 Job ID
def generate_job_id():
    records = worksheet.get_all_records()
    prefix = now_th().strftime("%y%m")
    filtered = [
        r for r in records
        if isinstance(r.get("Job ID"), str) and r["Job ID"].startswith(prefix)
    ]
    if filtered:
        try:
            last_seq = max([
                int(r["Job ID"][-4:])
                for r in filtered
                if isinstance(r.get("Job ID"), str) and r["Job ID"][-4:].isdigit()
            ])
        except:
            last_seq = 0
    else:
        last_seq = 0
    return f"{prefix}{last_seq + 1:04d}"

# 🔐 Login
if "user" not in st.session_state:
    st.title("🔐 เข้าสู่ระบบ")
    username = st.selectbox("👤 Username", emp_names)
    password = st.text_input("🔑 Password", type="password")
    if st.button("➡️ Login"):
        found = next((r for r in emp_data if r["ชื่อพนักงาน"] == username and str(r["รหัส"]) == password), None)
        if found:
            st.session_state["user"] = username
            st.rerun()
        else:
            st.error("❌ รหัสผ่านไม่ถูกต้อง")
    st.stop()

# 🌐 UI Main
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
        employee = st.session_state["user"]
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
                now_th().strftime("%Y-%m-%d %H:%M:%S"), job_id, employee, part_code,
                machine, lot_number, qty_checked, qty_ng, qty_pending, total,
                "Sorting MC", "", "", ""
            ]
            worksheet.append_row(new_row)
            st.success("✅ บันทึกข้อมูลเรียบร้อยแล้ว")
            send_telegram_message(
                f"📥 <b>New Sorting</b>\n"
                f"🆔 Job ID: <code>{job_id}</code>\n"
                f"👷‍♂️ พนักงาน: {employee}\n"
                f"🔩 รหัสงาน: {part_code}\n"
                f"📦 Lot: {lot_number}\n"
                f"🛠 เครื่อง: {machine}\n"
                f"❌ NG: {qty_ng} | ⏳ ยังไม่ตรวจ: {qty_pending}"
            )

# 🧾 Waiting Judgement
elif menu == "🧾 Waiting Judgement":
    st.subheader("🔍 เลือกตัดสินใจ (Recheck / Scrap)")
    df = pd.DataFrame(worksheet.get_all_records())
    df = df[df["สถานะ"] == "Sorting MC"]
    for idx, row in df.iterrows():
        st.markdown(
            f"🆔 <b>{row['Job ID']}</b> | รหัส: {row['รหัสงาน']} | NG: {row['จำนวน NG']} | ยังไม่ตรวจ: {row['จำนวนยังไม่ตรวจ']}",
            unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        if col1.button(f"♻️ Recheck - {row['Job ID']}", key=f"recheck_{row['Job ID']}"):
            worksheet.update_cell(idx + 2, 11, "Recheck")
            worksheet.update_cell(idx + 2, 12, now_th().strftime("%Y-%m-%d %H:%M:%S"))
            send_telegram_message(f"♻️ <b>Recheck</b>: Job ID <code>{row['Job ID']}</code>")
            st.rerun()
        if col2.button(f"🗑 Scrap - {row['Job ID']}", key=f"scrap_{row['Job ID']}"):
            worksheet.update_cell(idx + 2, 11, "Scrap")
            worksheet.update_cell(idx + 2, 12, now_th().strftime("%Y-%m-%d %H:%M:%S"))
            send_telegram_message(f"🗑 <b>Scrap</b>: Job ID <code>{row['Job ID']}</code>")
            st.rerun()

# 💧 Oil Cleaning
elif menu == "💧 Oil Cleaning":
    st.subheader("💧 งานที่รอการล้าง")
    df = pd.DataFrame(worksheet.get_all_records())
    df = df[df["สถานะ"] == "Recheck"]
    user = st.session_state["user"]
    for idx, row in df.iterrows():
        st.markdown(f"🆔 <b>{row['Job ID']}</b> | {row['รหัสงาน']} | ทั้งหมด: {row['จำนวนทั้งหมด']}", unsafe_allow_html=True)
        if st.button(f"✅ ล้างเสร็จแล้ว - {row['Job ID']}", key=f"cleaned_{row['Job ID']}_{idx}"):
            worksheet.update_cell(idx + 2, 11, "Cleaned")
            worksheet.update_cell(idx + 2, 13, now_th().strftime("%Y-%m-%d %H:%M:%S"))
            worksheet.update_cell(idx + 2, 14, user)
            send_telegram_message(
                f"💧 <b>ล้างเสร็จแล้ว</b>\n"
                f"🆔 Job ID: <code>{row['Job ID']}</code>\n"
                f"🔩 รหัสงาน: {row['รหัสงาน']}\n"
                f"📦 Lot: {row['Lot Number']}\n"
                f"🔢 จำนวนทั้งหมด: {row['จำนวนทั้งหมด']}\n"
                f"👷‍♂️ โดย: {user}"
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
    password = st.text_input("🔐 รหัส Sup เพื่ออัปโหลด Master", type="password")
    if password == "Sup":
        st.subheader("🛠 อัปโหลดรายชื่อพนักงานและรหัสงาน")
        emp_txt = st.text_area("👥 วางรายชื่อพนักงาน (Enter คั่น)", height=150)
        emp_code = st.text_area("🔑 รหัสผ่าน (Enter คั่น ลำดับตรงกัน)", height=150)
        part_txt = st.text_area("🧾 วางรหัสงาน (Enter คั่น)", height=150)
        if st.button("📤 อัปโหลด"):
            if emp_txt and emp_code:
                names = emp_txt.strip().split("\n")
                codes = emp_code.strip().split("\n")
                emp_values = [["ชื่อพนักงาน", "รหัส"]] + list(zip(names, codes))
                sheet.values_update("employee_master!A1", {"valueInputOption": "RAW"}, {"values": emp_values})
            if part_txt:
                part_values = [[p] for p in part_txt.strip().split("\n") if p.strip()]
                sheet.values_update("part_code_master!A1", {"valueInputOption": "RAW"}, {"values": [["รหัสงาน"]] + part_values})
            st.success("✅ อัปโหลดรายชื่อสำเร็จแล้ว")
            st.rerun()
