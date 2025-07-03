import streamlit as st
import psycopg2
import pandas as pd
import requests
import math
from datetime import datetime

# === Connection ===
def get_connection():
    try:
        conn = psycopg2.connect(st.secrets["postgres"]["conn_str"])
        return conn
    except Exception as e:
        st.error(f"ไม่สามารถเชื่อมต่อฐานข้อมูลได้: {e}")
        return None

# === Telegram Notification ===
def send_telegram_message(message):
    token = st.secrets["telegram"]["token"]
    chat_id = st.secrets["telegram"]["chat_id"]
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}"
    try:
        requests.get(url)
    except Exception as e:
        st.error(f"Telegram แจ้งเตือนไม่สำเร็จ: {e}")

# === Database Operations ===
def insert_job(data):
    with get_connection() as conn:
        if conn is None:
            return
        cur = conn.cursor()
        keys = ', '.join(data.keys())
        values = ', '.join(['%s'] * len(data))
        sql = f"INSERT INTO job_tracking ({keys}) VALUES ({values})"
        cur.execute(sql, list(data.values()))
        conn.commit()

def update_status(woc, new_status):
    with get_connection() as conn:
        if conn is None:
            return
        cur = conn.cursor()
        cur.execute("UPDATE job_tracking SET status = %s WHERE woc_number = %s", (new_status, woc))
        conn.commit()

def update_job(woc, updated_data):
    with get_connection() as conn:
        if conn is None:
            return
        cur = conn.cursor()
        set_clause = ', '.join([f"{key} = %s" for key in updated_data.keys()])
        sql = f"UPDATE job_tracking SET {set_clause} WHERE woc_number = %s"
        cur.execute(sql, list(updated_data.values()) + [woc])
        conn.commit()

def delete_job(woc):
    with get_connection() as conn:
        if conn is None:
            return
        cur = conn.cursor()
        cur.execute("DELETE FROM job_tracking WHERE woc_number = %s", (woc,))
        conn.commit()

def get_jobs_by_status(status):
    with get_connection() as conn:
        if conn is None:
            return pd.DataFrame()
        return pd.read_sql("SELECT * FROM job_tracking WHERE status = %s ORDER BY created_at DESC", conn, params=(status,))

def get_jobs_by_status_list(status_list):
    if not status_list:
        st.error("ไม่มีสถานะที่เลือก")
        return pd.DataFrame()
    qmarks = ','.join(['%s'] * len(status_list))
    sql = f"SELECT * FROM job_tracking WHERE status IN ({qmarks}) ORDER BY created_at DESC"
    with get_connection() as conn:
        if conn is None:
            return pd.DataFrame()
        return pd.read_sql(sql, conn, params=status_list)

def get_all_jobs():
    with get_connection() as conn:
        if conn is None:
            return pd.DataFrame()
        return pd.read_sql("SELECT * FROM job_tracking ORDER BY created_at DESC", conn)

# === Helper ===
def calculate_pieces(total_weight, barrel_weight, sample_weight, sample_count):
    if sample_count == 0:
        return 0
    try:
        return math.ceil((total_weight - barrel_weight) / ((sample_weight / sample_count) / 1000))
    except ZeroDivisionError:
        return 0

# === Admin Management Mode ===
def admin_management_mode():
    st.header("Admin Management - แก้ไขข้อมูล WOC")
    
    # เลือก WOC ที่จะแก้ไข
    woc_list = get_all_jobs()["woc_number"].tolist()
    if not woc_list:
        st.warning("ไม่มี WOC ในระบบ")
        return
    
    woc_selected = st.selectbox("เลือก WOC ที่ต้องการแก้ไขหรือลบ", woc_list)
    job = get_all_jobs()[get_all_jobs()["woc_number"] == woc_selected].iloc[0]
    
    st.markdown(f"### ข้อมูลปัจจุบันสำหรับ WOC: {woc_selected}")
    st.write(f"- **Part Name:** {job['part_name']}")
    st.write(f"- **สถานะ:** {job['status']}")
    st.write(f"- **น้ำหนักรวม:** {job['total_weight']}")
    st.write(f"- **น้ำหนักถัง:** {job['barrel_weight']}")
    st.write(f"- **น้ำหนักตัวอย่างรวม:** {job['sample_weight']}")
    st.write(f"- **จำนวนตัวอย่าง:** {job['sample_count']}")
    st.write(f"- **จำนวนชิ้นงาน:** {job['pieces_count']}")

    # แสดงแบบฟอร์มแก้ไขข้อมูล
    part_name = st.text_input("แก้ไขชื่อชิ้นงาน", value=job['part_name'])
    total_weight = st.number_input("แก้ไขน้ำหนักรวม", value=job['total_weight'], min_value=0.0, step=0.01)
    barrel_weight = st.number_input("แก้ไขน้ำหนักถัง", value=job['barrel_weight'], min_value=0.0, step=0.01)
    sample_weight = st.number_input("แก้ไขน้ำหนักตัวอย่างรวม", value=job['sample_weight'], min_value=0.0, step=0.01)
    sample_count = st.number_input("แก้ไขจำนวนตัวอย่าง", value=job['sample_count'], min_value=0, step=1)
    
    # แปลง pieces_count เป็นจำนวนเต็มก่อนใช้ใน number_input
    pieces_count = st.number_input("แก้ไขจำนวนชิ้นงาน", value=int(job['pieces_count']), min_value=0, step=1)
    
    status = st.selectbox("เลือกสถานะใหม่", ["FM Transfer TP", "TP Transfer FI", "FI Transfer OS", "Completed", "WIP"])

    # แก้ไขข้อมูลและบันทึก
    if st.button("บันทึกการแก้ไข"):
        updated_data = {
            "part_name": part_name,
            "total_weight": total_weight,
            "barrel_weight": barrel_weight,
            "sample_weight": sample_weight,
            "sample_count": sample_count,
            "pieces_count": pieces_count,
            "status": status
        }
        
        update_job(woc_selected, updated_data)
        st.success(f"บันทึกการแก้ไขข้อมูล WOC {woc_selected} เรียบร้อยแล้ว!")
    
    # ปุ่มลบข้อมูล
    if st.button("ลบข้อมูล WOC"):
        confirm = st.checkbox("ยืนยันการลบ")
        if confirm:
            delete_job(woc_selected)
            st.success(f"ลบข้อมูล WOC {woc_selected} เรียบร้อยแล้ว!")
        else:
            st.warning("กรุณายืนยันการลบก่อน")

# === Main Function ===
def main():
    st.set_page_config(page_title="WOC Tracker", layout="wide")
    st.title("🏭 ระบบติดตามงานโรงงาน (Supabase + Streamlit)")

    menu = st.sidebar.selectbox("เลือกโหมด", [
        "Forming Transfer", "Tapping Transfer", "OS Transfer",
        "Tapping Receive", "Final Receive", "OS Receive",
        "Tapping Work", "Final Work",
        "Completion", "Admin Management", "Report", "Dashboard"
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
    elif menu == "Admin Management":
        admin_management_mode()
    elif menu == "Report":
        report_mode()
    elif menu == "Dashboard":
        dashboard_mode()

if __name__ == "__main__":
    main()
