# 📦 Import Library
from datetime import datetime
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials
import gspread

# 🌐 เชื่อมต่อ Google Sheet
SCOPE = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(
    st.secrets["GOOGLE_SHEETS_CREDENTIALS"], scopes=SCOPE
)
client = gspread.authorize(creds)

# 🔗 ลิงก์ Google Sheet และ worksheet
SHEET_URL = "https://docs.google.com/spreadsheets/d/1GM-es30UBsqFCxBVQbBxht6IntIkL6troc5c2PWD3JA/edit?usp=sharing"
sheet = client.open_by_url(SHEET_URL)
worksheet = sheet.worksheet("Data")  # จำเป็นต้องมี worksheet ชื่อ "Data"

# 📁 โหลด employee_master และ part_code_master
try:
    emp_master = sheet.worksheet("employee_master").col_values(1)[1:]
except:
    emp_master = []

try:
    part_master = sheet.worksheet("part_code_master").col_values(1)[1:]
except:
    part_master = []

# 🆔 สร้าง Job ID อัตโนมัติ
def generate_job_id():
    records = worksheet.get_all_records()
    prefix = datetime.now().strftime("%y%m")
    filtered = [r for r in records if str(r.get("Job ID", "")).startswith(prefix)]
    last = max([int(r["Job ID"][-4:]) for r in filtered if str(r["Job ID"][-4:]).isdigit()], default=0)
    return f"{prefix}{last + 1:04d}"

# 🌐 ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="Sorting Process", layout="wide")
st.title("🔧 ระบบบันทึกข้อมูล Sorting Process - SCS")
menu = st.sidebar.selectbox("📌 เลือกโหมด", [
    "📥 Sorting MC", "🧾 Waiting Judgement", "💧 Oil Cleaning", "📊 รายงาน", "🛠 Upload Master"
])

# 📥 โหมด 1: Sorting MC
if menu == "📥 Sorting MC":
    st.subheader("📥 กรอกข้อมูล Sorting")
    with st.form("sorting_form"):
        job_id = generate_job_id()
        st.markdown(f"🆔 Job ID: `{job_id}`")
        employee = st.selectbox("👷‍♂️ พนักงาน", emp_master)
        part_code = st.selectbox("🔩 รหัสงาน", part_master)
        machine = st.selectbox("🛠 เครื่อง", [f"SM{i:02}" for i in range(1, 31)])
        lot = st.text_input("📦 Lot Number")
        qty_checked = st.number_input("✅ ตรวจทั้งหมด", min_value=0)
        qty_ng = st.number_input("❌ NG", min_value=0)
        qty_pending = st.number_input("⏳ ยังไม่ตรวจ", min_value=0)
        total = qty_ng + qty_pending
        submitted = st.form_submit_button("✅ บันทึก")

        if submitted:
            worksheet.append_row([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"), job_id, employee, part_code, machine,
                lot, qty_checked, qty_ng, qty_pending, total,
                "Sorting MC", "", "", ""
            ])
            st.success("✅ บันทึกสำเร็จ")

# 🧾 โหมด 2: Waiting Judgement
elif menu == "🧾 Waiting Judgement":
    if st.text_input("🔐 รหัสผ่าน (Admin1)", type="password") == "Admin1":
        df = pd.DataFrame(worksheet.get_all_records())
        df = df[df["สถานะ"] == "Sorting MC"]
        st.subheader("📋 ตัดสินใจ (Recheck/Scrap)")
        for idx, row in df.iterrows():
            st.markdown(f"🆔 <b>{row['Job ID']}</b> | {row['รหัสงาน']} | NG: {row['จำนวน NG']} | ยังไม่ตรวจ: {row['จำนวนยังไม่ตรวจ']}", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            if col1.button(f"♻️ Recheck - {row['Job ID']}"):
                worksheet.update_cell(idx + 2, 11, "Recheck")
                worksheet.update_cell(idx + 2, 12, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                st.rerun()
            if col2.button(f"🗑 Scrap - {row['Job ID']}"):
                worksheet.update_cell(idx + 2, 11, "Scrap")
                worksheet.update_cell(idx + 2, 12, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                st.rerun()
    else:
        st.warning("🔒 กรุณาใส่รหัสผ่านให้ถูกต้อง")

# 💧 โหมด 3: Oil Cleaning
elif menu == "💧 Oil Cleaning":
    st.subheader("💧 งานรอล้าง")
    df = pd.DataFrame(worksheet.get_all_records())
    df = df[df["สถานะ"] == "Recheck"]
    cleaner = st.selectbox("👷‍♀️ ผู้ล้าง", emp_master)
    for idx, row in df.iterrows():
        st.markdown(f"🆔 <b>{row['Job ID']}</b> | {row['รหัสงาน']} | ทั้งหมด: {row['จำนวนทั้งหมด']}", unsafe_allow_html=True)
        if st.button(f"✅ ล้างเสร็จแล้ว - {row['Job ID']}"):
            worksheet.update_cell(idx + 2, 11, "Lavage")
            worksheet.update_cell(idx + 2, 13, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            worksheet.update_cell(idx + 2, 14, cleaner)
            st.rerun()

# 📊 โหมด 4: รายงาน
elif menu == "📊 รายงาน":
    df = pd.DataFrame(worksheet.get_all_records())
    df["วันที่"] = pd.to_datetime(df["วันที่"], errors="coerce")
    filter_mode = st.selectbox("📆 เลือกช่วงเวลา", ["ทั้งหมด", "รายวัน", "รายสัปดาห์", "รายเดือน", "รายปี"])
    now = datetime.now()

    if filter_mode == "รายวัน":
        df = df[df["วันที่"].dt.date == now.date()]
    elif filter_mode == "รายสัปดาห์":
        df = df[df["วันที่"] >= now - pd.Timedelta(days=7)]
    elif filter_mode == "รายเดือน":
        df = df[df["วันที่"].dt.month == now.month]
    elif filter_mode == "รายปี":
        df = df[df["วันที่"].dt.year == now.year]

    st.dataframe(df)
    scrap_summary = df[df["สถานะ"] == "Scrap"].groupby("รหัสงาน")["จำนวนทั้งหมด"].sum().reset_index()
    st.markdown("📌 สรุป Scrap แยกตามรหัสงาน")
    st.dataframe(scrap_summary)

# 🛠 โหมด 5: Upload Master
elif menu == "🛠 Upload Master":
    if st.text_input("🔐 รหัส Sup", type="password") == "Sup":
        st.subheader("🛠 อัปโหลด Master")
        emp_txt = st.text_area("👷 รายชื่อพนักงาน (คั่นด้วย Enter)")
        part_txt = st.text_area("🔩 รหัสงาน (คั่นด้วย Enter)")
        if st.button("📤 อัปโหลด"):
            if emp_txt:
                emp_values = [[e] for e in emp_txt.strip().split("\n") if e.strip()]
                sheet.values_update("employee_master!A1", {"valueInputOption": "RAW"}, {"values": [["ชื่อพนักงาน"]] + emp_values})
            if part_txt:
                part_values = [[p] for p in part_txt.strip().split("\n") if p.strip()]
                sheet.values_update("part_code_master!A1", {"valueInputOption": "RAW"}, {"values": [["รหัสงาน"]] + part_values})
            st.success("✅ อัปโหลดสำเร็จ")
            st.rerun()
