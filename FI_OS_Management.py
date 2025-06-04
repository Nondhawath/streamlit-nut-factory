import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ตั้งค่า scope และเชื่อมต่อ Google Sheets ผ่าน service account
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(st.secrets["GOOGLE_SHEETS_CREDENTIALS"], scopes=SCOPE)
client = gspread.authorize(creds)

# เปิด Google Sheets และ Worksheets
SHEET_KEY = "1op8bQkslCAtRbeW7r3XjGP82kcIv0ox1azrCS2-1fRE"
data_sheet = client.open_by_key(SHEET_KEY).worksheet("Data")
part_code_sheet = client.open_by_key(SHEET_KEY).worksheet("OS_part_code_master")
login_sheet = client.open_by_key(SHEET_KEY).worksheet("ชื่อและรหัสพนักงาน")

# ดึงข้อมูลชื่องานจากชีท OS_part_code_master คอลัมน์ 'รหัสงาน'
job_codes = part_code_sheet.col_values(1)[1:]  # ข้าม header

# ดึงข้อมูลพนักงานจากชีท ชื่อและรหัสพนักงาน
employee_data = login_sheet.get_all_records()
users = {emp["รหัส"]: emp["ชื่อ"] for emp in employee_data}

# ---------------- ระบบ Login ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_name = ""

st.title("🔒 เข้าสู่ระบบ")

if not st.session_state.logged_in:
    user_id = st.text_input("รหัสพนักงาน", type="password")
    if st.button("Login"):
        if user_id in users:
            st.session_state.logged_in = True
            st.session_state.user_name = users[user_id]
            st.success(f"✅ ยินดีต้อนรับคุณ {users[user_id]}")
            st.experimental_rerun()  # โหลดใหม่เพื่อเข้าถึง main app
        else:
            st.error("❌ รหัสไม่ถูกต้อง กรุณาลองใหม่")
    st.stop()

# ---------------- ส่วนหลักของแอป ----------------
st.title("📦 ระบบบันทึกข้อมูลการรับงาน และส่งซ่อม")
st.write(f"ผู้ใช้งาน: {st.session_state.user_name}")

mode = st.sidebar.selectbox("เลือกโหมด", ["รับงานเข้า", "บันทึกงาน OK/NG", "ส่งซ่อม", "สรุปประวัติการส่งซ่อม"])

if mode == "รับงานเข้า":
    job = st.selectbox("เลือกชื่องาน", job_codes)
    qty = st.number_input("จำนวนรับเข้า", min_value=1)
    if st.button("บันทึก"):
        data_sheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            job,
            qty,
            st.session_state.user_name,
            "", "", "", ""
        ])
        st.success("✅ บันทึกข้อมูลรับงานเรียบร้อย")

elif mode == "บันทึกงาน OK/NG":
    job = st.selectbox("เลือกชื่องาน", job_codes)
    ok_qty = st.number_input("จำนวน OK", min_value=0)
    ng_qty = st.number_input("จำนวน NG", min_value=0)
    if st.button("บันทึกผล"):
        data_sheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            job,
            "",
            "",
            ok_qty,
            ng_qty,
            "",
            ""
        ])
        st.success("✅ บันทึกผลการตรวจเรียบร้อย")

elif mode == "ส่งซ่อม":
    job = st.selectbox("เลือกชื่องาน", job_codes)
    qty_repair = st.number_input("จำนวนที่ส่งซ่อม", min_value=1)
    if st.button("บันทึกการส่งซ่อม"):
        data_sheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            job,
            "",
            "",
            "",
            "",
            st.session_state.user_name,
            qty_repair
        ])
        st.success("✅ บันทึกการส่งซ่อมเรียบร้อย")

elif mode == "สรุปประวัติการส่งซ่อม":
    records = data_sheet.get_all_records()
    # กรองเฉพาะแถวที่มีข้อมูลผู้ส่งซ่อม (สมมติคอลัมน์ชื่อ 'ผู้ส่งซ่อม' อยู่ใน column ที่ 7)
    repair_data = [r for r in records if r.get("ผู้ส่งซ่อม")]
    st.dataframe(repair_data)
