# 📦 Import Libraries
from datetime import datetime
import os
import pandas as pd
import streamlit as st
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials
import requests

# ✅ Telegram
def send_telegram_message(message):
    TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
    TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
        requests.post(url, data=payload)
    except Exception as e:
        st.warning(f"⚠️ ไม่สามารถส่งข้อความ Telegram ได้: {e}")

# ✅ Google Sheets Setup
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(
    st.secrets["GOOGLE_SHEETS_CREDENTIALS"], scopes=SCOPE)
gc = gspread.authorize(creds)

# เปลี่ยน URL ให้เป็นของคุณ
SHEET_URL = "https://docs.google.com/spreadsheets/d/1GM-es30UBsqFCxBVQbBxht6IntIkL6troc5c2PWD3JA/edit?usp=sharing"
spreadsheet = gc.open_by_url(SHEET_URL)
worksheet = spreadsheet.worksheet("Data")

# 📁 โฟลเดอร์ภาพ
IMAGE_FOLDER = "images"
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# 🌐 Web setup
st.set_page_config(page_title="Sorting Process", layout="wide")
st.title("🔧 ระบบบันทึกข้อมูล Sorting Process - Google Sheets Edition")
menu = st.sidebar.selectbox("📌 เลือกโหมด", [
    "📥 Sorting MC", "🧾 Waiting Judgement", "💧 Oil Cleaning", "📊 รายงาน", "🛠 Upload Master"
])

# 📦 Load Master
@st.cache_data
def load_master_data():
    emp = st.secrets.get("employee_master", ["ไม่มีข้อมูล"])
    part = st.secrets.get("part_master", ["ไม่มีข้อมูล"])
    return emp, part

emp_list, part_list = load_master_data()

# 📄 Load current data
def load_data():
    records = worksheet.get_all_records()
    return pd.DataFrame(records)

df = load_data()

# 🆔 Auto Job ID
def generate_job_id():
    now = datetime.now()
    prefix = now.strftime("%y%m")
    existing = df[df['Job ID'].astype(str).str.startswith(prefix)]
    try:
        last_seq = max([int(str(jid)[-4:]) for jid in existing['Job ID']], default=0)
    except:
        last_seq = 0
    return f"{prefix}{last_seq + 1:04d}"

# 📥 Sorting MC
if menu == "📥 Sorting MC":
    st.subheader("📥 กรอกข้อมูล Sorting")
    with st.form("sorting_form"):
        job_id = generate_job_id()
        st.markdown(f"**🆔 Job ID:** `{job_id}`")

        employee = st.selectbox("👷‍♂️ พนักงาน", emp_list)
        part_code = st.selectbox("🔩 รหัสงาน", part_list)
        machine = st.selectbox("🛠 เครื่อง", [f"SM{i:02}" for i in range(1, 31)])
        lot_number = st.text_input("📦 Lot Number")
        qty_checked = st.number_input("🔍 ตรวจทั้งหมด", min_value=0)
        qty_ng = st.number_input("❌ NG", min_value=0)
        qty_pending = st.number_input("⏳ ยังไม่ตรวจ", min_value=0)
        image = st.file_uploader("📸 รูปภาพ", type=["jpg", "png", "jpeg"])

        submitted = st.form_submit_button("✅ บันทึก")
        if submitted:
            total = qty_ng + qty_pending
            image_path = ""
            if image:
                image_path = os.path.join(IMAGE_FOLDER, f"{job_id}.jpg")
                with open(image_path, "wb") as f:
                    f.write(image.read())

            row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), job_id, employee, part_code,
                   machine, lot_number, qty_checked, qty_ng, qty_pending, total,
                   "Sorting MC", "", "", image_path]
            worksheet.append_row(row)
            st.success("✅ บันทึกแล้ว")
            send_telegram_message(
                f"📥 <b>New Job</b> ID: <code>{job_id}</code>\n👷‍♂️ {employee} 🔩 {part_code}\nNG: {qty_ng} / ยังไม่ตรวจ: {qty_pending}"
            )
            st.rerun()

