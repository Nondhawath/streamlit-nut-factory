import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from pytz import timezone

# ✅ โหลด credentials จาก secrets
creds_dict = st.secrets["GOOGLE_CREDENTIALS"]

# ✅ เชื่อมต่อ Google Sheets
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
client = gspread.authorize(creds)

# ✅ เปิด Spreadsheet
SHEET_URL = "https://docs.google.com/spreadsheets/d/1z52GqjoO7NWiuxZNfoZrEcb8Sx_ZkpTa3InwweKXH5w/edit#gid=0"
spreadsheet = client.open_by_url(SHEET_URL)

sheet = spreadsheet.worksheet("Checklist")
machines_sheet = spreadsheet.worksheet("Machines")
emp_sheet = spreadsheet.worksheet("Employees")
reason_audit_sheet = spreadsheet.worksheet("Reason_Audit")  # ดึง Reason_Audit

# ✅ โหลดข้อมูลเครื่องจักรและพนักงาน
machines_df = pd.DataFrame(machines_sheet.get_all_records())
emp_df = pd.DataFrame(emp_sheet.get_all_records())

# ✅ ดึงข้อมูล Reason จากชีท Reason_Audit
reason_data = reason_audit_sheet.get_all_records()
checklist = [row["Reason"] for row in reason_data if "Reason" in row]  # คัดเลือกเฉพาะคอลัมน์ Reason

fail_reasons = ["ลืมปฏิบัติ", "ไม่มีอุปกรณ์", "ขาดความเข้าใจ", "อื่น ๆ"]

# ✅ ฟอร์ม
st.title("📋 แบบฟอร์ม Audit พนักงาน")
now = datetime.now(timezone("Asia/Bangkok"))
st.info(f"🕓 เวลา: {now.strftime('%Y-%m-%d %H:%M:%S')}")

inspector = st.text_input("🧑‍💼 ชื่อผู้ตรวจสอบ")
shift = st.selectbox("🕐 กะ", ["D", "N"])
process = st.selectbox("🧪 กระบวนการ", ["FM", "TP", "FI"])

# ✅ พนักงาน
emp_names = emp_df["ชื่อพนักงาน"].tolist()
employee = st.selectbox("👷‍♂️ พนักงานที่รับการตรวจสอบ", emp_names)

# ✅ เครื่องจักร
filtered_machines = machines_df[machines_df["Process"] == process]["Machines_Name"].tolist()
machine = st.selectbox("🛠 เลือกเครื่องจักร", filtered_machines) if filtered_machines else ""

st.write("---")  # ใช้ st.write แทน st.markdown

# ✅ Checklist
results = []
for item in checklist:
    col1, col2 = st.columns([3, 2])
    with col1:
        st.write(f"{item}")  # ใช้ st.write แทน st.markdown (ไม่ใช้ **)
    with col2:
        result = st.radio("ผล", ["✔️ ผ่าน", "❌ ไม่ผ่าน"], key=item)
        if result == "❌ ไม่ผ่าน":
            selected_reason = st.selectbox("เหตุผล", fail_reasons, key=f"{item}_reason")
            if selected_reason == "อื่น ๆ":
                custom_reason = st.text_input("กรุณาระบุเหตุผล", key=f"{item}_custom_reason")
                reason = f"อื่น ๆ: {custom_reason}" if custom_reason else "อื่น ๆ"
            else:
                reason = selected_reason
        else:
            reason = ""
        results.append((item, result, reason))

# ✅ บันทึกแนวนอน
if st.button("📤 บันทึกลง Google Sheets"):
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
