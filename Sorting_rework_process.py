# 📦 Import Library
from datetime import datetime
import os
import pandas as pd
import streamlit as st
from PIL import Image
import requests
import gspread
from google.oauth2.service_account import Credentials

# 📡 Telegram Function
def send_telegram_message(message):
    TELEGRAM_TOKEN = "7617656983:AAGqI7jQvEtKZw_tD11cQneH57WvYWl9r_s"
    TELEGRAM_CHAT_ID = "-4944715716"
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        requests.post(url, data=payload)
    except Exception as e:
        st.warning(f"⚠️ ไม่สามารถส่ง Telegram: {e}")

# 📁 Path
DATA_DIR = "data"
IMAGE_FOLDER = os.path.join(DATA_DIR, "images")
EMP_PATH = os.path.join(DATA_DIR, "employee_master.xlsx")
PART_PATH = os.path.join(DATA_DIR, "part_code_master.xlsx")
GSPREAD_JSON = os.path.join(DATA_DIR, "upheld-modem-461701-h1-295195eda574.json")  # อัปโหลดไฟล์นี้
GSHEET_URL = "https://docs.google.com/spreadsheets/d/1GM-es30UBsqFCxBVQbBxht6IntIkL6troc5c2PWD3JA"

# 🔐 GSheet Setup
scope = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(GSPREAD_JSON, scopes=scope)
client = gspread.authorize(creds)
sheet = client.open_by_url(GSHEET_URL)
ws = sheet.worksheet("Sheet1")

# 🛡 Folder
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# 📄 Load Master
def load_master():
    try:
        emp = pd.read_excel(EMP_PATH)
    except:
        emp = pd.DataFrame(columns=["ชื่อพนักงาน"])
    try:
        part = pd.read_excel(PART_PATH)
    except:
        part = pd.DataFrame(columns=["รหัสงาน"])
    return emp, part

# 🆔 Job ID
def generate_job_id(df):
    now = datetime.now()
    prefix = now.strftime("%y%m")
    try:
        existing = df[df['Job ID'].astype(str).str.startswith(prefix)]
        last_seq = max([int(j[-4:]) for j in existing['Job ID']], default=0)
    except:
        last_seq = 0
    return f"{prefix}{last_seq + 1:04d}"

# 🔁 Load report
try:
    df = pd.DataFrame(ws.get_all_records())
    if not df.empty and "วันที่" in df.columns:
        df["วันที่"] = pd.to_datetime(df["วันที่"], errors="coerce")
except:
    df = pd.DataFrame()

emp_df, part_df = load_master()

# 🌐 Streamlit UI
st.set_page_config(page_title="Sorting Process", layout="wide")
st.title("🔧 ระบบบันทึกข้อมูล Sorting Process - Google Sheets")

menu = st.sidebar.selectbox("📌 เลือกโหมด", ["📥 Sorting MC", "🧾 Waiting Judgement", "💧 Oil Cleaning", "📊 รายงาน", "🛠 Upload Master"])

# 📥 Sorting MC
if menu == "📥 Sorting MC":
    st.subheader("📥 กรอกข้อมูล Sorting")
    with st.form("form_sort"):
        job_id = generate_job_id(df)
        st.markdown(f"**🆔 Job ID:** `{job_id}`")
        emp_list = emp_df["ชื่อพนักงาน"].dropna().unique()
        part_list = part_df["รหัสงาน"].dropna().unique()

        employee = st.selectbox("👷‍♂️ พนักงาน", emp_list)
        part_code = st.selectbox("🔩 รหัสงาน", part_list)
        machine = st.selectbox("🛠 เครื่อง", [f"SM{i:02}" for i in range(1, 31)])
        lot = st.text_input("📦 Lot Number")
        qty_all = st.number_input("🔍 จำนวนตรวจ", 0)
        qty_ng = st.number_input("❌ NG", 0)
        qty_pending = st.number_input("⏳ ยังไม่ตรวจ", 0)
        total = qty_ng + qty_pending
        image = st.file_uploader("📸 รูป", type=["jpg", "jpeg", "png"])

        submit = st.form_submit_button("✅ บันทึก")
        if submit:
            now = datetime.now().replace(microsecond=0)
            image_path = ""
            if image:
                image_path = os.path.join(IMAGE_FOLDER, f"{job_id}.jpg")
                with open(image_path, "wb") as f:
                    f.write(image.read())

            row = [
                now.strftime("%Y-%m-%d %H:%M:%S"),
                job_id, employee, part_code, machine, lot,
                qty_all, qty_ng, qty_pending, total,
                "Sorting MC", "", "", image_path
            ]
            try:
                ws.append_row(row)
                st.success("✅ บันทึกแล้ว")
                send_telegram_message(f"📥 <b>New Sorting</b>\n🆔 <code>{job_id}</code>\n👷 {employee}\n🔩 {part_code}\n📦 Lot: {lot}\n❌ NG: {qty_ng} | ⏳ ยังไม่ตรวจ: {qty_pending}")
            except Exception as e:
                st.error(f"❌ บันทึกลง GSheet ล้มเหลว: {e}")

