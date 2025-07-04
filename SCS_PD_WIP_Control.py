import streamlit as st
import psycopg2
import pandas as pd
import requests
import math
from datetime import datetime

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

# === Database Operations ===
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

def get_jobs_by_status_list(status_list):
    with get_connection() as conn:
        qmarks = ','.join(['%s'] * len(status_list))
        sql = f"SELECT * FROM job_tracking WHERE status IN ({qmarks}) ORDER BY created_at DESC"
        return pd.read_sql(sql, conn, params=status_list)

def get_all_jobs():
    with get_connection() as conn:
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
def edit_job(woc_number):
    # ดึงข้อมูล WOC ที่ต้องการแก้ไข
    with get_connection() as conn:
        df = pd.read_sql(f"SELECT * FROM job_tracking WHERE woc_number = '{woc_number}'", conn)
    
    if df.empty:
        st.error(f"ไม่พบข้อมูล WOC: {woc_number}")
        return
    
    # แสดงข้อมูลที่ต้องการแก้ไข
    job = df.iloc[0]
    st.write(f"ข้อมูลที่จะแก้ไข: WOC {job['woc_number']} - Part Name: {job['part_name']}")

    new_status = st.selectbox("สถานะใหม่", ["FM Transfer TP", "TP Working", "Completed", "WIP-TP", "FI Working"], index=0)
    new_part_name = st.text_input("Part Name", value=job['part_name'])
    new_operator_name = st.text_input("Operator Name", value=job['operator_name'])
    
    # การบันทึกการแก้ไข
    if st.button("บันทึกการแก้ไข"):
        try:
            with get_connection() as conn:
                cur = conn.cursor()
                update_query = """
                    UPDATE job_tracking
                    SET status = %s, part_name = %s, operator_name = %s
                    WHERE woc_number = %s
                """
                cur.execute(update_query, (new_status, new_part_name, new_operator_name, woc_number))
                conn.commit()
                st.success("บันทึกการแก้ไขเรียบร้อยแล้ว")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")

def delete_job(woc_number):
    # ตรวจสอบการเลือก WOC ที่ต้องการลบ
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM job_tracking WHERE woc_number = %s", (woc_number,))
        job = cur.fetchone()

    if not job:
        st.error(f"ไม่พบข้อมูล WOC: {woc_number}")
        return
    
    st.write(f"คุณกำลังจะลบข้อมูล WOC: {woc_number} - Part Name: {job[2]}")  # แสดงข้อมูลบางส่วน

    # ยืนยันการลบ
    if st.button("ยืนยันการลบ"):
        try:
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM job_tracking WHERE woc_number = %s", (woc_number,))
                conn.commit()
                st.success("ลบข้อมูล WOC เรียบร้อยแล้ว")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการลบข้อมูล: {e}")

# === Admin Management Mode ===
def admin_management_mode():
    st.header("Admin Management")

    # เลือกฟังก์ชันที่ต้องการ
    action = st.selectbox("เลือกการดำเนินการ", ["แก้ไขข้อมูล", "ลบข้อมูล"])

    if action == "แก้ไขข้อมูล":
        woc_to_edit = st.text_input("กรุณากรอก WOC ที่ต้องการแก้ไข")
        if woc_to_edit:
            edit_job(woc_to_edit)

    elif action == "ลบข้อมูล":
        woc_to_delete = st.text_input("กรุณากรอก WOC ที่ต้องการลบ")
        if woc_to_delete:
            delete_job(woc_to_delete)

# === Report Mode ===
def report_mode():
    st.header("รายงานและสรุป WIP")
    
    # ดึงข้อมูลทั้งหมดจากฐานข้อมูล
    df = get_all_jobs()

    # เพิ่มช่องค้นหา
    search = st.text_input("ค้นหา Part Name หรือ WOC")
    if search:
        df = df[df["part_name"].str.contains(search, case=False) | df["woc_number"].str.contains(search, case=False)]
    
    st.dataframe(df)  # แสดงตารางทั้งหมดที่กรองตามคำค้นหา

    st.markdown("### สรุป WIP แยกตามแผนก")
    depts = ["FM", "TP", "FI", "OS"]
    for d in depts:
        wip_df = df[df["status"].str.contains(f"WIP-{d}")]
        if wip_df.empty:
            st.write(f"แผนก {d}: ไม่มีงาน WIP")
        else:
            summary = wip_df.groupby("part_name").agg(
                จำนวนงาน=pd.NamedAgg(column="woc_number", aggfunc="count"),
                จำนวนชิ้นงาน=pd.NamedAgg(column="pieces_count", aggfunc="sum")
            ).reset_index()
            st.write(f"แผนก {d}")
            st.dataframe(summary)

# === Main ===
def main():
    st.set_page_config(page_title="WOC Tracker", layout="wide")
    st.title("🏭 ระบบติดตามงานโรงงาน (Supabase + Streamlit)")

    menu = st.sidebar.selectbox("เลือกโหมด", [
        "Forming Transfer",
        "Tapping Transfer",
        "Tapping Receive",
        "Tapping Work",
        "OS Transfer",
        "OS Receive",
        "Final Receive",
        "Final Work",
        "Completion",
        "Report",
        "Dashboard",
        "Admin Management"  # เพิ่มเมนูนี้เข้าไป
    ])

    if menu == "Admin Management":
        admin_management_mode()
    elif menu == "Forming Transfer":
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
    elif menu == "Report":
        report_mode()
    elif menu == "Dashboard":
        dashboard_mode()

if __name__ == "__main__":
    main()
