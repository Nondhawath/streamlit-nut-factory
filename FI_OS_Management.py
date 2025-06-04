import streamlit as st
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# เวลาไทย
def now_th():
    return datetime.utcnow() + timedelta(hours=7)

# Google Sheets Auth
SCOPE = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(st.secrets["GOOGLE_SHEETS_CREDENTIALS"], scopes=SCOPE)
client = gspread.authorize(creds)

sheet_url = "https://docs.google.com/spreadsheets/d/1op8bQkslCAtRbeW7r3XjGP82kcIv0ox1azrCS2-1fRE"
sheet = client.open_by_url(sheet_url)
worksheet = sheet.worksheet("Data")  # ใช้ชีทชื่อ Data

st.set_page_config(page_title="ระบบ Sorting & ซ่อม", layout="wide")
st.title("📦 ระบบจัดการงาน Sorting & ซ่อม")

# โหลดข้อมูล Google Sheet เป็น DataFrame
@st.cache_data(ttl=60)
def load_data():
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    return df

df = load_data()

# เลือกโหมด
menu = st.sidebar.selectbox("🔍 เลือกโหมด", [
    "1️⃣ รับงานเข้า",
    "2️⃣ รับงานซ่อมกลับ",
    "3️⃣ สรุปประวัติการส่งซ่อม"
])

# โหมด 1: รับงานเข้า
if menu == "1️⃣ รับงานเข้า":
    st.header("📥 รับงานเข้า")
    with st.form("form_receive_job"):
        job_name = st.text_input("📌 ชื่องาน")
        qty_in = st.number_input("📥 จำนวนรับเข้า", min_value=0)
        received_by = st.text_input("👷‍♂️ ผู้รับเข้า")
        qty_ok = st.number_input("✅ จำนวน OK", min_value=0, max_value=qty_in)
        qty_ng = st.number_input("❌ จำนวน NG", min_value=0, max_value=qty_in - qty_ok)
        repair_by = st.text_input("🔧 ส่งซ่อมโดย (ถ้ามี)")
        qty_repair = st.number_input("🔁 จำนวนส่งซ่อม", min_value=0, max_value=qty_ng)
        submitted = st.form_submit_button("✅ บันทึกข้อมูล")

        if submitted:
            row = [
                now_th().strftime("%Y-%m-%d %H:%M:%S"),
                job_name,
                qty_in,
                received_by,
                qty_ok,
                qty_ng,
                repair_by,
                qty_repair,
                "",  # รับกลับซ่อมแล้วโดย (ว่างตอนนี้)
                ""   # เวลาได้รับคืน (ว่างตอนนี้)
            ]
            worksheet.append_row(row)
            st.success("✅ บันทึกข้อมูลเรียบร้อย")

# โหมด 2: รับงานซ่อมกลับ
elif menu == "2️⃣ รับงานซ่อมกลับ":
    st.header("🔄 รับงานที่ส่งซ่อมกลับ")
    if "รับกลับซ่อมแล้วโดย" not in df.columns or "เวลาได้รับคืน" not in df.columns:
        st.error("❌ Google Sheet ต้องมีคอลัมน์ 'รับกลับซ่อมแล้วโดย' และ 'เวลาได้รับคืน'")
    else:
        df_pending = df[(df["ส่งซ่อมโดย"] != "") & ((df["รับกลับซ่อมแล้วโดย"].isna()) | (df["รับกลับซ่อมแล้วโดย"] == ""))]
        if df_pending.empty:
            st.info("📭 ยังไม่มีงานที่รอรับกลับจากซ่อม")
        else:
            options = [
                f"{row['ชื่องาน']} | ส่งซ่อมโดย: {row['ส่งซ่อมโดย']} | จำนวนส่งซ่อม: {row['จำนวนส่งซ่อม']}"
                for idx, row in df_pending.iterrows()
            ]
            selected = st.selectbox("🧾 เลือกงานที่รับกลับจากซ่อม", options)
            selected_idx = df_pending.index[options.index(selected)]

            repair_received_by = st.text_input("👷‍♂️ ผู้รับกลับจากซ่อม")
            if st.button("📥 รับกลับเข้าระบบ"):
                if not repair_received_by:
                    st.warning("กรุณาระบุชื่อผู้รับกลับจากซ่อม")
                else:
                    row_number = selected_idx + 2
                    worksheet.update_cell(row_number, df.columns.get_loc("รับกลับซ่อมแล้วโดย") + 1, repair_received_by)
                    worksheet.update_cell(row_number, df.columns.get_loc("เวลาได้รับคืน") + 1, now_th().strftime("%Y-%m-%d %H:%M:%S"))
                    st.success("✅ บันทึกข้อมูลการรับกลับจากซ่อมเรียบร้อย")
                    st.experimental_rerun()

# โหมด 3: สรุปประวัติการส่งซ่อม
elif menu == "3️⃣ สรุปประวัติการส่งซ่อม":
    st.header("📊 สรุปประวัติการส่งซ่อม")
    if "ส่งซ่อมโดย" not in df.columns or "จำนวนส่งซ่อม" not in df.columns:
        st.error("❌ Google Sheet ต้องมีคอลัมน์ 'ส่งซ่อมโดย' และ 'จำนวนส่งซ่อม'")
    else:
        df_repair = df[df["ส่งซ่อมโดย"] != ""]
        if df_repair.empty:
            st.info("📭 ยังไม่มีประวัติการส่งซ่อม")
        else:
            st.dataframe(df_repair[[
                "วันที่", "ชื่องาน", "จำนวนส่งซ่อม", "ส่งซ่อมโดย", "รับกลับซ่อมแล้วโดย", "เวลาได้รับคืน"
            ]])
            summary = df_repair.groupby("ส่งซ่อมโดย")["จำนวนส่งซ่อม"].sum().reset_index()
            st.markdown("### 📌 สรุปจำนวนส่งซ่อมแยกตามผู้ส่งซ่อม")
            st.dataframe(summary)
