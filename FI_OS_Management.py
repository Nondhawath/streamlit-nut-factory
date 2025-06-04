import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Service Account credentials (JSON) จาก Google Cloud Console
credentials_json = {
  "type": "service_account",
  "project_id": "upheld-modem-461701-h1",
  "private_key_id": "295195eda574489ba07bdd1fd566c93d9ef6a14a",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCzsF6Z/z7fSs1p\n..."
                 "-----END PRIVATE KEY-----\n",
  "client_email": "sorting-service@upheld-modem-461701-h1.iam.gserviceaccount.com",
  "client_id": "103066540725350718650",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/sorting-service%40upheld-modem-461701-h1.iam.gserviceaccount.com"
}

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_json, scope)
client = gspread.authorize(credentials)

# Google Sheets key และ worksheet
SPREADSHEET_KEY = "1op8bQkslCAtRbeW7r3XjGP82kcIv0ox1azrCS2-1fRE"
data_sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("OSmanagementdata")
part_code_sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("OS_part_code_master")
user_sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("ชื่อและรหัสพนักงาน")

# โหลดข้อมูลรหัสงานและข้อมูลผู้ใช้
job_codes = part_code_sheet.col_values(1)[1:]  # ข้าม header
user_data_raw = user_sheet.get_all_records()
user_dict = {str(row["รหัส"]): row["ชื่อ"] for row in user_data_raw}

# ตั้งค่า Streamlit app
st.set_page_config(page_title="FI_OS_Management", layout="centered")

# ตรวจสอบสถานะ login ใน session
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""

# หน้า login
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
            job_id = f"{job_code}-{int(datetime.now().timestamp())}"  # สร้าง Job ID ไม่ซ้ำ

            # บันทึกงาน OK
            if ok_qty > 0:
                data_sheet.append_row([timestamp, st.session_state.username, job_code, ok_qty, "OK", remark, job_id, "รับงาน"])
            # บันทึกงาน NG
            if ng_qty > 0:
                data_sheet.append_row([timestamp, st.session_state.username, job_code, ng_qty, "NG", remark, job_id, "รับงาน"])

            st.success(f"✅ บันทึกข้อมูลแล้ว | Job ID: {job_id}")
