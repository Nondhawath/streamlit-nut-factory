import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime
import requests

# Connect to PostgreSQL
def get_connection():
    return psycopg2.connect(st.secrets["postgres"]["conn_str"])

# ส่งข้อความ Telegram
def send_telegram_message(message):
    token = st.secrets["telegram"]["token"]
    chat_id = st.secrets["telegram"]["chat_id"]
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}"
    requests.get(url)

# เพิ่มข้อมูลใหม่
def insert_job(data: dict):
    conn = get_connection()
    cur = conn.cursor()
    columns = ', '.join(data.keys())
    values = list(data.values())
    placeholders = ', '.join(['%s'] * len(values))
    sql = f"INSERT INTO job_tracking ({columns}) VALUES ({placeholders})"
    cur.execute(sql, values)
    conn.commit()
    cur.close()
    conn.close()

# อ่านข้อมูล WIP เฉพาะสถานะ
@st.cache_data(ttl=60)
def get_jobs_by_status(status):
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM job_tracking WHERE status = %s ORDER BY created_at DESC", conn, params=(status,))
    conn.close()
    return df

# อัปเดตสถานะ WOC
def update_status(woc_number, new_status):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE job_tracking SET status = %s WHERE woc_number = %s", (new_status, woc_number))
    conn.commit()
    cur.close()
    conn.close()

# ✅ Forming Mode
def forming_mode():
    st.header("Forming Mode")
    woc = st.text_input("WOC Number")
    part_name = st.text_input("Part Name")
    operator = st.text_input("Operator Name", value="นายคมสันต์")
    dept_to = st.selectbox("แผนกปลายทาง", ["TP", "FI", "OS"])
    lot = st.text_input("Lot Number")
    total = st.number_input("น้ำหนักรวม", 0.0)
    barrel = st.number_input("น้ำหนักถัง", 0.0)
    sample_w = st.number_input("น้ำหนักตัวอย่างรวม", 0.0)
    sample_c = st.number_input("จำนวนตัวอย่าง", 1)

    pieces = None
    if total and barrel and sample_w and sample_c:
        pieces = (total - barrel) / ((sample_w / sample_c) / 1000)
        st.metric("จำนวนชิ้นงาน", f"{pieces:.2f}")

    if st.button("บันทึกข้อมูล"):
        data = {
            "woc_number": woc,
            "part_name": part_name,
            "operator_name": operator,
            "dept_from": "FM",
            "dept_to": dept_to,
            "lot_number": lot,
            "total_weight": total,
            "barrel_weight": barrel,
            "sample_weight": sample_w,
            "sample_count": sample_c,
            "pieces_count": pieces,
            "status": "WIP-Forming"
        }
        insert_job(data)
        st.success("บันทึกเรียบร้อย")
        send_telegram_message(f"Forming ส่ง WOC {woc} ไป {dept_to}")

# ✅ Tapping รับงาน
def tapping_receive_mode():
    st.header("Tapping รับงานจาก Forming")
    df = get_jobs_by_status("WIP-Forming")

    if df.empty:
        st.info("ยังไม่มีงานที่รอรับจาก Forming")
        return

    woc = st.selectbox("เลือก WOC", df["woc_number"])
    job = df[df["woc_number"] == woc].iloc[0]

    st.write(f"Part: {job.part_name}, Lot: {job.lot_number}")
    st.write(f"น้ำหนักรวม: {job.total_weight}, ตัวอย่าง: {job.sample_weight} / {job.sample_count}")
    st.write(f"จำนวนชิ้นงาน: {job.pieces_count:.2f}")

    if st.button("รับงาน"):
        update_status(woc, "Tapping-Received")
        st.success(f"รับงาน WOC {woc} สำเร็จ")
        send_telegram_message(f"Tapping รับงาน WOC {woc}")

# ✅ Main app
def main():
    st.title("📦 ระบบติดตามงานผ่าน Supabase")

    mode = st.sidebar.radio("เลือกโหมด", [
        "Forming Mode",
        "Tapping Receive Mode"
    ])

    if mode == "Forming Mode":
        forming_mode()
    elif mode == "Tapping Receive Mode":
        tapping_receive_mode()

if __name__ == "__main__":
    main()
