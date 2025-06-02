# 📦 Import
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests

# ✅ Telegram
TOKEN = "7617656983:AAGqI7jQvEtKZw_tD11cQneH57WvYWl9r_s"
CHAT_ID = "-4944715716"

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}
        requests.post(url, data=data)
    except Exception as e:
        st.warning(f"❌ Telegram error: {e}")

# ⏰ Timezone
def now_th():
    return datetime.utcnow() + timedelta(hours=7)

# 🔐 Auth
SCOPE = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(st.secrets["GOOGLE_SHEETS_CREDENTIALS"], scopes=SCOPE)
client = gspread.authorize(creds)
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1GM-es30UBsqFCxBVQbBxht6IntIkL6troc5c2PWD3JA")
ws_data = sheet.worksheet("Data")

# 📚 Load master
try:
    emp_df = pd.DataFrame(sheet.worksheet("employee_master").get_all_records())
    emp_names = emp_df["ชื่อพนักงาน"].tolist()
    emp_levels = dict(zip(emp_df["ชื่อพนักงาน"], emp_df["ระดับ"]))
    emp_pass = dict(zip(emp_df["ชื่อพนักงาน"], emp_df["รหัส"].astype(str)))
except:
    emp_names, emp_levels, emp_pass = [], {}, {}

try:
    part_master = sheet.worksheet("part_code_master").col_values(1)[1:]
except:
    part_master = []

# 🧑 Login
if "user" not in st.session_state:
    with st.form("login_form"):
        st.subheader("🔐 เข้าสู่ระบบ")
        user = st.selectbox("👤 ชื่อพนักงาน", emp_names)
        pw = st.text_input("🔑 รหัสผ่าน", type="password")
        login = st.form_submit_button("✅ Login")
        if login:
            if emp_pass.get(user) == pw:
                st.session_state["user"] = user
                st.session_state["level"] = emp_levels.get(user, "")
                st.success("✅ เข้าสู่ระบบสำเร็จ")
                st.rerun()
            else:
                st.error("❌ รหัสผ่านไม่ถูกต้อง")
    st.stop()

user = st.session_state["user"]
level = st.session_state["level"]
st.set_page_config(page_title="Sorting Process", layout="wide")
st.title(f"🔧 Sorting Process - สวัสดี {user} ({level})")

# 🛡 Permission
mode_options = []
if level in ["S1"]:
    mode_options = ["📥 Sorting MC", "🧾 Waiting Judgement", "💧 Oil Cleaning", "📊 รายงาน", "🛠 Upload Master"]
elif level == "T1":
    mode_options = ["🧾 Waiting Judgement"]
elif level == "T7":
    mode_options = ["📥 Sorting MC"]
elif level == "T8":
    mode_options = ["💧 Oil Cleaning"]
else:
    st.error("❌ ไม่สามารถระบุสิทธิ์การเข้าใช้งาน")
    st.stop()

menu = st.sidebar.selectbox("📌 เลือกโหมด", mode_options)

# 🆔 Job ID
def generate_job_id():
    records = ws_data.get_all_records()
    prefix = now_th().strftime("%y%m")
    seq = [
        int(str(r["Job ID"])[-4:])
        for r in records if str(r.get("Job ID", "")).startswith(prefix) and str(r.get("Job ID", "")[-4:]).isdigit()
    ]
    return f"{prefix}{(max(seq)+1) if seq else 1:04d}"

# 📥 Sorting MC
if menu == "📥 Sorting MC":
    st.subheader("📥 กรอกข้อมูล Sorting")
    with st.form("sorting_form"):
        job_id = generate_job_id()
        st.markdown(f"🆔 Job ID: `{job_id}`")
        part = st.selectbox("🔩 รหัสงาน", part_master)
        machine = st.selectbox("🛠 เครื่อง", [f"SM{i:02}" for i in range(1, 31)])
        lot = st.text_input("📦 Lot")
        checked = st.number_input("🔍 จำนวนตรวจ", min_value=0)
        ng = st.number_input("❌ NG", min_value=0)
        pending = st.number_input("⏳ ยังไม่ตรวจ", min_value=0)
        total = ng + pending
        submit = st.form_submit_button("✅ บันทึก")
        if submit:
            row = [
                now_th().strftime("%Y-%m-%d %H:%M:%S"), job_id, user, part,
                machine, lot, checked, ng, pending, total,
                "Sorting MC", "", "", ""
            ]
            ws_data.append_row(row)
            st.success("✅ บันทึกเรียบร้อย")
            send_telegram(
                f"📥 <b>New Sorting</b>\n"
                f"🆔 Job ID: <code>{job_id}</code>\n"
                f"👷‍♂️ {user} | 🔩 {part} | 🛠 {machine} | 📦 Lot: {lot}\n"
                f"❌ NG: {ng} | ⏳ ยังไม่ตรวจ: {pending}"
            )

