import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ตั้งค่า credentials สำหรับ Google Sheets
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_info(st.secrets["GOOGLE_SHEETS_CREDENTIALS"], scopes=SCOPE)
client = gspread.authorize(creds)

# เปิดชีทต่าง ๆ
SPREADSHEET_KEY = "1op8bQkslCAtRbeW7r3XjGP82kcIv0ox1azrCS2-1fRE"
data_sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("Data")
part_code_sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("OS_part_code_master")
login_sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("ชื่อและรหัสพนักงาน")

# ดึงรหัสงาน (สมมติชื่อรหัสงานอยู่คอลัมน์แรกของ OS_part_code_master)
job_codes = part_code_sheet.col_values(1)[1:]  # ข้าม header

# ดึงข้อมูล user/pass จากชีท login
employee_data = login_sheet.get_all_records()
users = {emp["รหัส"]: emp["ชื่อ"] for emp in employee_data}

# -------------- ระบบ Login ---------------- #
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
            st.experimental_rerun()  # รีเฟรชหน้าเพื่อล็อกอินสำเร็จ
        else:
            st.error("❌ รหัสไม่ถูกต้อง กรุณาลองใหม่")
    st.stop()

# ----------- หน้าแอปหลัก ------------- #
st.title("📦 ระบบบันทึกข้อมูลการรับงานและส่งซ่อม")

mode = st.sidebar.selectbox("เลือกโหมดการทำงาน", [
    "รับงานและบันทึก OK/NG",
    "ส่งซ่อม",
    "สรุปประวัติการส่งซ่อม"
])

if mode == "รับงานและบันทึก OK/NG":
    job = st.selectbox("เลือกชื่องาน", job_codes)
    qty_in = st.number_input("จำนวนรับเข้า", min_value=0, step=1)
    ok_qty = st.number_input("จำนวน OK", min_value=0, step=1)
    ng_qty = st.number_input("จำนวน NG", min_value=0, step=1)

    if st.button("บันทึกข้อมูล"):
        data_sheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # Timestamp
            job,                       # ชื่องาน / รหัสงาน
            qty_in if qty_in > 0 else "",       # จำนวนรับเข้า
            st.session_state.user_name,          # คนรับงาน
            ok_qty if ok_qty > 0 else "",        # จำนวน OK
            ng_qty if ng_qty > 0 else "",        # จำนวน NG
            "", "", ""                           # เว้นช่องอื่นว่าง
        ])
        st.success("✅ บันทึกข้อมูลเรียบร้อยแล้ว")

elif mode == "ส่งซ่อม":
    job = st.selectbox("เลือกชื่องาน", job_codes)
    qty_repair = st.number_input("จำนวนที่ส่งซ่อม", min_value=1, step=1)
    if st.button("บันทึกการส่งซ่อม"):
        data_sheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            job, "", "", "", "", st.session_state.user_name, qty_repair, ""
        ])
        st.success("✅ บันทึกการส่งซ่อมเรียบร้อย")

elif mode == "สรุปประวัติการส่งซ่อม":
    records = data_sheet.get_all_records()
    repair_data = [r for r in records if r.get("ผู้ส่งซ่อม")]
    st.dataframe(repair_data)
