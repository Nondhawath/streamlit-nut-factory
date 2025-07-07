import streamlit as st
import psycopg2
import pandas as pd
import requests
import math
from datetime import datetime, timedelta
import numpy as np

# === Connection Pool ===
def get_connection():
    try:
        conn = psycopg2.connect(st.secrets["postgres"]["conn_str"])
        return conn
    except psycopg2.DatabaseError as e:
        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อฐานข้อมูล {e}")
        return None

# === Telegram Notification ===
def send_telegram_message(message):
    token = st.secrets["telegram"]["token"]
    chat_id = st.secrets["telegram"]["chat_id"]
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}"
    try:
        response = requests.get(url)
        if response.status_code != 200:
            st.error(f"Telegram แจ้งเตือนไม่สำเร็จ {response.status_code}")
    except Exception as e:
        st.error(f"Telegram แจ้งเตือนไม่สำเร็จ {e}")

# === Database Operations ===
def insert_job(data):
    data["created_at"] = datetime.utcnow() + timedelta(hours=7)
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

# === Helper Functions ===
def calculate_pieces(total_weight, barrel_weight, sample_weight, sample_count):
    if total_weight == barrel_weight or sample_weight == 0 or sample_count == 0:
        st.warning("ค่าที่กรอกไม่ถูกต้อง น้ำหนักรวม, น้ำหนักตัวอย่าง, และจำนวนตัวอย่างต้องเป็นค่าบวกที่ถูกต้อง")
        return 0
    try:
        return math.ceil((total_weight - barrel_weight) / ((sample_weight * sample_count) / 1000))
    except ZeroDivisionError:
        st.error("เกิดข้อผิดพลาดในการคำนวณ แบ่งด้วยศูนย์")
        return 0

# === Transfer Mode ===
def transfer_mode(dept_from):
    st.header(f"{dept_from} Transfer")
    df_all = get_all_jobs()
    prev_woc = ""

    # เลือก WOC ก่อนหน้า
    if dept_from == "TP":
        df = get_jobs_by_status("TP Working")
        prev_woc_options = [""] + list(df["woc_number"].unique())
        prev_woc = st.selectbox("WOC ก่อนหน้า (ถ้ามี)", prev_woc_options)
    elif dept_from == "OS":
        df = get_jobs_by_status("OS Received")
        prev_woc_options = [""] + list(df["woc_number"].unique())
        prev_woc = st.selectbox("WOC ก่อนหน้า (ถ้ามี)", prev_woc_options)
    else:
        st.write("FM Transfer ไม่ต้องเลือก WOC ก่อนหน้า")

    new_woc = st.text_input("WOC ใหม่")
    part_name = ""
    if prev_woc:
        part_name = df_all[df_all["woc_number"] == prev_woc]["part_name"].values[0]
    part_name = st.text_input("Part Name", value=part_name)

    dept_to = st.selectbox("แผนกปลายทาง", ["TP", "FI", "OS"])
    lot_number = st.text_input("Lot Number")
    total_weight = st.number_input("น้ำหนักรวม", min_value=0.0, step=0.01)
    barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0, step=0.01)
    sample_weight = st.number_input("น้ำหนักตัวอย่างรวม", min_value=0.0, step=0.01)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=0, step=1, value=0)
    operator_name = st.text_input("ชื่อผู้ใช้งาน (Operator)")

    pieces_count = calculate_pieces(total_weight, barrel_weight, sample_weight, sample_count)
    st.metric("จำนวนชิ้นงาน (คำนวณ)", pieces_count)

    if st.button("บันทึก Transfer"):
        if not new_woc.strip():
            st.error("กรุณากรอก WOC ใหม่")
            return
        if pieces_count == 0:
            st.error("กรุณากรอกข้อมูลน้ำหนักและจำนวนตัวอย่างให้ถูกต้อง")
            return

        data = {
            "woc_number": new_woc,
            "part_name": part_name,
            "operator_name": operator_name,
            "dept_from": dept_from,
            "dept_to": dept_to,
            "lot_number": lot_number,
            "total_weight": total_weight,
            "barrel_weight": barrel_weight,
            "sample_weight": sample_weight,
            "sample_count": sample_count,
            "pieces_count": pieces_count,
            "status": f"{dept_from} Transfer {dept_to}",
            "created_at": datetime.utcnow(),
            "prev_woc_number": prev_woc,
            "ok_count": 0,
            "ng_count": 0,
            "rework_count": 0,
            "remain_count": 0,
            "machine_name": ""
        }

        insert_job(data)

        # Update status of the previous WOC as Completed
        if prev_woc:
            update_status(prev_woc, "Completed")

        st.success(f"บันทึก {dept_from} Transfer เรียบร้อยแล้ว")

