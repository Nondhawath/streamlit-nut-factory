# 📦 Import Library
from datetime import datetime
import os
import pandas as pd
import streamlit as st
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials

# 📌 เชื่อมต่อ Google Sheets
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["GOOGLE_SHEETS_CREDENTIALS"], scopes=SCOPE)
client = gspread.authorize(creds)

SHEET_URL = "https://docs.google.com/spreadsheets/d/1GM-es30UBsqFCxBVQbBxht6IntIkL6troc5c2PWD3JA/edit?usp=sharing"
sheet = client.open_by_url(SHEET_URL)
worksheet = sheet.worksheet("Data")  # โปรดสร้างแท็บชื่อ "Data" ใน Google Sheets

# 📁 เตรียมรายชื่อ Master
try:
    emp_master = sheet.worksheet("employee_master").col_values(1)[1:]
except:
    emp_master = []
try:
    part_master = sheet.worksheet("part_code_master").col_values(1)[1:]
except:
    part_master = []

# 📌 สร้าง Job ID อัตโนมัติ
def generate_job_id():
    records = worksheet.get_all_records()
    now = datetime.now()
    prefix = now.strftime("%y%m")
    filtered = [row for row in records if str(row.get("Job ID", "")).startswith(prefix)]
    if filtered:
        last_seq = max([int(r["Job ID"][-4:]) for r in filtered if r["Job ID"][-4:].isdigit()])
    else:
        last_seq = 0
    return f"{prefix}{last_seq + 1:04d}"

# 🌐 UI
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
        st.markdown(f"**🆔 Job ID:** `{job_id}`")
        employee = st.selectbox("👷‍♂️ เลือกชื่อพนักงาน", emp_master)
        part_code = st.selectbox("🔩 เลือกรหัสงาน", part_master)
        machine = st.selectbox("🛠 เลือกชื่อเครื่อง", [f"SM{i:02}" for i in range(1, 31)])
        lot_number = st.text_input("📦 Lot Number")
        qty_checked = st.number_input("🔍 จำนวนที่ตรวจสอบทั้งหมดของ Lot", min_value=0)
        qty_ng = st.number_input("❌ จำนวน NG", min_value=0)
        qty_pending = st.number_input("⏳ จำนวนที่ยังไม่ตรวจ", min_value=0)
        total = qty_ng + qty_pending
        submitted = st.form_submit_button("✅ บันทึกข้อมูล")

        if submitted:
            new_row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"), job_id, employee, part_code,
                machine, lot_number, qty_checked, qty_ng, qty_pending, total,
                "Sorting MC", "", "", ""
            ]
            worksheet.append_row(new_row)
            st.success("✅ บันทึกข้อมูลเรียบร้อยแล้ว")

# 🧾 โหมด 2: Waiting Judgement
elif menu == "🧾 Waiting Judgement":
    password = st.text_input("🔐 รหัสผ่าน (Admin1)", type="password")
    if password == "Admin1":
        df = pd.DataFrame(worksheet.get_all_records())
        df = df[df["สถานะ"] == "Sorting MC"]
        st.subheader("🔍 เลือกตัดสินใจ (Recheck / Scrap)")
        for idx, row in df.iterrows():
            st.markdown(f"🆔 <b>{row['Job ID']}</b> | รหัส: {row['รหัสงาน']} | NG: {row['จำนวน NG']} | ยังไม่ตรวจ: {row['จำนวนยังไม่ตรวจ']}", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"♻️ Recheck - {row['Job ID']}"):
                    worksheet.update_cell(idx + 2, 11, "Recheck")
                    worksheet.update_cell(idx + 2, 12, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    st.rerun()
            with col2:
                if st.button(f"🗑 Scrap - {row['Job ID']}"):
                    worksheet.update_cell(idx + 2, 11, "Scrap")
                    worksheet.update_cell(idx + 2, 12, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    st.rerun()
    else:
        st.warning("🔒 กรุณาใส่รหัสผ่าน")

# 💧 โหมด 3: Oil Cleaning
elif menu == "💧 Oil Cleaning":
    st.subheader("💧 งานที่รอการล้าง")
    df = pd.DataFrame(worksheet.get_all_records())
    df = df[df["สถานะ"] == "Recheck"]
    employee_done = st.selectbox("👷‍♂️ ผู้ล้าง:", emp_master)
    for idx, row in df.iterrows():
        st.markdown(f"🆔 <b>{row['Job ID']}</b> | {row['รหัสงาน']} | ทั้งหมด: {row['จำนวนทั้งหมด']}", unsafe_allow_html=True)
        if st.button(f"✅ ล้างเสร็จแล้ว - {row['Job ID']}"):
            if not employee_done:
                st.warning("⚠️ กรุณาเลือกชื่อผู้ล้างก่อนกดปุ่ม")
            else:
                worksheet.update_cell(idx + 2, 11, "Lavage")
                worksheet.update_cell(idx + 2, 13, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                worksheet.update_cell(idx + 2, 14, employee_done)
                st.success("✅ ล้างเสร็จแล้ว")
                st.rerun()

# 📊 โหมด 4: รายงาน
elif menu == "📊 รายงาน":
    df = pd.DataFrame(worksheet.get_all_records())
    view = st.selectbox("📅 เลือกช่วงเวลา", ["ทั้งหมด", "รายวัน", "รายสัปดาห์", "รายเดือน", "รายปี"])
    now = datetime.now()
    df["วันที่"] = pd.to_datetime(df["วันที่"], errors="coerce")
    if view == "รายวัน":
        df = df[df["วันที่"].dt.date == now.date()]
    elif view == "รายสัปดาห์":
        df = df[df["วันที่"] >= now - pd.Timedelta(days=7)]
    elif view == "รายเดือน":
        df = df[df["วันที่"].dt.month == now.month]
    elif view == "รายปี":
        df = df[df["วันที่"].dt.year == now.year]

    st.dataframe(df)
    scrap_sum = df[df["สถานะ"] == "Scrap"].groupby("รหัสงาน")["จำนวนทั้งหมด"].sum().reset_index()
    st.markdown("📌 สรุป Scrap แยกรหัสงาน")
    st.dataframe(scrap_sum)

# 🛠 โหมด 5: Upload Master
elif menu == "🛠 Upload Master":
    password = st.text_input("🔐 รหัส Sup เพื่ออัปโหลด Master", type="password")
    if password == "Sup":
        st.subheader("🛠 อัปโหลดรายชื่อพนักงานและรหัสงาน")
        emp_txt = st.text_area("👥 วางรายชื่อพนักงาน (Enter คั่น)", height=150)
        part_txt = st.text_area("🧾 วางรหัสงาน (Enter คั่น)", height=150)
        if st.button("📤 อัปโหลด"):
            if emp_txt:
                emp_values = [[e] for e in emp_txt.strip().split("\n") if e.strip()]
                sheet.values_update("employee_master!A1", {"valueInputOption": "RAW"}, {"values": [["ชื่อพนักงาน"]] + emp_values})
            if part_txt:
                part_values = [[p] for p in part_txt.strip().split("\n") if p.strip()]
                sheet.values_update("part_code_master!A1", {"valueInputOption": "RAW"}, {"values": [["รหัสงาน"]] + part_values})
            st.success("✅ อัปโหลดรายชื่อสำเร็จแล้ว")
            st.rerun()