# 🧾 Waiting Judgement
elif menu == "🧾 Waiting Judgement":
    st.subheader("🧾 ตัดสินใจ Scrap / Recheck")
    df = pd.DataFrame(ws_data.get_all_records())
    df = df[df["สถานะ"] == "Sorting MC"]
    for i, row in df.iterrows():
        st.markdown(f"🆔 <b>{row['Job ID']}</b> | {row['รหัสงาน']} | NG: {row['จำนวน NG']} | ⏳ {row['จำนวนยังไม่ตรวจ']}", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        if col1.button("♻️ Recheck", key=f"re_{row['Job ID']}_{i}"):
            ws_data.update_cell(i+2, 11, "Recheck")
            ws_data.update_cell(i+2, 12, now_th().strftime("%Y-%m-%d %H:%M:%S"))
            ws_data.update_cell(i+2, 14, user)
            send_telegram(f"♻️ <b>Recheck</b>: Job ID <code>{row['Job ID']}</code> โดย {user}")
            st.rerun()
        if col2.button("🗑 Scrap", key=f"sc_{row['Job ID']}_{i}"):
            ws_data.update_cell(i+2, 11, "Scrap")
            ws_data.update_cell(i+2, 12, now_th().strftime("%Y-%m-%d %H:%M:%S"))
            ws_data.update_cell(i+2, 14, user)
            send_telegram(
                f"🗑 <b>Scrap</b>: Job ID <code>{row['Job ID']}</code>\n"
                f"🔩 {row['รหัสงาน']} | จำนวน: {row['จำนวนทั้งหมด']} | 👷‍♂️ โดย {user}"
            )
            st.rerun()

# 💧 Oil Cleaning
elif menu == "💧 Oil Cleaning":
    st.subheader("💧 ล้างงาน")
    df = pd.DataFrame(ws_data.get_all_records())
    df = df[df["สถานะ"] == "Recheck"]
    for i, row in df.iterrows():
        st.markdown(f"🆔 <b>{row['Job ID']}</b> | {row['รหัสงาน']} | {row['จำนวนทั้งหมด']}", unsafe_allow_html=True)
        if st.button("✅ ล้างเสร็จแล้ว", key=f"done_{row['Job ID']}_{i}"):
            ws_data.update_cell(i+2, 11, "Cleaned")
            ws_data.update_cell(i+2, 13, now_th().strftime("%Y-%m-%d %H:%M:%S"))
            ws_data.update_cell(i+2, 14, user)
            send_telegram(
                f"💧 <b>ล้างเสร็จแล้ว</b>: Job ID <code>{row['Job ID']}</code>\n"
                f"🔩 {row['รหัสงาน']} | จำนวน: {row['จำนวนทั้งหมด']} | 👷‍♂️ โดย {user}"
            )
            st.success("✅ ล้างเสร็จแล้ว")
            st.rerun()

# 📊 รายงาน
elif menu == "📊 รายงาน":
    df = pd.DataFrame(ws_data.get_all_records())
    df["วันที่"] = pd.to_datetime(df["วันที่"], errors="coerce")
    st.subheader("📊 รายงานข้อมูล")
    view = st.selectbox("📆 ช่วงเวลา", ["ทั้งหมด", "รายวัน", "รายสัปดาห์", "รายเดือน", "รายปี"])
    now = now_th()
    if view == "รายวัน":
        df = df[df["วันที่"].dt.date == now.date()]
    elif view == "รายสัปดาห์":
        df = df[df["วันที่"] >= now - pd.Timedelta(days=7)]
    elif view == "รายเดือน":
        df = df[df["วันที่"].dt.month == now.month]
    elif view == "รายปี":
        df = df[df["วันที่"].dt.year == now.year]
    st.dataframe(df)
    scrap = df[df["สถานะ"] == "Scrap"].groupby("รหัสงาน")["จำนวนทั้งหมด"].sum().reset_index()
    st.markdown("📌 สรุป Scrap")
    st.dataframe(scrap)

# 🛠 Upload Master
elif menu == "🛠 Upload Master":
    password = st.text_input("รหัส Sup", type="password")
    if password == "Sup":
        st.subheader("🛠 อัปโหลด Master")
        emp_txt = st.text_area("👥 รายชื่อ (ชื่อ,รหัส,ระดับ)", height=150)
        part_txt = st.text_area("🧾 รหัสงาน", height=150)
        if st.button("📤 อัปโหลด"):
            if emp_txt:
                lines = [l.split(",") for l in emp_txt.strip().split("\n") if "," in l]
                values = [["ชื่อพนักงาน", "รหัส", "ระดับ"]] + lines
                sheet.values_update("employee_master!A1", {"valueInputOption": "RAW"}, {"values": values})
            if part_txt:
                parts = [[p] for p in part_txt.strip().split("\n") if p]
                sheet.values_update("part_code_master!A1", {"valueInputOption": "RAW"}, {"values": [["รหัสงาน"]] + parts})
            st.success("✅ อัปโหลดสำเร็จ")
            st.rerun()
