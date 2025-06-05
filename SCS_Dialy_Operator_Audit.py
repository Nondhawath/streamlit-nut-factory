import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ✅ โหลด credentials จาก secrets (แบบ dict)
creds_dict = st.secrets["GOOGLE_CREDENTIALS"]

# ✅ สร้าง Credentials object
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
client = gspread.authorize(creds)

# ✅ เชื่อม Google Sheet
SHEET_URL = "https://docs.google.com/spreadsheets/d/1z52GqjoO7NWiuxZNfoZrEcb8Sx_ZkpTa3InwweKXH5w/edit#gid=0"
spreadsheet = client.open_by_url(SHEET_URL)
sheet = spreadsheet.worksheet("Checklist")

# ✅ Checklist
checklist = [
    "1.1 สวมใส่ PPE ครบถ้วนและถูกต้อง",
    "1.2 ทวนสอบความพร้อมของพนักงาน (ไม่เจ็บป่วย)",
    "1.3 เตรียมเอกสารและอุปกรณ์ตรงกับรุ่น",
    "1.4 เตรียม Box แดง / ถุง NG / Tag NG",
    "1.5 ตรวจสอบ Daily PM: Jig, Pokayoke, Guage GO/NO GO",
    "1.6 บันทึกหลังการตรวจสอบ, Lot ชิ้นงาน",
    "1.7 ตรวจสอบคุณภาพชิ้นงานตาม WI, OPS",
    "1.8 ความปลอดภัยในพื้นที่ทำงาน",
    "1.9 ความเหมาะสมของแสงสว่าง",
    "1.10 ความสะอาด / ขยะ / Box อยู่ที่กำหนด",
    "1.11 ไม่มี Part ตกค้าง / รับข้อเสนอแนะพนักงาน"
]

fail_reasons = ["ลืมปฏิบัติ", "ไม่มีอุปกรณ์", "ขาดความเข้าใจ", "อื่น ๆ"]

# ✅ UI แบบฟอร์ม
st.title("📋 แบบฟอร์ม Check Sheet พนักงาน")
date = st.date_input("📅 วันที่", value=datetime.today())
inspector = st.text_input("🧑‍💼 ชื่อผู้ตรวจสอบ")
shift = st.selectbox("🕐 กะ", ["D", "N"])
process = st.selectbox("🧪 กระบวนการ", ["FM", "TP", "FI"])

st.markdown("---")

results = []
for item in checklist:
    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown(f"**{item}**")
    with col2:
        result = st.radio("ผล", ["✔️ ผ่าน", "❌ ไม่ผ่าน"], key=item)
        reason = st.selectbox("เหตุผล", fail_reasons, key=f"{item}_reason") if result == "❌ ไม่ผ่าน" else ""
        results.append((item, result, reason))

# ✅ ปุ่มบันทึก
if st.button("📤 บันทึกลง Google Sheets"):
    for item, result, reason in results:
        sheet.append_row([
            date.strftime("%Y-%m-%d"),
            inspector,
            shift,
            process,
            item,
            "ผ่าน" if result == "✔️ ผ่าน" else "ไม่ผ่าน",
            reason
        ])
    st.success("✅ บันทึกเรียบร้อยแล้ว!")
