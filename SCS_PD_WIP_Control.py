
import streamlit as st
import psycopg2
import pandas as pd
import requests
import math
from datetime import datetime
from io import BytesIO
import base64
from st_aggrid import AgGrid

# === Connection ===
def get_connection():
    return psycopg2.connect(st.secrets["postgres"]["conn_str"])

# === Telegram Notification ===
def send_telegram_message(message):
    token = st.secrets["telegram"]["token"]
    chat_id = st.secrets["telegram"]["chat_id"]
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}"
    try:
        requests.get(url)
    except Exception as e:
        st.error(f"Telegram แจ้งเตือนไม่สำเร็จ: {e}")

# === Authentication ===
def login_page():
    st.title("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == "admin" and password == "1234":
            st.session_state.logged_in = True
            st.session_state.role = "admin"
        elif username == "staff" and password == "1234":
            st.session_state.logged_in = True
            st.session_state.role = "staff"
        else:
            st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

# === Export Excel ===
def download_excel(df: pd.DataFrame, filename="report.xlsx"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    processed = output.getvalue()
    b64 = base64.b64encode(processed).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">📥 ดาวน์โหลด Excel</a>'
    return href

# === Upload Excel ===
def upload_job_file():
    st.title("📤 อัปโหลดไฟล์งานเข้า Database")
    uploaded = st.file_uploader("เลือกไฟล์ Excel", type=["xlsx"])
    if uploaded:
        df = pd.read_excel(uploaded)
        st.write("Preview:", df.head())
        status = st.selectbox("เลือกสถานะเริ่มต้นของไฟล์นี้", ["FM Transfer TP", "TP Received", "FI Working"])
        if st.button("อัปโหลดเข้า Database"):
            with get_connection() as conn:
                cur = conn.cursor()
                for _, row in df.iterrows():
                    data = row.to_dict()
                    data["status"] = status
                    data["created_at"] = datetime.utcnow() + pd.Timedelta(hours=7)
                    cur.execute("SELECT 1 FROM job_tracking WHERE woc_number = %s", (data["woc_number"],))
                    if cur.fetchone():
                        continue
                    keys = ', '.join(data.keys())
                    values = ', '.join(['%s'] * len(data))
                    sql = f"INSERT INTO job_tracking ({keys}) VALUES ({values})"
                    cur.execute(sql, list(data.values()))
                conn.commit()
            st.success("อัปโหลดเรียบร้อยแล้ว")

# === Dashboard ===
def dashboard_mode():
    st.header("📊 Dashboard")
    df = get_all_jobs()
    if df.empty:
        st.info("ไม่มีข้อมูล")
        return
    st.dataframe(df)
    st.markdown(download_excel(df), unsafe_allow_html=True)

# === Report Mode ===
def report_mode():
    st.header("📈 รายงานตามสถานะ")
    df = get_all_jobs()
    if df.empty:
        st.info("ไม่มีข้อมูล")
        return

    statuses = df["status"].unique().tolist()
    selected = st.multiselect("เลือกสถานะที่ต้องการแสดง", statuses, default=statuses)
    filtered = df[df["status"].isin(selected)]

    st.write(f"จำนวนรายการ: {len(filtered)}")
    st.dataframe(filtered)
    st.markdown(download_excel(filtered, filename="filtered_report.xlsx"), unsafe_allow_html=True)

# === Main ===
def main():
    st.set_page_config(page_title="WOC Tracker", layout="wide")
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login_page()
        return

    role = st.session_state.get("role", "")

    menu = st.sidebar.selectbox("เลือกโหมด", [
        "Forming Transfer", "Tapping Transfer", "Tapping Receive", "Tapping Work",
        "OS Transfer", "OS Receive", "Final Receive", "Final Work", "Completion",
        "📊 Dashboard", "📈 Report",
        "📤 Upload Jobs", "📥 Export รายงานทั้งหมด"
    ])

    if menu == "Forming Transfer":
        transfer_mode("FM")
    elif menu == "Tapping Transfer":
        transfer_mode("TP")
    elif menu == "Tapping Receive":
        receive_mode("TP")
    elif menu == "Tapping Work":
        work_mode("TP")
    elif menu == "OS Transfer":
        transfer_mode("OS")
    elif menu == "OS Receive":
        receive_mode("OS")
    elif menu == "Final Receive":
        receive_mode("FI")
    elif menu == "Final Work":
        work_mode("FI")
    elif menu == "Completion":
        completion_mode()
    elif menu == "📊 Dashboard":
        dashboard_mode()
    elif menu == "📈 Report":
        report_mode()
    elif menu == "📤 Upload Jobs":
        upload_job_file()
    elif menu == "📥 Export รายงานทั้งหมด":
        df = get_all_jobs()
        st.dataframe(df)
        st.markdown(download_excel(df), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