# === Receive Mode ===
def receive_mode(dept_to):
    st.header(f"{dept_to} Receive")

    # กำหนดสถานะที่แผนกต้องการรับ
    if dept_to == "FI":
        status_filters = ["FM Transfer FI", "TP Transfer FI", "OS Transfer FI"]
    elif dept_to == "TP":
        status_filters = ["FM Transfer TP", "OS Transfer TP"]
    elif dept_to == "OS":
        status_filters = ["FM Transfer OS", "TP Transfer OS"]
    else:
        status_filters = []

    # ดึงข้อมูลจากฐานข้อมูลที่ตรงกับสถานะที่ต้องการ
    df = get_jobs_by_status_list(status_filters)

    if df.empty:
        st.warning("ไม่มีงานรอรับ")
        return

    # แสดง WOC ที่สามารถเลือกได้
    woc_list = df["woc_number"].tolist()
    woc_selected = st.selectbox("เลือก WOC", woc_list)
    job = df[df["woc_number"] == woc_selected].iloc[0]

    st.markdown(f"- Part Name: {job['part_name']}")
    st.markdown(f"- Lot Number: {job['lot_number']}")
    st.markdown(f"- จำนวนชิ้นงานเดิม: {job['pieces_count']}")

    total_weight = st.number_input("น้ำหนักรวม", min_value=0.0, step=0.01, value=0.0)
    barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0, step=0.01, value=0.0)
    sample_weight = st.number_input("น้ำหนักตัวอย่างรวม", min_value=0.0, step=0.01, value=0.0)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=0, step=1, value=0)
    pieces_new = calculate_pieces(total_weight, barrel_weight, sample_weight, sample_count)
    st.metric("จำนวนชิ้นงานที่คำนวณได้", pieces_new)

    # คำนวณเปอร์เซ็นต์คลาดเคลื่อนระหว่างจำนวนชิ้นงานที่คำนวณได้และจำนวนที่บันทึกไว้
    try:
        diff_pct = abs(pieces_new - job["pieces_count"]) / job["pieces_count"] * 100 if job["pieces_count"] > 0 else 0
    except Exception:
        diff_pct = 0
    st.metric("% คลาดเคลื่อน", f"{diff_pct:.2f}%")

    if diff_pct > 2:
        send_telegram_message(
            f"⚠️ ความคลาดเคลื่อนน้ำหนักเกิน 2% | แผนก: {dept_to} | WOC: {woc_selected} | Part: {job['part_name']} | "
            f"จำนวนเดิม: {job['pieces_count']} | จำนวนที่รับจริง: {pieces_new} | คลาดเคลื่อน: {diff_pct:.2f}%"
        )

    operator_name = st.text_input("ชื่อผู้ใช้งาน (Operator)")

    # เลือกแผนกถัดไป
    if dept_to == "TP":
        dept_to_next = st.selectbox("แผนกถัดไป", ["Tapping Work"])
    elif dept_to == "FI":
        dept_to_next = "Final Work"
        st.markdown(f"- แผนกถัดไป: {dept_to_next}")
    elif dept_to == "OS":
        dept_to_next = st.selectbox("แผนกถัดไป", ["OS Transfer"])
    else:
        dept_to_next = ""
        st.markdown("- กรุณาระบุแผนกถัดไป")

    # ปุ่มบันทึกการรับงาน
    if st.button("รับเข้าและส่งต่อ"):
        if not dept_to_next:
            st.error("กรุณาเลือกแผนกถัดไป")
            return

        next_status = f"WIP-{dept_to_next}"

        insert_job({
            "woc_number": woc_selected,
            "part_name": job["part_name"],
            "operator_name": operator_name,
            "dept_from": dept_to,
            "dept_to": dept_to_next,
            "lot_number": job["lot_number"],
            "total_weight": total_weight,
            "barrel_weight": barrel_weight,
            "sample_weight": sample_weight,
            "sample_count": sample_count,
            "pieces_count": pieces_new,
            "status": next_status,
            "created_at": datetime.utcnow()
        })

        # เปลี่ยนสถานะของ WOC ที่เป็น TP Received หรือ FI Received ให้เป็น Completed
        if job['status'] == "TP Received" or job['status'] == "FI Received":
            update_status(woc_selected, "Completed")

        st.success(f"รับ WOC {woc_selected} เรียบร้อยและเปลี่ยนสถานะเป็น {dept_to} Received")
        send_telegram_message(f"{dept_to} รับ WOC {woc_selected} ส่งต่อไปยัง {dept_to_next}")
