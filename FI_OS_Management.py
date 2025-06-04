import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# กำหนด scope สำหรับ Google Sheets และ Drive
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# โหลดไฟล์ credentials.json จากเครื่อง (ต้องอยู่ใน folder เดียวกันกับไฟล์นี้)
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(credentials)

# Google Sheets key และชื่อชีท
SPREADSHEET_KEY = "1op8bQkslCAtRbeW7r3XjGP82kcIv0ox1azrCS2-1fRE"
data_sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("OSmanagementdata")
part_code_sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("OS_part_code_master")
user_sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("ชื่อและรหัสพนักงาน")

# โหลดข้อมูลรหัสงาน และข้อมูลพนักงาน
job_codes = part_code_sheet.col_values(1)[1:]  # ข้าม header
user_data_raw = user_sheet.get_all_records()
user_dict = {str(row["รหัส"]): row["ชื่อ"] for row in user_data_raw}

# เริ่มแอป Streamlit
st.set_page_config(page_title="FI_OS_Management", layout="centered")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""

if not st.session_state.authenticated:
    st.header("🔒 เข้าสู่ระบบ")
    user_code = st.text_input("รหัสพนักงาน", type="password")

    if st.button("เข้าสู่ระบบ"):
        if user_code in user_dict:
            st.session_state.authenticated = True
            st.session_state.username = user_dict[user_code]
            st.experimental_rerun()
        else:
            st.error("❌ รหัสไม่ถูกต้อง กรุณาลองใหม่")
else:
    st.success(f"✅ ยินดีต้อนรับคุณ {st.session_state.username}")
    st.header("📋 รับงานเข้า / บันทึกงาน OK-NG")

    job_code = st.selectbox("เลือกรหัสงาน", job_codes)
    ok_qty = st.number_input("จำนวนงาน OK", min_value=0, step=1)
    ng_qty = st.number_input("จำนวนงาน NG", min_value=0, step=1)
    total_qty = ok_qty + ng_qty
    st.markdown(f"**รวมทั้งหมด: {total_qty} ชิ้น**")

    remark = st.text_input("หมายเหตุเพิ่มเติม (ถ้ามี)")

    if st.button("บันทึกข้อมูล"):
        if total_qty == 0:
            st.warning("⚠️ กรุณากรอกจำนวน OK หรือ NG อย่างน้อยหนึ่งค่า")
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            job_id = f"{job_code}-{int(datetime.now().timestamp())}"

            if ok_qty > 0:
                data_sheet.append_row([timestamp, st.session_state.username, job_code, ok_qty, "OK", remark, job_id, "รับงาน"])
            if ng_qty > 0:
                data_sheet.append_row([timestamp, st.session_state.username, job_code, ng_qty, "NG", remark, job_id, "รับงาน"])

            st.success(f"✅ บันทึกข้อมูลแล้ว | Job ID: {job_id}")