# 🧾 Waiting Judgement
elif menu == "🧾 Waiting Judgement":
    st.subheader("🧾 พิจารณา Scrap / Recheck")
    password = st.text_input("🔐 รหัสผ่าน", type="password")
    if password == "Admin1":
        pending = df[df["สถานะ"] == "Sorting MC"]
        for idx, row in pending.iterrows():
            col1, col2, col3 = st.columns([2, 2, 2])
            with col1:
                st.markdown(f"🆔 <b>{row['Job ID']}</b> - {row['รหัสงาน']}", unsafe_allow_html=True)
                st.markdown(f"❌ NG: {row['จำนวน NG']} / ⏳ {row['จำนวนยังไม่ตรวจ']}")
            with col2:
                if st.button("♻️ Recheck", key=f"r_{row['Job ID']}"):
                    worksheet.update_cell(idx + 2, 11, "Recheck")
                    worksheet.update_cell(idx + 2, 12, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    send_telegram_message(f"🔁 <b>Recheck</b>: Job ID <code>{row['Job ID']}</code>")
                    st.rerun()
            with col3:
                if st.button("🗑 Scrap", key=f"s_{row['Job ID']}"):
                    worksheet.update_cell(idx + 2, 11, "Scrap")
                    worksheet.update_cell(idx + 2, 12, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    send_telegram_message(f"🗑 <b>Scrap</b>: Job ID <code>{row['Job ID']}</code>")
                    st.rerun()
    else:
        st.error("🔒 รหัสไม่ถูกต้อง")

# 💧 Oil Cleaning
elif menu == "💧 Oil Cleaning":
    st.subheader("💧 ล้างงานที่ Recheck")
    jobs = df[df["สถานะ"] == "Recheck"]
    for idx, row in jobs.iterrows():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"🆔 {row['Job ID']} - {row['รหัสงาน']} ({row['ชื่อพนักงาน']}) - Total: {row['จำนวนทั้งหมด']}")
        with col2:
            cleaner = st.selectbox("👤 ผู้ล้าง", emp_list, key=f"cleaner_{idx}")
            if st.button("✅ ล้างเสร็จ", key=f"lav_{row['Job ID']}"):
                if cleaner:
                    worksheet.update_cell(idx + 2, 11, "Lavage")
                    worksheet.update_cell(idx + 2, 13, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    send_telegram_message(f"💧 <b>ล้างแล้ว</b>: Job ID <code>{row['Job ID']}</code> โดย {cleaner}")
                    st.rerun()
                else:
                    st.warning("⚠ กรุณาเลือกชื่อผู้ล้าง")

# 📊 รายงาน
elif menu == "📊 รายงาน":
    st.subheader("📊 รายงาน")
    view = st.selectbox("📆 ช่วงเวลา", ["ทั้งหมด", "รายวัน", "รายเดือน", "รายปี"])
    df["วันที่"] = pd.to_datetime(df["วันที่"], errors="coerce")
    now = datetime.now()
    if view == "รายวัน":
        df = df[df["วันที่"].dt.date == now.date()]
    elif view == "รายเดือน":
        df = df[df["วันที่"].dt.month == now.month]
    elif view == "รายปี":
        df = df[df["วันที่"].dt.year == now.year]
    st.dataframe(df)
    scrap_summary = df[df["สถานะ"] == "Scrap"].groupby("รหัสงาน")["จำนวนทั้งหมด"].sum().reset_index()
    st.markdown("📌 <b>รวม Scrap ตามรหัสงาน</b>", unsafe_allow_html=True)
    st.dataframe(scrap_summary)

# 🛠 Upload Master (จำลองจาก st.secrets)
elif menu == "🛠 Upload Master":
    st.subheader("🛠 อัปโหลด Master Data")
    st.info("🚫 ระบบนี้จำลองข้อมูล Master ผ่าน `st.secrets` เท่านั้น\nหากต้องการอัปโหลดจริง ให้ปรับโค้ดให้บันทึกไฟล์ หรือใช้ Google Sheets แยก")
