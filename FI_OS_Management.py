import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd
import json

# โหลด credentials จาก secrets
creds_dict = st.secrets["GOOGLE_SHEETS_CREDENTIALS"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(
    creds_dict,
    ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets"]
)
client = gspread.authorize(credentials)

# Key ของ Google Sheet
SPREADSHEET_KEY = "1op8bQkslCAtRbeW7r3XjGP82kcIv0ox1azrCS2-1fRE"

# Load worksheets
try:
    data_sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("Data")
    user_sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("ชื่อและรหัสพนักงาน")
    part_code_sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("OS_part_code_master")
except Exception as e:
    st.error(f"ไม่สามารถโหลดข้อมูลจาก Google Sheets ได้: {e}")
    st.stop()

# โหลดข้อมูลผู้ใช้
user_data = user_sheet.get_all_records()
user_dict = {str(row["รหัส"]): row["ชื่อ"] for row in user_data if row.get("รหัส") and row.get("ชื่อ")}

# โหลดรหัสงาน
try:
    job_codes = part_code_sheet.col_values(1)[1:]  # ข้าม header
except Exception as e:
    st.error(f"ไม่สามารถโหลดรหัสงานได้: {e}")
    st.stop()

# ------------------- UI -------------------
if "user_name" not in st.session_state:
    st.title("🔒 เข้าสู่ระบบ")
    user_code = st.text_input("รหัสพนักงาน", type="password")
    if st.button("เข้าสู่ระบบ"):
        if user_code in user_dict:
            st.session_state.user_name = user_dict[user_code]
            st.experimental_rerun()
        else:
            st.error("❌ รหัสไม่ถูกต้อง กรุณาลองใหม่")
    st.stop()

# ------------------- หน้าหลัก -------------------
st.title(f"✅ ยินดีต้อนรับคุณ {st.session_state.user_name}")

mode = st.radio("เลือกโหมดการทำงาน", ["รับงานเข้า", "บันทึกงาน OK/NG"])

selected_job = st.selectbox("เลือกรหัสงาน", job_codes)
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if mode == "รับงานเข้า":
    qty_in = st.number_input("จำนวนที่รับเข้า", min_value=1, step=1)
    if st.button("📥 บันทึกงานเข้า"):
        data_sheet.append_row([now, st.session_state.user_name, selected_job, "รับงานเข้า", qty_in, "", ""])
        st.success("✅ บันทึกข้อมูลเรียบร้อยแล้ว")

elif mode == "บันทึกงาน OK/NG":
    qty_ok = st.number_input("จำนวน OK", min_value=0, step=1)
    qty_ng = st.number_input("จำนวน NG", min_value=0, step=1)
    if st.button("📝 บันทึกผลการตรวจสอบ"):
        data_sheet.append_row([now, st.session_state.user_name, selected_job, "บันทึกงาน OK/NG", "", qty_ok, qty_ng])
        st.success("✅ บันทึกข้อมูลเรียบร้อยแล้ว")
