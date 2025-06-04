import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ตั้งค่า credentials
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["GOOGLE_SHEETS_CREDENTIALS"], scopes=SCOPE)
client = gspread.authorize(creds)

# เปิดชีทต่าง ๆ
SPREADSHEET_KEY = "1op8bQkslCAtRbeW7r3XjGP82kcIv0ox1azrCS2-1fRE"
data_sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("Data")
part_code_sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("OS_part_code_master")
login_sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("ชื่อและรหัสพนักงาน")

# ดึงรหัสงาน (สมมติชื่อคอลัมน์ใน OS_part_code_master เป็น 'รหัสงาน')
job_codes = part_code_sheet.col_values(1)[1:]  # ข้าม header

# ดึง user/pass จาก sheet ชื่อและรหัสพนักงาน
employee_data = login_sheet.get_all_records()
users = {str(emp["รหัส"]).strip(): emp["ชื่อ"].strip() for emp in employee_data}

# ---------------- LOGIN ---------------- #
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_name = ""

st.title("🔒 เข้าสู่ระบบ")

if not st.session_state.logged_in:
    user_id = st.text_input("รหัสพนักงาน", type="password").strip()
    if st.button("Login"):
        if user_id in users:
            st.session_state.logged_in = True
            st.session_state.user_name = users[user_id]
            st.success(f"✅ ยินดีต้อนรับคุณ {users[user_id]}")
            st.experimental_rerun()
        else:
            st.error("❌ รหัสไม่ถูกต้อง กรุณาลองใหม่")
    st.stop()

# ---------------- MAIN APP ---------------- #
st.title("📦 ระบบบันทึกข้อมูลการรับงาน และส่งซ่อม")

mode = st.sidebar.selectbox("โหมด", ["รับและบันทึกงาน OK/NG", "ส่งซ่อม", "สรุปประวัติการส่งซ่อม"])

if mode == "รับและบันทึกงาน OK/NG":
    job = st.selectbox("เลือกชื่องาน", job_codes)
    qty_in = st.number_input("จำนวนรับเข้า", min_value=0)
    ok_qty = st.number_input("จำนวน OK", min_value=0)
    ng_qty = st.number_input("จำนวน NG", min_value=0)
    if st.button("บันทึกข้อมูล"):
        # เก็บข้อมูล row: Timestamp, งาน, จำนวนรับเข้า, ผู้รับเข้า, จำนวน OK, จำนวน NG, ผู้ส่งซ่อม, จำนวนส่งซ่อม
        data_sheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            job,
            qty_in,
            st.session_state.user_name,
            ok_qty,
            ng_qty,
            "",
            ""
        ])
        st.success("✅ บันทึกข้อมูลเรียบร้อยแล้ว")

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
    repair_data = [r for r in records if r.get("ผู้ส่งซ่อม")]
    st.dataframe(repair_data)
