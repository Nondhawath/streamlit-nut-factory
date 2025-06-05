import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from pytz import timezone

# ✅ โหลด credentials จาก secrets
creds_dict = st.secrets["GOOGLE_CREDENTIALS"]

# ✅ ตั้งค่า Scope และเชื่อมต่อ
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
client = gspread.authorize(creds)

# ✅ เชื่อม Google Sheets
SHEET_URL = "https://docs.google.com/spreadsheets/d/1z52GqjoO7NWiuxZNfoZrEcb8Sx_ZkpTa3InwweKXH5w/edit#gid=0"
spreadsheet = client.open_by_url(SHEET_URL)

# ✅ โหลดชีตต่าง ๆ
sheet = spreadsheet.worksheet("Checklist")
machines_sheet = spreadsheet.worksheet("Machines")
emp_sheet = spreadsheet.worksheet("Employees")

# ✅ โหลดข้อมูลเครื่องจักรและพนักงาน
machines_df = pd.DataFrame(machines_sheet.get_all_records())
emp_df = pd.DataFrame(emp_sheet.get_all_records())

# ✅ หัวข้อ Checklist
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

# ✅ UI ฟอร์ม
st.title("📋 แบบฟอร์ม Check Sheet พนักงาน")
now = datetime.now(timezone("Asia/Bangkok"))  # Timestamp GMT+7
st.info(f"🕓 เวลา: {now.strftime('%Y-%m-%d %H:%M:%S')}")

inspector = st.text_input("🧑‍💼 ชื่อผู้ตรวจสอบ")
shift = st.selectbox("🕐 กะ", ["D", "N"])
process = st.selectbox("🧪 กระบวนการ", ["FM", "TP", "FI"])

# ✅ เลือกพนักงาน
emp_names = emp_df["ชื่อพนักงาน"].tolist()
employee = st.selectbox("👷‍♂️ พนักงานที่ตรวจ", emp_names)

# ✅ เลือกเครื่องจักรจาก process
filtered_machines = machines_df[machines_df["Process"] == process]["Machines_Name"].tolist()
machine = st.selectbox("🛠 เลือกเครื่องจักร", filtered_machines) if filtered_machines else ""

st.markdown("---")

# ✅ รายการ Checklist
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
if st.button("📤 บันทึกข้อมูล"):
    if not machine:
        st.error("⚠️ กรุณาเลือกเครื่องจักรก่อนบันทึก")
        st.stop()

    row_data = [
        now.strftime("%Y-%m-%d %H:%M:%S"),
        inspector,
        shift,
        process,
        machine,
        employee
    ]

    for _, result, reason in results:
        if result == "✔️ ผ่าน":
            row_data.append("✅ ผ่าน")
        else:
            row_data.append(f"❌ ไม่ผ่าน เหตุผล: {reason}")

    sheet.append_row(row_data)
    st.success("✅ บันทึกเรียบร้อยแล้ว!")
