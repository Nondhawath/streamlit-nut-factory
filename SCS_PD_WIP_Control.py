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

# === Transfer Mode ===
def transfer_mode(dept_from):
    st.header(f"{dept_from} Transfer")
    prev_woc = ""
    
    # เลือก WOC ก่อนหน้า (สถานะ TP Working)
    if dept_from == "TP":
        df = get_jobs_by_status("TP Working")  # ดึงงานที่มีสถานะ TP Working
        prev_woc_options = [""] + list(df["woc_number"].unique())
        prev_woc = st.selectbox("WOC ก่อนหน้า (ถ้ามี)", prev_woc_options)
    else:
        st.write("FM Transfer ไม่ต้องเลือก WOC ก่อนหน้า")

    # เพิ่ม WOC ใหม่
    new_woc = st.text_input("WOC ใหม่")
    
    # แสดงชื่อชิ้นงานจาก WOC ก่อนหน้า (ถ้ามี)
    part_name = ""
    if prev_woc:
        df_all = get_all_jobs()
        part_name = df_all[df_all["woc_number"] == prev_woc]["part_name"].values[0]
    part_name = st.text_input("Part Name", value=part_name)

    dept_to = st.selectbox("แผนกปลายทาง", ["TP", "FI", "OS"])
    lot_number = st.text_input("Lot Number")
    total_weight = st.number_input("น้ำหนักรวม", min_value=0.0, step=0.01)
    barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0, step=0.01)
    sample_weight = st.number_input("น้ำหนักตัวอย่างรวม", min_value=0.0, step=0.01)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=0, step=1, value=0)

    pieces_count = 0
    if all(v > 0 for v in [total_weight, sample_weight]) and sample_count > 0:
        pieces_count = calculate_pieces(total_weight, barrel_weight, sample_weight, sample_count)
        st.metric("จำนวนชิ้นงาน (คำนวณ)", pieces_count)

    operator_name = st.text_input("ชื่อผู้ใช้งาน (Operator)")

    if st.button("บันทึก Transfer"):
        if not new_woc.strip():
            st.error("กรุณากรอก WOC ใหม่")
            return
        if pieces_count == 0:
            st.error("กรุณากรอกข้อมูลน้ำหนักและจำนวนตัวอย่างให้ถูกต้อง")
            return
        
        # บันทึกข้อมูลในฐานข้อมูล
        insert_job({
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
            "created_at": datetime.utcnow()
        })
        
        # ถ้ามี WOC ก่อนหน้า ให้เปลี่ยนสถานะเป็น "Completed"
        if prev_woc:
            update_status(prev_woc, "Completed")
        
        st.success(f"บันทึก {dept_from} Transfer เรียบร้อยแล้ว")

# === Receive Mode ===
def receive_mode(dept_to):
    st.header(f"{dept_to} Receive")
    
    # กรองงานตามแผนกที่ต้องการรับ
    dept_from_map = {
        "TP": ["FM", "TP Working"],
        "FI": ["TP"],
        "OS": ["FM", "TP"]
    }

    dept_to_next = "Final Work" if dept_to == "FI" else ""  # ตั้งค่าแผนกถัดไปในกรณี FI

    from_depts = dept_from_map.get(dept_to, [])
    status_filters = [f"{fd} Transfer {dept_to}" for fd in from_depts]
    
    if dept_to == "FI":
        # แสดงเฉพาะ WOC ที่มีสถานะ 'FM Transfer FI' หรือ 'TP Transfer FI'
        status_filters = ["FM Transfer FI", "TP Transfer FI"]

    df = get_jobs_by_status_list(status_filters)

    if df.empty:
        st.warning("ไม่มีงานรอรับ")
        return

    woc_list = df["woc_number"].tolist()
    woc_selected = st.selectbox("เลือก WOC", woc_list)
    job = df[df["woc_number"] == woc_selected].iloc[0]

    st.markdown(f"- **Part Name:** {job['part_name']}")
    st.markdown(f"- **Lot Number:** {job['lot_number']}")
    st.markdown(f"- **จำนวนชิ้นงานเดิม:** {job['pieces_count']}")

    # บันทึกข้อมูลน้ำหนักใหม่
    total_weight = st.number_input("น้ำหนักรวม", min_value=0.0, step=0.01, value=0.0)
    barrel_weight = st.number_input("น้ำหนักถัง", min_value=0.0, step=0.01, value=0.0)
    sample_weight = st.number_input("น้ำหนักตัวอย่างรวม", min_value=0.0, step=0.01, value=0.0)
    sample_count = st.number_input("จำนวนตัวอย่าง", min_value=0, step=1, value=0)

    pieces_new = calculate_pieces(total_weight, barrel_weight, sample_weight, sample_count)
    st.metric("จำนวนชิ้นงานที่คำนวณได้", pieces_new)

    # คำนวณ % คลาดเคลื่อน
    try:
        diff_pct = abs(pieces_new - job["pieces_count"]) / job["pieces_count"] * 100 if job["pieces_count"] > 0 else 0
    except Exception:
        diff_pct = 0

    # แสดงเปอร์เซ็นต์คลาดเคลื่อน
    st.write(f"% คลาดเคลื่อน: {diff_pct:.2f}%")

    operator_name = st.text_input("ชื่อผู้ใช้งาน (Operator)")

    # แสดงแผนกถัดไป
    if dept_to == "FI":
        dept_to_next = "Final Work"  # ถัดไปจะต้องเป็น "Final Work" สำหรับแผนก FI

    if st.button("รับเข้าและส่งต่อ"):
        if dept_to_next == "":
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

        # เปลี่ยนสถานะของ WOC
        update_status(woc_selected, next_status)
        st.success(f"รับเข้า {dept_to} เรียบร้อยแล้ว และส่งต่อไปยัง {dept_to_next}")

# === Main App ===
def main():
    mode = st.sidebar.radio("เลือกโหมด", ("Tapping Receive", "Final Receive"))

    if mode == "Tapping Receive":
        st.title("Tapping Receive Mode")
        receive_mode("TP")
    elif mode == "Final Receive":
        st.title("Final Receive Mode")
        receive_mode("FI")

if __name__ == "__main__":
    main()
