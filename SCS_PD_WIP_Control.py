import streamlit as st
import psycopg2
import pandas as pd
import requests
import math

# ====== CONNECTION ======
def get_connection():
    return psycopg2.connect(st.secrets["postgres"]["conn_str"])

# ====== TELEGRAM ======
def send_telegram_message(message):
    token = st.secrets["telegram"]["token"]
    chat_id = st.secrets["telegram"]["chat_id"]
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}"
    try:
        requests.get(url)
    except Exception as e:
        st.error("Telegram แจ้งเตือนไม่สำเร็จ: " + str(e))

# ====== DATABASE ======
def insert_job(data):
    with get_connection() as conn:
        cur = conn.cursor()
        keys = ', '.join(data.keys())
        values = ', '.join(['%s'] * len(data))
        sql = f"INSERT INTO job_tracking ({keys}) VALUES ({values})"
        cur.execute(sql, list(data.values()))
        conn.commit()

def update_status(woc, new_status):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE job_tracking SET status = %s WHERE woc_number = %s", (new_status, woc))
        conn.commit()

def get_jobs_by_status(status):
    with get_connection() as conn:
        return pd.read_sql("SELECT * FROM job_tracking WHERE status = %s ORDER BY created_at DESC", conn, params=(status,))

def get_all_jobs():
    with get_connection() as conn:
        return pd.read_sql("SELECT * FROM job_tracking ORDER BY created_at DESC", conn)

def get_jobs_by_multiple_status(status_list):
    with get_connection() as conn:
        qmarks = ','.join(['%s'] * len(status_list))
        sql = f"SELECT * FROM job_tracking WHERE status IN ({qmarks}) ORDER BY created_at DESC"
        return pd.read_sql(sql, conn, params=status_list)

# ====== HELPER ======
def calculate_pieces(total, barrel, sample_weight, sample_count):
    if sample_count == 0:
        return 0
    try:
        return math.ceil((total - barrel) / ((sample_weight / sample_count) / 1000))
    except ZeroDivisionError:
        return 0

# ====== MAIN ======
def main():
    st.set_page_config("WOC Tracker", layout="wide")
    st.title("🏭 ระบบติดตามงานโรงงาน (Supabase)")

    menu = st.sidebar.selectbox("เลือกโหมด", [
        "Forming Transfer", "Tapping Transfer", "OS Transfer",
        "Tapping Receive", "Final Receive", "OS Receive",
        "Tapping Work", "Final Work",
        "Completion", "Export", "Report"
    ])

    if menu == "Forming Transfer":
        transfer_mode("FM")
    elif menu == "Tapping Transfer":
        transfer_mode("TP")
    elif menu == "OS Transfer":
        transfer_mode("OS")
    elif menu == "Tapping Receive":
        receive_mode("TP")
    elif menu == "Final Receive":
        receive_mode("FI")
    elif menu == "OS Receive":
        receive_mode("OS")
    elif menu == "Tapping Work":
        work_mode("TP")
    elif menu == "Final Work":
        work_mode("FI")
    elif menu == "Completion":
        completion_mode()
    elif menu == "Export":
        export_mode()
    elif menu == "Report":
        report_mode()

if __name__ == "__main__":
    main()
