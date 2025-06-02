
# 📦 Import Library
from datetime import datetime
import os
import pandas as pd
import streamlit as st
from PIL import Image
import requests
import gspread
from google.oauth2.service_account import Credentials

# 📁 ตั้งค่าการเชื่อมต่อ Google Sheets
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
GSHEET_ID = "1GM-es30UBsqFCxBVQbBxht6IntIkL6troc5c2PWD3JA"
GSHEET_NAME = "Sheet1"

creds = Credentials.from_service_account_info(st.secrets["GOOGLE_SHEETS_CREDENTIALS"], scopes=SCOPE)
client = gspread.authorize(creds)
worksheet = client.open_by_key(GSHEET_ID).worksheet(GSHEET_NAME)

# 📁 Path สำหรับรูปภาพ
DATA_DIR = "data"
IMAGE_FOLDER = os.path.join(DATA_DIR, "images")
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# 📡 Telegram
def send_telegram_message(message):
    TELEGRAM_TOKEN = "7617656983:AAGqI7jQvEtKZw_tD11cQneH57WvYWl9r_s"
    TELEGRAM_CHAT_ID = "-4944715716"
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
        requests.post(url, data=payload)
    except Exception as e:
        st.warning(f"⚠️ ไม่สามารถส่งข้อความ Telegram ได้: {e}")

# 🌐 UI
st.set_page_config(page_title="Sorting Process", layout="wide")
st.title("🔧 ระบบบันทึกข้อมูล Sorting Process - SCS")
menu = st.sidebar.selectbox("📌 เลือกโหมด", ["📥 Sorting MC", "🧾 Waiting Judgement", "💧 Oil Cleaning", "📊 รายงาน"])

# 🔄 โหลดข้อมูลจาก Google Sheet
def load_data():
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

df = load_data()

# 📥 โหมด Sorting MC
if menu == "📥 Sorting MC":
    st.subheader("📥 กรอกข้อมูล Sorting")
    with st.form("sorting_form"):
        now = datetime.now()
        job_id = now.strftime("%y%m%H%M%S")
        employee = st.text_input("👷‍♂️ ชื่อพนักงาน")
        part_code = st.text_input("🔩 รหัสงาน")
        machine = st.selectbox("🛠 ชื่อเครื่อง", [f"SM{i:02}" for i in range(1, 31)])
        lot = st.text_input("📦 Lot Number")
        qty_checked = st.number_input("🔍 จำนวนที่ตรวจสอบ", min_value=0)
        qty_ng = st.number_input("❌ จำนวน NG", min_value=0)
        qty_pending = st.number_input("⏳ ยังไม่ตรวจ", min_value=0)
        total = qty_ng + qty_pending
        image = st.file_uploader("📸 อัปโหลดรูป", type=["jpg", "jpeg", "png"])

        submitted = st.form_submit_button("✅ บันทึก")
        if submitted:
            image_path = ""
            if image:
                image_path = os.path.join(IMAGE_FOLDER, f"{job_id}.jpg")
                with open(image_path, "wb") as f:
                    f.write(image.read())

            row = [now.strftime("%Y-%m-%d %H:%M:%S"), job_id, employee, part_code, machine, lot, qty_checked, qty_ng, qty_pending, total, "Sorting MC", "", "", image_path]
            worksheet.append_row(row)
            st.success("✅ บันทึกสำเร็จ")
            send_telegram_message(f"📥 <b>New Sorting</b> - Job ID: <code>{job_id}</code>")

# 🧾 โหมด Judgement
elif menu == "🧾 Waiting Judgement":
    st.subheader("🧾 รอตัดสินใจ Recheck หรือ Scrap")
    pending = df[df["สถานะ"] == "Sorting MC"]
    for idx, row in pending.iterrows():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"🆔 <b>{row['Job ID']}</b> - {row['รหัสงาน']} ({row['ชื่อพนักงาน']})")
        with col2:
            if st.button("♻️ Recheck", key=f"recheck_{row['Job ID']}"):
                cell = worksheet.find(row["Job ID"])
                worksheet.update_cell(cell.row, 11, "Recheck")
                worksheet.update_cell(cell.row, 12, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                st.rerun()
            if st.button("🗑 Scrap", key=f"scrap_{row['Job ID']}"):
                cell = worksheet.find(row["Job ID"])
                worksheet.update_cell(cell.row, 11, "Scrap")
                worksheet.update_cell(cell.row, 12, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                st.rerun()

# 💧 โหมด Oil Cleaning
elif menu == "💧 Oil Cleaning":
    st.subheader("💧 รอเข้าสู่กระบวนการล้าง")
    rechecks = df[df["สถานะ"] == "Recheck"]
    for idx, row in rechecks.iterrows():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"🆔 {row['Job ID']} - {row['รหัสงาน']} ({row['ชื่อพนักงาน']})")
        with col2:
            if st.button("✅ ล้างเสร็จแล้ว", key=f"done_{row['Job ID']}"):
                cell = worksheet.find(row["Job ID"])
                worksheet.update_cell(cell.row, 11, "Lavage")
                worksheet.update_cell(cell.row, 13, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                st.rerun()

# 📊 รายงาน
elif menu == "📊 รายงาน":
    st.subheader("📊 รายงาน")
    view = st.selectbox("เลือกช่วงเวลา", ["ทั้งหมด", "รายวัน", "รายสัปดาห์", "รายเดือน", "รายปี"])
    now = datetime.now()
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

    scrap_summary = df[df["สถานะ"] == "Scrap"].groupby("รหัสงาน")["จำนวนทั้งหมด"].sum().reset_index()
    st.markdown("📌 **ยอด Scrap แยกรหัสงาน**")
    st.dataframe(scrap_summary)