# 🧾 Waiting Judgement
elif menu == "🧾 Waiting Judgement":
    st.subheader("🧾 รอการตัดสินใจ")
    pw = st.text_input("🔐 รหัสผ่าน", type="password")
    if pw == "Admin1":
        pending = df[df["สถานะ"] == "Sorting MC"]
        for idx, row in pending.iterrows():
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"🆔 {row['Job ID']} - {row['รหัสงาน']} ({row['ชื่อพนักงาน']})")
                st.text(f"❌ {row['จำนวน NG']} | ⏳ {row['จำนวนยังไม่ตรวจ']}")
            with col2:
                if st.button("♻️ Recheck", key=f"rc_{idx}"):
                    ws.update_cell(idx + 2, 11, "Recheck")
                    ws.update_cell(idx + 2, 12, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    send_telegram_message(f"🔁 <b>Recheck</b>: <code>{row['Job ID']}</code>")
                    st.rerun()
            with col3:
                if st.button("🗑 Scrap", key=f"sp_{idx}"):
                    ws.update_cell(idx + 2, 11, "Scrap")
                    ws.update_cell(idx + 2, 12, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    send_telegram_message(f"🗑 <b>Scrap</b>: <code>{row['Job ID']}</code>")
                    st.rerun()

# 💧 Oil Cleaning
elif menu == "💧 Oil Cleaning":
    st.subheader("💧 ล้างงานที่ Recheck")
    jobs = df[df["สถานะ"] == "Recheck"]
    emp_list = emp_df["ชื่อพนักงาน"].dropna().unique()
    operator = st.selectbox("👤 พนักงานล้าง", [""] + list(emp_list))
    for idx, row in jobs.iterrows():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"🆔 {row['Job ID']} - {row['รหัสงาน']} ({row['ชื่อพนักงาน']})\n- 📦 Lot: {row['Lot Number']} | 📊 รวม: {row['จำนวนทั้งหมด']}")
        with col2:
            if st.button("✅ ล้างเสร็จแล้ว", key=f"lav_{idx}"):
                if operator:
                    ws.update_cell(idx + 2, 11, "Lavage")
                    ws.update_cell(idx + 2, 13, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    send_telegram_message(f"💧 <b>ล้างเสร็จแล้ว</b>: <code>{row['Job ID']}</code> โดย {operator}")
                    st.rerun()
                else:
                    st.warning("⚠ กรุณาเลือกชื่อพนักงานก่อนกดปุ่ม")

# 📊 รายงาน
elif menu == "📊 รายงาน":
    st.subheader("📊 รายงานทั้งหมด")
    view = st.selectbox("📆 ช่วงเวลา", ["ทั้งหมด", "รายวัน", "รายสัปดาห์", "รายเดือน", "รายปี"])
    view_df = df.copy()
    now = datetime.now()

    if view == "รายวัน":
        view_df = view_df[view_df["วันที่"].dt.date == now.date()]
    elif view == "รายสัปดาห์":
        view_df = view_df[view_df["วันที่"] >= now - pd.Timedelta(days=7)]
    elif view == "รายเดือน":
        view_df = view_df[view_df["วันที่"].dt.month == now.month]
    elif view == "รายปี":
        view_df = view_df[view_df["วันที่"].dt.year == now.year]

    st.dataframe(view_df)
    scrap_summary = view_df[view_df["สถานะ"] == "Scrap"].groupby("รหัสงาน")["จำนวนทั้งหมด"].sum().reset_index()
    st.markdown("📌 **ยอด Scrap แยกรหัสงาน**")
    st.dataframe(scrap_summary)

# 🛠 Upload Master
elif menu == "🛠 Upload Master":
    st.subheader("🛠 อัปโหลดรายชื่อ / รหัสงาน")
    pw = st.text_input("รหัสผ่าน", type="password")
    if pw == "Sup":
        emp_file = st.file_uploader("👥 พนักงาน", type="xlsx")
        part_file = st.file_uploader("🧾 รหัสงาน", type="xlsx")
        if st.button("📤 บันทึก"):
            if emp_file:
                pd.read_excel(emp_file).to_excel(EMP_PATH, index=False)
            if part_file:
                pd.read_excel(part_file).to_excel(PART_PATH, index=False)
            st.success("✅ บันทึก Master สำเร็จ")
            st.rerun()
