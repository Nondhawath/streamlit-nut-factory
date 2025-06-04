import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ใส่ข้อมูล service account credential ของคุณที่นี่ (จากไฟล์ JSON ของ Google)
credentials_json = {
  "type": "service_account",
  "project_id": "upheld-modem-461701-h1",
  "private_key_id": "295195eda574489ba07bdd1fd566c93d9ef6a14a",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCzsF6Z/z7fSs1p\nnRQdMk+DinOHaXyWdETeTz+A9lehFGthFOxPTOQ+Ez0VGFh0IZv9wIAlMAcRD0o0\npgTWH5QYZZjVcWBTAb7Bg7llayu01NBrBB2zZ16WDuDh/2llHqApSADFexowrOuc\n/eAN3C61ZCRo8LUPg1yitZt3oANmx2UA/0jOegWVPbcenmc1NhpAMlc2fQL2HSvU\nNmdEk0Lev26Cmal4FiKy+A+GQDMurKzXk9iUPAb21+/WlXdsyoLWJ194oPBiTljK\nhAsFQ1qwnm9W/ig0+5ODFd/u4Txb8BLURlCCoxK6S186+n+bQIltQUwkBSSlK3Zl\n2HCaw9kbAgMBAAECggEATOeSRZShww2PxsDsx+Ytc94AvhbetMIEa6U9R6OnM5C6\nuG0tCm+dTBgNz4aA7QspaTxHXCMnEx0ZJFldvor7ZkmtVMTWdhBMJSSMZ6SrqxRe\nMz8quwrlx5GMnA0lfZrS73gapGqgde68VI+voh73erjmgGdtBruxHQ5fAJ7idczu\n2UCCflRIhuOlIhPiAMgYtsAoYBY1G71XaF2H281qUWwrHNC8lCscSvBQph6ACCom\nxSl/8SYqlY21SgunV53TOXGcg3nak8Vj/xyN1GLLbW0aXv4uQIkxutHU8RHbN4tn\nquDb6v5HS4ELIiREp0bg5PPAHWr6KtTkDPb59o452QKBgQDqHcCoQidSWUziqtVD\n7d7ypskFQvVxa7NMMrPVH++i1PkxxbIzpR5TAYj6hWectV/TWL0EH4mGTXiRzyo2\ni6HFww1o9PGgh2utQYh8BTRHVxfeTlkY+RXHJt6pMChBYNHlSvwCVrqxeyz/ZI9T\nQxoslaHEmzXhWfqvbyS+QDz3zwKBgQDEfDU85vuA0M7LqBB5Cbb92FxXLcNNXQMo\ngwIwp+Pw8xJEuV1B4kR7Z+b1VDyuU0/7D7CDqKMr/npiYn8lgWqlL+Xy/+9T0cub\nyWB+TG+jxYKWzRPikdBnBjeQFsfWGsqn44OKutCQsKnDcltgXynf/O/mcX+rzFzh\nH2YCYeZQ9QKBgBNyjUJs3F9W07AwiK6v38lAWYp6WXEmhSpbO90EXh+kmV6tEXSA\nztgOVJaa5lR6LI+d23WwOPhTDyTtlJAbYUDQRxjk3/15wlQOEYxb0k/qyCzLTVNp\nvYlhjTV4rp9fr4/gfrajBbcgiEhezhkYheAWPe3bBsrFcrGIBgFXzLi5AoGBAIpT\nTz+S9ZiYaB2kMgSkPDm1ajzNsOL0Clco9A/BAo4M8d2ECg1p+ABRA53PMfEgIfyD\n7SajQEymmQ5OfWiwFZ45fE94ssp1tjv0p4QC182aLPdxZQBq2ybMj61W/FTVA7ry\nRxcRsedLGBjKl13fYSGZdmLroJAYDYNHkY830OdJAoGANi8q2G5U+FTcwAf0psfH\n+VRospXR579GZcNUuSfC1u9bvJ8G6ykAIn9IyMqW3p3erMgycQ5YNOSkvBBiBMkv\npaJUf8xDgaIuECJWLbyKwIK7dKRBhnS27hp2/c2T2PiCB/V8DZ08MMi9IWiPpw34\nWKfBha0hZB72FP1NuzaD4ZU=\n-----END PRIVATE KEY-----\n",
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

# Google Sheets key และชื่อชีท
SPREADSHEET_KEY = "1op8bQkslCAtRbeW7r3XjGP82kcIv0ox1azrCS2-1fRE"
data_sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("OSmanagementdata")
part_code_sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("OS_part_code_master")
user_sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("ชื่อและรหัสพนักงาน")

# โหลดข้อมูล
job_codes = part_code_sheet.col_values(1)[1:]  # ข้าม header
user_data_raw = user_sheet.get_all_records()
user_dict = {str(row["รหัส"]): row["ชื่อ"] for row in user_data_raw}

# เริ่มแอป
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
