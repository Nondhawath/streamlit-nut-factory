# 📦 Import Library
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import gspread
import requests
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

# 🌐 Timezone +7
def now_th():
    return datetime.utcnow() + timedelta(hours=7)

# 🔐 Auth Google Sheets
SCOPE = ["https://www.googleapis.com/auth/spreadsheets"]
service_account_info = st.secrets["GOOGLE_SHEETS_CREDENTIALS"]
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
client = gspread.authorize(creds)

# 🔗 Sheet
SHEET_URL = "https://docs.google.com/spreadsheets/d/1GM-es30UBsqFCxBVQbBxht6IntIkL6troc5c2PWD3JA/edit?usp=sharing"
sheet = client.open_by_url(SHEET_URL)
worksheet = sheet.worksheet("Data")

# 📁 Master Data
try:
    emp_data = sheet.worksheet("employee_master").get_all_records()
    emp_names = [row["ชื่อพนักงาน"] for row in emp_data]
    emp_pass_dict = {row["ชื่อพนักงาน"]: str(row["รหัส"]).strip() for row in emp_data}
except:
    emp_names = []
    emp_pass_dict = {}

try:
    part_master = sheet.worksheet("part_code_master").col_values(1)[1:]
except:
    part_master = []

# 🆔 Login
if "user" not in st.session_state:
    st.header("🔐 เข้าสู่ระบบ")
    username = st.selectbox("👤 เลือกชื่อพนักงาน", emp_names)
    password = st.text_input("🔑 รหัสผ่าน", type="password")
    if st.button("➡️ เข้าสู่ระบบ"):
        if emp_pass_dict.get(username) == password:
            st.session_state.user = username
            st.experimental_rerun()
        else:
            st.error("❌ รหัสผ่านไม่ถูกต้อง")
    st.stop()

# 🔢 Job ID
def generate_job_id():
    records = worksheet.get_all_records()
    prefix = now_th().strftime("%y%m")
    filtered = [r for r in records if str(r.get("Job ID", "")).startswith(prefix)]
    if filtered:
        last_seq = max([
            int(r["Job ID"][-4:]) for r in filtered if str(r["Job ID"][-4:]).isdigit()
        ])
    else:
        last_seq = 0
    return f"{prefix}{last_seq + 1:04d}"

# 🌐 UI
st.set_page_config(page_title="Sorting Process", layout="wide")
st.title(f"🔧 Sorting Process - SCS ({st.session_state.user})")
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
        qty_checked = st.number_input("🔍 ตรวจทั้งหมด", min_value=0)
        qty_ng = st.number_input("❌ NG", min_value=0)
        qty_pending = st.number_input("⏳ ยังไม่ตรวจ", min_value=0)
        total = qty_ng + qty_pending
        submitted = st.form_submit_button("✅ บันทึกข้อมูล")
        if submitted:
            row = [
                now_th().strftime("%Y-%m-%d %H:%M:%S"), job_id, st.session_state.user, part_code,
                machine, lot_number, qty_checked, qty_ng, qty_pending, total,
                "Sorting MC", "", "", ""
            ]
            worksheet.append_row(row)
            st.success("✅ บันทึกสำเร็จ")
            send_telegram_message(
                f"📥 <b>New Sorting</b>\n"
                f"🆔 Job ID: <code>{job_id}</code>\n"
                f"👷‍♂️ พนักงาน: {st.session_state.user}\n"
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
        st.markdown(f"🆔 <b>{row['Job ID']}</b> | {row['รหัสงาน']} | NG: {row['จำนวน NG']} | ยังไม่ตรวจ: {row['จำนวนยังไม่ตรวจ']}", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        if col1.button("♻️ Recheck", key=f"recheck_{row['Job ID']}"):
            worksheet.update_cell(idx + 2, 11, "Recheck")
            worksheet.update_cell(idx + 2, 12, now_th().strftime("%Y-%m-%d %H:%M:%S"))
            send_telegram_message(f"♻️ <b>Recheck</b>: Job ID <code>{row['Job ID']}</code>")
            st.rerun()
        if col2.button("🗑 Scrap", key=f"scrap_{row['Job ID']}"):
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
        if st.button("✅ ล้างเสร็จแล้ว", key=f"cleaned_{row['Job ID']}"):
            worksheet.update_cell(idx + 2, 11, "Cleaned")
            worksheet.update_cell(idx + 2, 13, now_th().strftime("%Y-%m-%d %H:%M:%S"))
            worksheet.update_cell(idx + 2, 14, st.session_state.user)
            send_telegram_message(
                f"💧 <b>ล้างเสร็จแล้ว</b>\n"
                f"🆔 Job ID: <code>{row['Job ID']}</code>\n"
                f"🔩 รหัสงาน: {row['รหัสงาน']}\n"
                f"📦 ทั้งหมด: {row['จำนวนทั้งหมด']}\n"
                f"👷‍♂️ ผู้ล้าง: {st.session_state.user}"
            )
            st.success("✅ ล้างเสร็จแล้ว")
            st.rerun()

# 📊 รายงาน
elif menu == "📊 รายงาน":
    df = pd.DataFrame(worksheet.get_all_records())
    df["วันที่"] = pd.to_datetime(df["วันที่"], errors="coerce")
    view = st.selectbox("📅 เลือกช่วงเวลา", ["ทั้งหมด", "รายวัน", "รายสัปดาห์", "รายเดือน", "รายปี"])
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
    scrap = df[df["สถานะ"] == "Scrap"].groupby("รหัสงาน")["จำนวนทั้งหมด"].sum().reset_index()
    st.markdown("📌 สรุป Scrap แยกรหัสงาน")
    st.dataframe(scrap)

# 🛠 Upload Master
elif menu == "🛠 Upload Master":
    password = st.text_input("🔐 รหัส Sup", type="password")
    if password == "Sup":
        st.subheader("🛠 อัปโหลดรายชื่อพนักงานและรหัสงาน")
        emp_txt = st.text_area("👥 รายชื่อพนักงาน (Enter คั่น)", height=150)
        part_txt = st.text_area("🧾 รหัสงาน (Enter คั่น)", height=150)
        if st.button("📤 อัปโหลด"):
            if emp_txt:
                emp_values = [x.split(",") for x in emp_txt.strip().split("\n") if x.strip()]
                sheet.values_update("employee_master!A1", {"valueInputOption": "RAW"}, {
                    "values": [["ชื่อพนักงาน", "รหัส"]] + emp_values
                })
            if part_txt:
                part_values = [[p] for p in part_txt.strip().split("\n") if p.strip()]
                sheet.values_update("part_code_master!A1", {"valueInputOption": "RAW"}, {
                    "values": [["รหัสงาน"]] + part_values
                })
            st.success("✅ อัปโหลดสำเร็จแล้ว")
            st.rerun()
