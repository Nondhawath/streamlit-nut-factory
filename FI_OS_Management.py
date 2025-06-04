import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

# ตั้งค่า credentials และเชื่อมต่อ Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["GOOGLE_SHEETS_CREDENTIALS"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Spreadsheet key
SPREADSHEET_KEY = "1op8bQkslCAtRbeW7r3XjGP82kcIv0ox1azrCS2-1fRE"

# โหลด worksheets
data_sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("Data")
login_sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("ชื่อและรหัสพนักงาน")
part_code_sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("OS_part_code_master")

# โหลดข้อมูลสำหรับ login
login_data = login_sheet.get_all_records()
users = {str(row['รหัส']): row['ชื่อ'] for row in login_data}

# โหลดรหัสงาน
job_codes = part_code_sheet.col_values(1)[1:]

# สร้าง session state สำหรับ login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""

# --- หน้า Login ---
if not st.session_state.logged_in:
    st.title("🔒 เข้าสู่ระบบ")
    emp_id = st.text_input("รหัสพนักงาน", type="password")

    if st.button("เข้าสู่ระบบ"):
        if emp_id in users:
            st.session_state.logged_in = True
            st.session_state.username = users[emp_id]
            st.success(f"✅ ยินดีต้อนรับคุณ {users[emp_id]}")
            st.experimental_rerun()
        else:
            st.error("❌ รหัสไม่ถูกต้อง กรุณาลองใหม่")
    st.stop()

# --- โหมดหลัก ---
st.title("📋 ระบบจัดการ OS")

mode = st.selectbox("เลือกโหมด", ["รับงานเข้า / บันทึก OK-NG", "รับงานซ่อมเข้า"])

if mode == "รับงานเข้า / บันทึก OK-NG":
    st.subheader("🛠 รับงานใหม่ หรือบันทึกผล OK/NG")

    job_code = st.selectbox("เลือกรหัสงาน", job_codes)
    quantity = st.number_input("จำนวนงาน", min_value=1, step=1)
    result = st.radio("สถานะงาน", ["OK", "NG"])
    remark = st.text_input("หมายเหตุเพิ่มเติม (ถ้ามี)")
    if st.button("บันทึกข้อมูล"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        job_id = f"{job_code}-{int(datetime.now().timestamp())}"
        new_row = [timestamp, st.session_state.username, job_code, quantity, result, remark, job_id, "รับงาน"]
        data_sheet.append_row(new_row)
        st.success(f"✅ บันทึกข้อมูลแล้ว | Job ID: {job_id}")

elif mode == "รับงานซ่อมเข้า":
    st.subheader("🔧 รับงานซ่อมกลับเข้า")

    job_id_input = st.text_input("กรุณาใส่ Job ID ของงานซ่อมที่ส่งออกไป")

    if job_id_input:
        records = data_sheet.get_all_records()
        matched_job = None
        for row in records:
            if str(row.get("Job ID", "")).strip() == job_id_input.strip() and row.get("สถานะ", "") == "ส่งงานซ่อม":
                matched_job = row
                break

        if matched_job:
            st.markdown(f"""
                ✅ พบข้อมูล Job ID:
                - ชื่อผู้ส่ง: **{matched_job['ชื่อผู้ใช้']}**
                - รหัสงาน: **{matched_job['รหัสงาน']}**
                - จำนวน: **{matched_job['จำนวน']}**
                - หมายเหตุ: _{matched_job['หมายเหตุ']}_""")

            remark = st.text_input("หมายเหตุเพิ่มเติม (ถ้ามี)", key="repair_remark")

            if st.button("บันทึกการรับงานซ่อมกลับเข้า"):
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_row = [timestamp, st.session_state.username, matched_job['รหัสงาน'], matched_job['จำนวน'], "รับซ่อมเข้า", remark, job_id_input, "รับงานซ่อมเข้า"]
                data_sheet.append_row(new_row)
                st.success(f"✅ รับงานซ่อมกลับเข้าเรียบร้อยแล้ว | Job ID: {job_id_input}")
        else:
            st.error("❌ ไม่พบ Job ID ที่เคยส่งงานซ่อม หรือสถานะไม่ถูกต้อง")
